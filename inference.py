"""
inference.py — Run NEXUS Enhanced episodes with a scripted or LLM-backed IC policy.

Usage:
    # Scripted baseline on INC003 (no API key needed)
    python inference.py --incident INC003 --policy baseline

    # Run all 7 incidents once each with verbose output
    python inference.py --policy baseline --all-incidents --verbose

    # Run 5 episodes on medium difficulty, save results
    python inference.py --difficulty medium --episodes 5 --output results.json

    # LLM-backed IC (requires ANTHROPIC_API_KEY or OPENAI_API_KEY in env)
    python inference.py --incident INC003 --policy llm --model claude-haiku-4-5-20251001

    # Headless benchmark (used by train.py)
    python inference.py --incident INC003 --policy baseline --episodes 3 --quiet
"""

import os
import sys
import json
import argparse
import time
from typing import Dict, Optional, List

from client import NexusClient


# ---------------------------------------------------------------------------
# Scripted baseline policy
# ---------------------------------------------------------------------------

def baseline_policy(obs: Dict) -> Dict:
    """
    Deterministic scripted IC. Does sensible things at each phase.
    Used as the pre-training baseline and as the rollout-completion policy
    during GRPO training.
    """
    phase = obs.get("phase", "detection")
    step = obs.get("step", 0)
    incident_id = obs.get("incident_id", "INC003")
    competing = obs.get("competing_hypotheses", [])

    # Coalition vote: use last hypothesis once past step 8
    coalition_vote = None
    if competing and step >= 8:
        coalition_vote = competing[-1]

    # Resolution confidence: ramp up once in resolution/postmortem
    resolution_confidence = 0.0
    if phase in ("resolution", "postmortem"):
        resolution_confidence = min(0.92, 0.05 * step)
    elif step > 22:
        resolution_confidence = min(0.85, 0.04 * step)

    situation = (
        f"[Baseline] Phase={phase}, step={step}. "
        f"Continuing systematic investigation of {incident_id}. "
        f"Dispatching all agents for parallel evidence collection. "
        f"Evaluating root cause hypothesis based on accumulated findings."
    )

    return {
        "situation_assessment": situation,
        "hypothesis": "Root cause under systematic investigation via agent findings",
        "coalition_vote": coalition_vote,
        "l1_directive": {
            "action": "send_notification" if step <= 5 else "check_customer_reports",
            "parameters": {"message": "P1 incident under investigation", "severity": "high"} if step <= 5 else {},
            "reasoning": "Proactive customer communication on P1 incidents",
        },
        "l2_directive": {
            "action": "check_all_alerts" if step <= 3 else "query_logs",
            "parameters": {} if step <= 3 else {"service": obs.get("affected_services", ["unknown"])[0] if obs.get("affected_services") else "unknown"},
            "reasoning": "Systematic alert sweep then targeted log analysis",
        },
        "sre_directive": {
            "action": "list_runbooks" if step <= 6 else "execute_runbook_step",
            "parameters": {} if step <= 6 else {"step_id": "rb_check_logs"},
            "reasoning": "Enumerate options then execute correct runbook path",
        },
        "pm_directive": {
            "action": "track_revenue_impact",
            "parameters": {},
            "reasoning": "Continuous SLA and revenue impact monitoring",
        },
        "resolution_confidence": resolution_confidence,
        "escalation_required": step > 6,
    }


# ---------------------------------------------------------------------------
# LLM-backed policy (optional — requires API key)
# ---------------------------------------------------------------------------

