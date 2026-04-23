"""
NEXUS Enhanced - Long-Run GRPO (Resumable) companion script.

Purpose:
- Keep `grpo_colab_v2.ipynb` unchanged for normal runs.
- Provide a separate resumable path for longer training where Colab can disconnect.

How to use in Colab:
1) Mount Drive:
     from google.colab import drive
     drive.mount("/content/drive")
2) Put this repo in `/content/nexus-enhanced` (or adjust paths below).
3) Set env vars (optional), then run:
     !python notebooks/grpo_colab_longrun_resumable.py

Core behavior:
- Saves checkpoints to a Drive-backed directory by default.
- On restart, auto-detects the latest checkpoint and resumes from it.
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Optional

import requests
import torch
from datasets import Dataset
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastLanguageModel


def _env(name: str, default, cast=str):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    if cast is bool:
        return str(raw).lower() in {"1", "true", "yes", "y", "on"}
    return cast(raw)


# ---------------------------
# Configuration
# ---------------------------
BASE_URL = _env("NEXUS_HF_SPACE_URL", "https://kunalkachru23-nexus-enhanced-stage.hf.space").rstrip("/")
TRAINING_INCIDENT_ID = _env("NEXUS_INCIDENT_ID", "INC003")

MODEL_NAME = _env("NEXUS_MODEL_NAME", "unsloth/Qwen2.5-1.5B-Instruct")
MAX_SEQ_LENGTH = _env("NEXUS_MAX_SEQ_LENGTH", 1024, int)
REWARD_MAX_STEPS = _env("NEXUS_REWARD_MAX_STEPS", 28, int)

# Long-run defaults (override with env vars as needed)
N_PROMPTS_LONG = _env("NEXUS_LONG_PROMPTS", 240, int)
GRPO_LR = _env("NEXUS_GRPO_LR", 5e-5, float)
GRPO_EPOCHS = _env("NEXUS_GRPO_EPOCHS", 1, int)
GRPO_BATCH = _env("NEXUS_GRPO_BATCH_LONG", 2, int)
GRPO_NUM_GEN = _env("NEXUS_GRPO_NUM_GEN_LONG", 4, int)
GRPO_LOGGING_STEPS = _env("NEXUS_GRPO_LOGGING_STEPS", 1, int)
GRPO_SAVE_STEPS = _env("NEXUS_GRPO_SAVE_STEPS_LONG", 5, int)

PEFT_R = _env("NEXUS_PEFT_R", 16, int)
PEFT_ALPHA = _env("NEXUS_PEFT_ALPHA", 16, int)
PEFT_DROPOUT = _env("NEXUS_PEFT_DROPOUT", 0.05, float)

# Separate output dir from standard notebook for flexibility.
DEFAULT_RESUME_DIR = "/content/drive/MyDrive/NEXUS_GRPO_backups/resumable_longrun/grpo_checkpoints"
GRPO_OUTPUT_DIR = _env("NEXUS_GRPO_OUTPUT_DIR_LONG_RESUME", DEFAULT_RESUME_DIR)
AUTO_RESUME = _env("NEXUS_AUTO_RESUME", True, bool)


class NexusRemoteEnv:
    def reset(self, incident_id: Optional[str] = None):
        if incident_id is None:
            incident_id = TRAINING_INCIDENT_ID
        resp = requests.post(
            f"{BASE_URL}/reset",
            json={"incident_id": incident_id, "difficulty": None, "seed": None},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["session_id"], data["observation"]

    def step(self, session_id: str, action: dict):
        resp = requests.post(
            f"{BASE_URL}/step/{session_id}",
            json=action,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["observation"], data["reward"], data["done"], data["info"]


def parse_ic_action(completion_text: str) -> dict:
    situation = completion_text[:200] if len(completion_text) > 200 else completion_text
    situation = situation.split("==")[0].strip() if "==" in situation else situation.strip()

    hypothesis_match = re.search(r"hypothesis[:\s]+([^\n.]+)", completion_text, re.IGNORECASE)
    hypothesis = hypothesis_match.group(1).strip() if hypothesis_match else situation[:50]

    coalition_match = re.search(r"coalition[:\s]+([^\n.]+)", completion_text, re.IGNORECASE)
    coalition_vote = coalition_match.group(1).strip() if coalition_match else None

    return {
        "situation_assessment": situation,
        "hypothesis": hypothesis,
        "coalition_vote": coalition_vote,
        "l1_directive": {"action": "send_notification", "parameters": {}, "reasoning": ""},
        "l2_directive": {"action": "check_all_alerts", "parameters": {}, "reasoning": ""},
        "sre_directive": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
        "pm_directive": {"action": "check_sla_status", "parameters": {}, "reasoning": ""},
        "severity_assessment": "p2",
        "resolution_confidence": 0.75,
        "escalation_required": False,
    }


def build_reward_fn():
    env = NexusRemoteEnv()

    def reward_fn(completions, **kwargs):
        rewards = []
        for completion_text in completions:
            try:
                session_id, _ = env.reset()
                done = False
                step_count = 0
                reward = 0.0
                while not done and step_count < REWARD_MAX_STEPS:
                    action = parse_ic_action(completion_text)
                    _, reward, done, _ = env.step(session_id, action)
                    step_count += 1
                    if reward > 0:
                        break
                rewards.append(reward)
            except Exception:
                rewards.append(0.0)
        return rewards

    return reward_fn


def latest_checkpoint(output_dir: str) -> Optional[str]:
    pattern = os.path.join(output_dir, "checkpoint-*")
    candidates = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: int(p.rsplit("-", 1)[-1]))


def build_long_prompt_dataset(n_prompts: int) -> Dataset:
    prompt_pool = [
        "You are an Incident Commander. INC003: ML model cache memory leak. What is your assessment?",
        "Analyze recommendation-service memory at 96%, GC pauses 4.2s. Root cause hypothesis?",
        "Evidence shows ML model v4 cache unbounded. What mitigation steps now?",
        "System shows cache eviction needed. What sequence should SRE execute?",
        "Customer impact: 320k users affected. What comms and escalation actions are needed?",
        "Hypothesis: LRU eviction missing. Confidence and evidence?",
        "Running rb_heap_profile - what does it reveal about memory allocation?",
        "Cache configuration max_size=unlimited. Should we change this now?",
        "Coalition debate: code bug vs config issue. Your vote and rationale?",
        "Runbook step rb_set_cache_eviction is available. Execute now?",
    ]
    repeats = (n_prompts + len(prompt_pool) - 1) // len(prompt_pool)
    prompts = (prompt_pool * repeats)[:n_prompts]
    return Dataset.from_dict({"prompt": prompts})


def main():
    print("=" * 72)
    print("NEXUS GRPO LONG-RUN (RESUMABLE)")
    print("=" * 72)
    print(f"BASE_URL={BASE_URL}")
    print(f"MODEL_NAME={MODEL_NAME}")
    print(f"N_PROMPTS_LONG={N_PROMPTS_LONG}")
    print(f"GRPO_OUTPUT_DIR={GRPO_OUTPUT_DIR}")
    print(f"AUTO_RESUME={AUTO_RESUME}")

    os.makedirs(GRPO_OUTPUT_DIR, exist_ok=True)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
        dtype=torch.bfloat16,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=PEFT_R,
        lora_alpha=PEFT_ALPHA,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=PEFT_DROPOUT,
        bias="none",
        use_gradient_checkpointing=True,
        use_rslora=True,
    )

    config = GRPOConfig(
        output_dir=GRPO_OUTPUT_DIR,
        learning_rate=GRPO_LR,
        per_device_train_batch_size=GRPO_BATCH,
        num_train_epochs=GRPO_EPOCHS,
        num_generations=GRPO_NUM_GEN,
        logging_steps=GRPO_LOGGING_STEPS,
        save_steps=GRPO_SAVE_STEPS,
    )

    train_dataset = build_long_prompt_dataset(N_PROMPTS_LONG)
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=build_reward_fn(),
        args=config,
        train_dataset=train_dataset,
    )

    resume_ckpt = latest_checkpoint(GRPO_OUTPUT_DIR) if AUTO_RESUME else None
    if resume_ckpt:
        print(f"Resuming from checkpoint: {resume_ckpt}")
        trainer.train(resume_from_checkpoint=resume_ckpt)
    else:
        print("No checkpoint found (or AUTO_RESUME disabled), starting fresh.")
        trainer.train()

    print("Training finished.")
    print(f"Checkpoints saved in: {GRPO_OUTPUT_DIR}")
    print(f"Monitor: {BASE_URL}/")
    print("=" * 72)


if __name__ == "__main__":
    main()
