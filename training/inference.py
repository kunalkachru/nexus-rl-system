"""
NEXUS Inference — Qwen2.5-1.5B IC action generation.

Converts environment observations into structured IC actions via:
  1. build_ic_prompt()  — observation dict → chat-formatted prompt string
  2. parse_ic_action()  — model completion → action dict (with fallback)
  3. NexusInferenceEngine — thin model wrapper (Unsloth 4-bit LoRA)

The model generates a JSON block containing all IC action fields.
parse_ic_action() is lenient: partial JSON, missing fields, and hallucinated
keys are all handled gracefully so training never crashes on bad completions.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, Optional

# ------------------------------------------------------------------
# Prompt construction
# ------------------------------------------------------------------

IC_SYSTEM_PROMPT = """\
You are the Incident Commander (IC) for NEXUS, a production incident response AI system.
Your role is to coordinate 4 specialist agents (L1 Support, L2 Engineer, SRE, Product Manager)
and an OversightAgent to detect, investigate, and resolve production incidents.

You receive a partial observation of the incident — your agents see different subsets.
You must reason carefully, identify red herrings, and orchestrate the correct response.

Expert review criteria for this episode: {expert_criteria}
- speed: prioritize MTTR above all else
- communication: prioritize customer notifications and SLA management
- technical: prioritize root cause accuracy and runbook correctness
- cost: prioritize coordination efficiency, avoid duplicate tool queries

RESPONSE FORMAT (JSON only — no other text):
{{
  "situation_assessment": "<detailed multi-sentence analysis of current evidence, hypotheses, and plan>",
  "hypothesis": "<specific root cause hypothesis>",
  "coalition_vote": "<vote for competing hypothesis if in investigation phase, else null>",
  "l1_directive": {{"action": "<action>", "parameters": {{}}, "reasoning": "<why>"}},
  "l2_directive": {{"action": "<action>", "parameters": {{}}, "reasoning": "<why>"}},
  "sre_directive": {{"action": "<action>", "parameters": {{}}, "reasoning": "<why>"}},
  "pm_directive": {{"action": "<action>", "parameters": {{}}, "reasoning": "<why>"}},
  "resolution_confidence": <0.0–1.0; >0.8 ends the episode>,
  "escalation_required": <true|false>
}}

Available agent actions:
  L1 (SimSlack + SimCustomerPortal): check_customer_reports, send_notification, get_sla_status
  L2 (SimDatadog): check_all_alerts, query_metric, query_logs, check_deploy_history, get_service_map
  SRE (SimRunbook): execute_runbook_step, list_runbooks, rollback_step
  PM (SimJira): track_revenue_impact, create_ticket, get_open_tickets, get_breach_risk

Schema note: If schema_version is v2.0 (INC007 after drift), SRE must use runbook_ref not step_id.
"""


def build_ic_prompt(obs: Dict[str, Any]) -> str:
    """
    Convert an IC observation dict into a Qwen2.5 chat-formatted prompt.
    Returns the full prompt string ready for tokenization.
    """
    expert_criteria = obs.get("expert_criteria", "technical")
    system = IC_SYSTEM_PROMPT.format(expert_criteria=expert_criteria)

    # Build user message from observation fields
    alerts = obs.get("initial_alerts", [])
    alert_lines = "\n".join(
        f"  [{a.get('status', 'UNKNOWN'):8s}] {a.get('service')}.{a.get('metric')} "
        f"= {a.get('value')} (threshold: {a.get('threshold', 'N/A')})"
        for a in alerts
    )

    findings = obs.get("agent_findings", [])
    finding_lines = "\n".join(
        f"  [{f.get('agent'):12s} step {f.get('step'):2d}] {f.get('finding')}"
        for f in findings[-8:]  # Last 8 findings
    ) or "  (none yet)"

    oversight = obs.get("oversight_findings", [])
    oversight_lines = "\n".join(
        f"  [{o.get('type'):9s}] {o.get('finding_category')}: {o.get('description')}"
        for o in oversight[-3:]
    ) or "  (none)"

    competing = obs.get("competing_hypotheses", [])
    competing_block = ""
    if competing:
        competing_block = "\nCOMPETING HYPOTHESES (vote required in investigation phase):\n"
        for i, h in enumerate(competing):
            competing_block += f"  [{i + 1}] {h}\n"

    runbooks = obs.get("runbooks_available", [])
    schema = obs.get("schema_version", "v1.0")
    key_field = "runbook_ref" if schema == "v2.0" else "step_id"
    runbook_lines = "\n".join(
        f"  {r.get(key_field, r.get('step_id', r.get('runbook_ref', '?')))}: {r.get('title')}"
        for r in runbooks[:6]
    ) or "  (none available)"

    user_msg = f"""\
INCIDENT: [{obs.get('incident_id')}] {obs.get('incident_title', '')}
SEVERITY: {obs.get('severity', '').upper()} | PHASE: {obs.get('phase', '').upper()} | \
STEP: {obs.get('step', 0)} | ELAPSED: {obs.get('elapsed_minutes', 0):.0f}min
SCHEMA VERSION: {schema} | COALITION: {obs.get('coalition_result') or 'pending'}