def build_ic_prompt(obs: Dict) -> str:
    """Build ChatML-format prompt from current observation."""
    system = (
        "You are the Incident Commander (IC) for NEXUS, an enterprise incident response AI. "
        "Coordinate L1 Support, L2 Engineer, SRE, and Product Manager agents to resolve production incidents. "
        f"Expert review focus: {obs.get('expert_criteria', 'technical')}.\n\n"
        "Respond with valid JSON only:\n"
        '{"situation_assessment":"<multi-sentence analysis>","hypothesis":"<root cause>","coalition_vote":null,'
        '"l1_directive":{"action":"send_notification","parameters":{},"reasoning":""},'
        '"l2_directive":{"action":"check_all_alerts","parameters":{},"reasoning":""},'
        '"sre_directive":{"action":"list_runbooks","parameters":{},"reasoning":""},'
        '"pm_directive":{"action":"track_revenue_impact","parameters":{},"reasoning":""},'
        '"resolution_confidence":0.0,"escalation_required":false}'
    )

    alerts = obs.get("initial_alerts", [])
    if alerts and isinstance(alerts[0], dict) and "summary" in alerts[0]:
        alert_text = alerts[0]["summary"]
    else:
        alert_text = "; ".join(
            f"{a.get('service')}.{a.get('metric')}={a.get('value')} [{a.get('status','')}]"
            for a in alerts
        )

    findings = obs.get("agent_findings", [])
    finding_text = "\n".join(f"  [{f['agent']}] {f['finding']}" for f in findings[-5:]) or "  (none yet)"

    competing = obs.get("competing_hypotheses", [])
    hyp_text = ""
    if competing:
        hyp_text = "\nCOMPETING HYPOTHESES:\n" + "\n".join(f"  [{i+1}] {h}" for i, h in enumerate(competing))

    user = (
        f"INCIDENT [{obs.get('incident_id')}]: {obs.get('incident_title','')}\n"
        f"SEVERITY: {obs.get('severity','').upper()} | PHASE: {obs.get('phase','').upper()} "
        f"| STEP {obs.get('step',0)} | {obs.get('elapsed_minutes',0):.0f}min elapsed\n"
        f"SERVICES: {', '.join(obs.get('affected_services', ['unknown']))}\n"
        f"ALERTS: {alert_text}\n"
        f"AGENT FINDINGS:\n{finding_text}"
        f"{hyp_text}\n"
        f"NOTIFICATIONS: {obs.get('notifications_sent',0)} | VIOLATIONS: {obs.get('oversight_violations',0)}\n\n"
        "Respond with IC action JSON:"
    )

    return f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"


def parse_llm_action(text: str, obs: Dict) -> Dict:
    """Parse LLM completion into action dict. Falls back to baseline on parse error."""
    default_dir = {"action": "no_op", "parameters": {}, "reasoning": ""}

    def _extract(raw: dict, key: str) -> dict:
        v = raw.get(key)
        return {**default_dir, **v} if isinstance(v, dict) else dict(default_dir)

    # Try JSON parse
    try:
        raw = json.loads(text.strip())
    except Exception:
        # Try to extract JSON block
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                raw = json.loads(text[start:end+1])
            except Exception:
                return baseline_policy(obs)
        else:
            return baseline_policy(obs)

    conf = float(raw.get("resolution_confidence", 0.0))
    return {
        "situation_assessment": str(raw.get("situation_assessment", "")),
        "hypothesis": str(raw.get("hypothesis", "")),
        "coalition_vote": raw.get("coalition_vote"),
        "l1_directive": _extract(raw, "l1_directive"),
        "l2_directive": _extract(raw, "l2_directive"),
        "sre_directive": _extract(raw, "sre_directive"),
        "pm_directive": _extract(raw, "pm_directive"),
        "resolution_confidence": max(0.0, min(1.0, conf)),
        "escalation_required": bool(raw.get("escalation_required", False)),
    }