AFFECTED SERVICES: {', '.join(obs.get('affected_services', []))}
AFFECTED REGIONS: {', '.join(obs.get('affected_regions', []))}
CUSTOMER REPORTS: {'; '.join(obs.get('customer_reports', ['none'])[:3])}

ACTIVE ALERTS:
{alert_lines or '  (none)'}

AGENT FINDINGS (most recent):
{finding_lines}

OVERSIGHT FINDINGS:
{oversight_lines}
{competing_block}
AVAILABLE RUNBOOKS ({schema}):
{runbook_lines}

NOTIFICATIONS SENT: {obs.get('notifications_sent', 0)}
RUNBOOK STEPS COMPLETED: {', '.join(obs.get('runbook_steps_completed', [])) or 'none'}
ESCALATION DONE: {obs.get('escalation_done', False)}
OVERSIGHT VIOLATIONS: {obs.get('oversight_violations', 0)}

Respond with your IC action JSON:"""

    # Qwen2.5-Instruct chat format
    prompt = (
        f"<|im_start|>system\n{system}<|im_end|>\n"
        f"<|im_start|>user\n{user_msg}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    return prompt


# ------------------------------------------------------------------
# Action parsing
# ------------------------------------------------------------------

_DIRECTIVE_DEFAULTS = {
    "action": "no_op",
    "parameters": {},
    "reasoning": "",
}


def parse_ic_action(completion: str, obs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse model completion → IC action dict.

    Strategy:
    1. Extract first JSON object from completion (lenient regex)
    2. Fill missing fields with safe defaults
    3. Never raise — always return a valid (if suboptimal) action
    """
    raw = _extract_json(completion)

    def _dir(key: str) -> Dict[str, Any]:
        val = raw.get(key)
        if isinstance(val, dict):
            return {**_DIRECTIVE_DEFAULTS, **val}
        return dict(_DIRECTIVE_DEFAULTS)

    resolution_confidence = float(raw.get("resolution_confidence", 0.0))
    resolution_confidence = max(0.0, min(1.0, resolution_confidence))

    action = {
        "situation_assessment": str(raw.get("situation_assessment", "")),
        "hypothesis": str(raw.get("hypothesis", "")),
        "coalition_vote": raw.get("coalition_vote"),
        "l1_directive": _dir("l1_directive"),
        "l2_directive": _dir("l2_directive"),
        "sre_directive": _dir("sre_directive"),
        "pm_directive": _dir("pm_directive"),
        "resolution_confidence": resolution_confidence,
        "escalation_required": bool(raw.get("escalation_required", False)),
    }

    # Null coalition_vote if not in investigation phase
    if obs and obs.get("phase") not in ("investigation", "mitigation"):
        action["coalition_vote"] = None

    return action


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from text. Returns {} on failure."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON block via brace matching
    start = text.find("{")
    if start == -1:
        return {}

    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break

    # Regex fallback — extract key-value pairs from partial JSON
    result: Dict[str, Any] = {}
    for key in ("situation_assessment", "hypothesis", "resolution_confidence", "escalation_required"):
        m = re.search(rf'"{key}"\s*:\s*("(?:[^"\\]|\\.)*"|\d+\.?\d*|true|false|null)', text)
        if m:
            try:
                result[key] = json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

    return result


# ------------------------------------------------------------------
# Inference engine
# ------------------------------------------------------------------

class NexusInferenceEngine:
    """
    Wraps Qwen2.5-1.5B-Instruct (or a LoRA checkpoint) for IC action generation.

    Designed for Colab with Unsloth 4-bit LoRA. Falls back to standard
    HuggingFace transformers if Unsloth is unavailable (e.g., local dev).

    Usage:
        engine = NexusInferenceEngine()
        engine.load("Qwen/Qwen2.5-1.5B-Instruct")
        action = engine.generate(observation)
    """

    MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
    MAX_NEW_TOKENS = 512
    TEMPERATURE = 0.7
    TOP_P = 0.9

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._use_unsloth = False

    def load(self, model_id: Optional[str] = None, lora_path: Optional[str] = None):
        """Load model. Tries Unsloth first, falls back to transformers."""
        model_id = model_id or self.MODEL_ID

        try:
            from unsloth import FastLanguageModel
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_id,
                max_seq_length=2048,
                dtype=None,  # Auto
                load_in_4bit=True,
            )
            if lora_path:
                self.model = FastLanguageModel.get_peft_model(self.model)
                self.model.load_adapter(lora_path)
            FastLanguageModel.for_inference(self.model)
            self._use_unsloth = True
            print(f"[NexusInference] Loaded {model_id} via Unsloth (4-bit LoRA)")

        except ImportError:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype=torch.float16,
                device_map="auto",
            )
            if lora_path:
                from peft import PeftModel
                self.model = PeftModel.from_pretrained(self.model, lora_path)
            self._use_unsloth = False
            print(f"[NexusInference] Loaded {model_id} via transformers (fp16)")

    def generate(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an IC action from an observation dict.
        Returns parsed action dict ready for env.step().
        """
        if self.model is None:
            raise RuntimeError("Call load() before generate()")

        prompt = build_ic_prompt(obs)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        import torch
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.MAX_NEW_TOKENS,
                temperature=self.TEMPERATURE,
                top_p=self.TOP_P,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only new tokens
        completion = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
        )
        return parse_ic_action(completion, obs)

    def generate_batch(
        self, obs: Dict[str, Any], n: int = 8
    ) -> list[tuple[str, Dict[str, Any]]]:
        """
        Generate n completions for the same observation (for GRPO group sampling).
        Returns list of (raw_completion, parsed_action) tuples.
        """
        if self.model is None:
            raise RuntimeError("Call load() before generate_batch()")

        prompt = build_ic_prompt(obs)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        import torch
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.MAX_NEW_TOKENS,
                temperature=self.TEMPERATURE,
                top_p=self.TOP_P,
                do_sample=True,
                num_return_sequences=n,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        results = []
        prompt_len = inputs["input_ids"].shape[1]
        for seq in outputs:
            completion = self.tokenizer.decode(
                seq[prompt_len:], skip_special_tokens=True
            )
            action = parse_ic_action(completion, obs)
            results.append((completion, action))

        return results


# ------------------------------------------------------------------
# CLI smoke test
# ------------------------------------------------------------------

if __name__ == "__main__":
    # Quick functional test without a real model — just verify prompt building and parsing
    sample_obs = {
        "session_id": "test-001",
        "incident_id": "INC003",
        "incident_title": "Memory Leak Under Load",
        "severity": "p2",
        "phase": "investigation",
        "step": 10,
        "elapsed_minutes": 20.0,
        "schema_version": "v1.0",
        "expert_criteria": "technical",
        "initial_alerts": [
            {"service": "recommendation-service", "metric": "memory_rss_gb", "value": 14.2, "threshold": 8.0, "status": "CRITICAL"},
            {"service": "search-service", "metric": "error_rate", "value": 0.08, "threshold": 0.10, "status": "OK"},
        ],
        "customer_reports": ["Recommendations page very slow", "Homepage not loading"],
        "affected_services": ["recommendation-service", "homepage-service"],
        "affected_regions": ["us-east-1"],
        "agent_findings": [
            {"agent": "l2_engineer", "finding": "recommendation-service heap at 14GB, OOM restarts every 90s", "step": 8},
        ],
        "competing_hypotheses": [
            "Network issue across recommendation and homepage services",
            "OOM on recommendation-service due to memory leak in new ML model",
        ],
        "oversight_findings": [],
        "runbooks_available": [
            {"step_id": "rb_heap_profile", "title": "Capture heap profile"},
            {"step_id": "rb_set_cache_eviction", "title": "Apply LRU eviction"},
        ],
        "runbook_steps_completed": ["rb_check_pod_restarts"],
        "notifications_sent": 1,
        "coalition_result": None,
        "escalation_done": True,
        "oversight_violations": 0,
    }

    print("=== Prompt ===")
    prompt = build_ic_prompt(sample_obs)
    print(prompt[:800], "...\n")

    print("=== Parse test (good JSON) ===")
    good_completion = json.dumps({
        "situation_assessment": "L2 confirms OOM on recommendation-service. Heap at 14GB. Deploying cache eviction fix.",
        "hypothesis": "ML model v4 feature vector cache lacks LRU eviction — unbounded heap growth",
        "coalition_vote": "OOM on recommendation-service due to memory leak in new ML model",
        "l1_directive": {"action": "send_notification", "parameters": {}, "reasoning": "Update customers"},
        "l2_directive": {"action": "query_metric", "parameters": {"service": "recommendation-service", "metric": "memory_rss_gb"}, "reasoning": "Confirm heap"},
        "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_set_cache_eviction"}, "reasoning": "Apply fix"},
        "pm_directive": {"action": "track_revenue_impact", "parameters": {}, "reasoning": "Revenue update"},
        "resolution_confidence": 0.85,
        "escalation_required": False,
    })
    action = parse_ic_action(good_completion, sample_obs)
    print(f"  resolution_confidence: {action['resolution_confidence']}")
    print(f"  coalition_vote: {action['coalition_vote']}")
    print(f"  sre step_id: {action['sre_directive']['parameters'].get('step_id')}")

    print("\n=== Parse test (malformed JSON) ===")
    bad_completion = '{"situation_assessment": "investigating...", "resolution_confidence": 0.3, broken json here'
    action2 = parse_ic_action(bad_completion, sample_obs)
    print(f"  situation_assessment: {action2['situation_assessment'][:40]}...")
    print(f"  resolution_confidence: {action2['resolution_confidence']}")

    print("\nAll inference smoke tests passed.")