def make_llm_policy(model: str):
    """
    Return a policy function backed by an LLM.
    Supports claude-* (via anthropic) and gpt-* / openai (via openai).
    Falls back to baseline if no API key is set.
    """
    provider = None

    if model.startswith("claude"):
        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                print("[inference] ANTHROPIC_API_KEY not set — falling back to baseline")
                return baseline_policy
            client = anthropic.Anthropic(api_key=api_key)
            provider = "anthropic"
        except ImportError:
            print("[inference] anthropic package not installed — falling back to baseline")
            return baseline_policy

    elif model.startswith("gpt") or model.startswith("o"):
        try:
            import openai
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                print("[inference] OPENAI_API_KEY not set — falling back to baseline")
                return baseline_policy
            oai_client = openai.OpenAI(api_key=api_key)
            provider = "openai"
        except ImportError:
            print("[inference] openai package not installed — falling back to baseline")
            return baseline_policy
    else:
        print(f"[inference] Unknown model '{model}' — falling back to baseline")
        return baseline_policy

    def policy(obs: Dict) -> Dict:
        prompt = build_ic_prompt(obs)
        try:
            if provider == "anthropic":
                msg = client.messages.create(
                    model=model,
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = msg.content[0].text
            else:
                resp = oai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.7,
                )
                text = resp.choices[0].message.content
            return parse_llm_action(text, obs)
        except Exception as e:
            print(f"  [llm] error: {e} — using baseline")
            return baseline_policy(obs)

    return policy


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_episodes(
    client: NexusClient,
    policy,
    incidents: List[Optional[str]],
    difficulty: Optional[str],
    n_episodes: int,
    max_steps: int,
    verbose: bool,
    quiet: bool,
) -> List[Dict]:
    """Run episodes and collect results."""
    results = []
    total = len(incidents) if incidents else n_episodes

    for i in range(total):
        incident_id = incidents[i] if incidents else None
        label = incident_id or f"difficulty={difficulty or 'auto'}"

        if not quiet:
            print(f"\n[Episode {i+1}/{total}] {label}")

        t0 = time.time()
        result = client.run_episode(
            policy=policy,
            incident_id=incident_id,
            difficulty=difficulty if not incident_id else None,
            seed=i,
            max_steps=max_steps,
            verbose=verbose,
        )
        elapsed = time.time() - t0

        result["wall_time_s"] = round(elapsed, 2)
        results.append(result)

        if not quiet:
            rb = result["reward_breakdown"]
            print(
                f"  reward={result['reward']:.4f} steps={result['steps']} "
                f"done={result['done']} notif={result['notifications_sent']} "
                f"coalition={'✓' if result['coalition_correct'] else ('✗' if result['coalition_correct'] is False else '-')}"
            )
            if rb:
                print(
                    f"  breakdown: mttr={rb.get('mttr',0):.3f} diag={rb.get('diagnosis',0):.3f} "
                    f"cust={rb.get('customer',0):.3f} coord={rb.get('coordination',0):.3f} "
                    f"depth={rb.get('depth_bonus',0):.3f}"
                )

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NEXUS Enhanced inference — run IC policy on incidents"
    )
    parser.add_argument("--server", default="http://localhost:7860", help="NEXUS server URL")
    parser.add_argument("--incident", help="Specific incident ID (e.g. INC003)")
    parser.add_argument("--all-incidents", action="store_true", help="Run all 7 incidents once each")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard", "very_hard", "nightmare"],
                        help="Select incidents by difficulty (random if no --incident)")
    parser.add_argument("--episodes", type=int, default=1, help="Number of episodes to run")
    parser.add_argument("--policy", choices=["baseline", "llm"], default="baseline",
                        help="IC policy to use")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001",
                        help="Model ID for --policy llm")
    parser.add_argument("--max-steps", type=int, default=30, help="Max steps per episode")
    parser.add_argument("--output", help="Save results JSON to this path")
    parser.add_argument("--verbose", action="store_true", help="Print every step")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-episode output")
    args = parser.parse_args()

    client = NexusClient(args.server)

    # Verify server
    try:
        h = client.health()
        if not args.quiet:
            print(f"Server: {h.get('status')} | {h.get('environment','nexus-enhanced')} v{h.get('version','?')}")
    except Exception as e:
        print(f"Cannot reach server at {args.server}: {e}")
        sys.exit(1)

    # Build policy
    if args.policy == "llm":
        policy = make_llm_policy(args.model)
        if not args.quiet:
            print(f"Policy: LLM ({args.model})")
    else:
        policy = baseline_policy
        if not args.quiet:
            print("Policy: Scripted baseline")

    # Build incident list
    if args.all_incidents:
        incidents = [inc["case_id"] for inc in client.list_incidents()]
    elif args.incident:
        incidents = [args.incident] * args.episodes
    else:
        incidents = [None] * args.episodes

    # Run
    results = run_episodes(
        client=client,
        policy=policy,
        incidents=incidents,
        difficulty=args.difficulty,
        n_episodes=args.episodes,
        max_steps=args.max_steps,
        verbose=args.verbose,
        quiet=args.quiet,
    )

    # Summary
    if not args.quiet and len(results) > 1:
        rewards = [r["reward"] for r in results]
        avg = sum(rewards) / len(rewards)
        print(f"\n{'='*50}")
        print(f"Episodes: {len(results)} | Avg reward: {avg:.4f} | "
              f"Min: {min(rewards):.4f} | Max: {max(rewards):.4f}")
        print(f"{'='*50}")

    # Save
    if args.output:
        with open(args.output, "w") as f:
            json.dump({"policy": args.policy, "model": args.model, "results": results}, f, indent=2)
        if not args.quiet:
            print(f"\nResults saved → {args.output}")

    return results


if __name__ == "__main__":
    main()
