"""
grpo_train.py — GRPO fine-tuning of Qwen2.5-1.5B on NEXUS episodes.

Uses HuggingFace TRL GRPOTrainer + Unsloth 4-bit LoRA.
Designed to run in Colab with HuggingFace on-site compute (April 25–26).

Algorithm:
  For each training step:
    1. Sample G=8 IC action completions from the current model (group)
    2. Execute each action in the NEXUS environment (first step of episode,
       then complete with scripted baseline policy)
    3. Use final episode reward as GRPO reward signal
    4. Normalize rewards within the group → advantage estimate
    5. Compute GRPO policy gradient loss + update model

Reward function (per the plan):
  Calls NEXUS environment directly (not via HTTP) for speed.
  Single first-step evaluation: model generates step-1 action,
  episode completes via baseline policy, final reward attributed.

Run locally (CPU mock):
    python training/grpo_train.py --dry-run

Run in Colab (GPU):
    python training/grpo_train.py \
      --model Qwen/Qwen2.5-1.5B-Instruct \
      --steps 200 \
      --group-size 8 \
      --push-to-hub YOUR_USERNAME/nexus-qwen-1.5b
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ------------------------------------------------------------------
# Environment reward function (direct import — no HTTP overhead)
# ------------------------------------------------------------------

def build_nexus_reward_fn(server_url: str = "http://localhost:7860"):
    """
    Returns a TRL-compatible reward function:
        reward_fn(prompts, completions, **kwargs) -> list[float]

    Each (prompt, completion) pair is evaluated by:
    1. Extracting incident_id from the prompt
    2. Resetting a fresh environment for that incident
    3. Parsing the completion as a step-1 IC action
    4. Running the episode to completion with the baseline policy
    5. Returning the final episode reward
    """
    from training.client import NexusClient, _baseline_policy
    from training.inference import parse_ic_action

    client = NexusClient(server_url)

    def reward_fn(
        prompts: List[str],
        completions: List[str],
        **kwargs,
    ) -> List[float]:
        rewards = []

        for prompt, completion in zip(prompts, completions):
            try:
                # Extract incident_id from prompt (embedded in first user line)
                incident_id = _extract_incident_id(prompt)

                # Reset environment for this incident
                session_id, obs = client.reset(incident_id=incident_id)

                # Parse completion as IC action
                action = parse_ic_action(completion, obs)

                # Execute step 1 with the model's action
                obs, reward, done, info = client.step(session_id, action)

                # Complete remaining steps with baseline policy
                step = 1
                max_steps = 20  # Cap rollout for training speed
                while not done and step < max_steps:
                    baseline_action = _baseline_policy(obs)
                    obs, reward, done, info = client.step(session_id, baseline_action)
                    step += 1

                # Extract final reward
                if done and reward > 0:
                    episode_reward = reward
                else:
                    # Episode timed out — get partial reward from state
                    state = client.get_reward(session_id)
                    episode_reward = state.get("total", 0.0)

                rewards.append(float(episode_reward))

            except Exception as e:
                # Never crash training — return 0 reward for failed rollouts
                rewards.append(0.0)
                print(f"[grpo_reward] Rollout failed: {e}")

        return rewards

    return reward_fn


def _extract_incident_id(prompt: str) -> str:
    """Extract incident ID from formatted prompt string."""
    import re
    m = re.search(r"\[(INC\d+)\]", prompt)
    if m:
        return m.group(1)
    # Fallback: cycle through incidents
    return "INC003"


# ------------------------------------------------------------------
# Training dataset
# ------------------------------------------------------------------

def build_grpo_dataset(
    server_url: str = "http://localhost:7860",
    n_prompts: int = 100,
    difficulties: Optional[List[str]] = None,
) -> "datasets.Dataset":
    """
    Build a HuggingFace Dataset of IC prompts for GRPO training.

    Each example: {"prompt": "<Qwen2.5 chat-formatted IC observation>"}
    The dataset is regenerated from fresh environment resets so observations
    vary across training — no static dataset that could be memorized.
    """
    from datasets import Dataset
    from training.client import NexusClient
    from training.inference import build_ic_prompt

    if difficulties is None:
        difficulties = ["easy", "medium", "hard"]

    incident_pool = {
        "easy": ["INC001", "INC002", "INC008"],
        "medium": ["INC003", "INC004"],
        "hard": ["INC005", "INC006"],
        "nightmare": ["INC007"],
    }

    client = NexusClient(server_url)
    prompts = []

    for i in range(n_prompts):
        difficulty = difficulties[i % len(difficulties)]
        incidents = incident_pool.get(difficulty, ["INC001"])
        incident_id = incidents[i % len(incidents)]

        try:
            session_id, obs = client.reset(incident_id=incident_id)
            prompt = build_ic_prompt(obs)
            prompts.append({"prompt": prompt})
        except Exception as e:
            print(f"[dataset] Skipping prompt {i}: {e}")
            # Use a minimal fallback prompt
            prompts.append({"prompt": f"<|im_start|>user\nInvestigate {incident_id}<|im_end|>\n<|im_start|>assistant\n"})

    return Dataset.from_list(prompts)


# ------------------------------------------------------------------
# GRPO training loop
# ------------------------------------------------------------------

def run_grpo_training(
    model_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
    server_url: str = "http://localhost:7860",
    n_steps: int = 200,
    group_size: int = 8,
    learning_rate: float = 5e-6,
    batch_size: int = 1,
    n_prompts: int = 100,
    output_dir: str = "./training_artifacts/grpo_checkpoint",
    push_to_hub: Optional[str] = None,
    difficulties: Optional[List[str]] = None,
    dry_run: bool = False,
) -> None:
    """
    Full GRPO fine-tuning run. Called from Colab notebook Cell 4.

    Args:
        model_id: Base model to fine-tune
        server_url: NEXUS environment server URL
        n_steps: Total GRPO update steps
        group_size: G — completions per prompt per step
        learning_rate: AdamW learning rate
        batch_size: Prompts per gradient step (keep at 1 for memory)
        n_prompts: Dataset size (prompts cycled during training)
        output_dir: Where to save LoRA checkpoint
        push_to_hub: HF repo ID to push checkpoint (optional)
        difficulties: Which difficulty tiers to sample from
        dry_run: Skip model loading — just verify config and dataset
    """
    from training.client import NexusClient

    if difficulties is None:
        difficulties = ["easy", "medium"]

    print("=" * 60)
    print("  NEXUS Enhanced — GRPO Fine-Tuning")
    print("=" * 60)
    print(f"  Model      : {model_id}")
    print(f"  Steps      : {n_steps}")
    print(f"  Group size : {group_size}")
    print(f"  LR         : {learning_rate}")
    print(f"  Dataset    : {n_prompts} prompts ({', '.join(difficulties)})")
    print(f"  Output     : {output_dir}")
    print(f"  Hub push   : {push_to_hub or 'disabled'}")
    print()

    # Verify server is up
    client = NexusClient(server_url)
    if not dry_run:
        if not client.wait_until_ready(max_wait=60):
            raise RuntimeError(f"NEXUS server not ready at {server_url}")
        print(f"[grpo] Server ready at {server_url}")

    # Build dataset
    print("[grpo] Building training dataset...")
    if dry_run:
        from datasets import Dataset
        dataset = Dataset.from_list([{"prompt": f"<|im_start|>user\ntest<|im_end|>\n<|im_start|>assistant\n"}] * 10)
        print(f"[grpo] Dry-run dataset: {len(dataset)} prompts")
    else:
        dataset = build_grpo_dataset(server_url, n_prompts, difficulties)
        print(f"[grpo] Dataset ready: {len(dataset)} prompts")

    if dry_run:
        print("\n[grpo] DRY RUN complete — config and dataset verified.")
        print("  Remove --dry-run to start real training.")
        return

    # Load model via Unsloth
    print(f"\n[grpo] Loading {model_id} via Unsloth...")
    try:
        from unsloth import FastLanguageModel
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_id,
            max_seq_length=2048,
            dtype=None,
            load_in_4bit=True,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0.0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=42,
        )
        print("[grpo] Model loaded via Unsloth (4-bit LoRA, r=16)")
    except ImportError:
        print("[grpo] Unsloth not available — falling back to standard transformers + PEFT")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import get_peft_model, LoraConfig, TaskType
        import torch

        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=torch.bfloat16, device_map="auto"
        )
        lora_config = LoraConfig(
            r=16,
            lora_alpha=16,
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
            lora_dropout=0.0,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Build reward function
    reward_fn = build_nexus_reward_fn(server_url)

    # Configure GRPO
    from trl import GRPOConfig, GRPOTrainer

    grpo_config = GRPOConfig(
        output_dir=output_dir,
        num_train_epochs=1,
        max_steps=n_steps,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=1,
        learning_rate=learning_rate,
        warmup_steps=max(1, n_steps // 20),
        lr_scheduler_type="cosine",
        optim="adamw_8bit",

        # GRPO-specific
        num_generations=group_size,
        max_completion_length=512,
        max_prompt_length=1024,
        temperature=0.7,
        top_p=0.9,
        beta=0.04,  # KL penalty coefficient

        # Logging
        logging_steps=5,
        save_steps=50,
        save_total_limit=3,

        # HF Hub
        push_to_hub=push_to_hub is not None,
        hub_model_id=push_to_hub,

        # Reproducibility
        seed=42,
        report_to="none",  # Use manual logging below
    )

    # Initialize trainer
    trainer = GRPOTrainer(
        model=model,
        reward_funcs=[reward_fn],
        args=grpo_config,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # Train
    print(f"\n[grpo] Starting GRPO training — {n_steps} steps, G={group_size}...")
    t0 = time.time()
    trainer.train()
    elapsed = time.time() - t0

    print(f"\n[grpo] Training complete in {elapsed/60:.1f}min")

    # Save checkpoint
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"[grpo] Checkpoint saved → {output_dir}")

    # Save training log
    log_path = Path(output_dir) / "training_log.json"
    log_data = {
        "model_id": model_id,
        "n_steps": n_steps,
        "group_size": group_size,
        "learning_rate": learning_rate,
        "difficulties": difficulties,
        "elapsed_minutes": round(elapsed / 60, 2),
        "output_dir": output_dir,
        "push_to_hub": push_to_hub,
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
    print(f"[grpo] Training log saved → {log_path}")

    # Push to HuggingFace Hub
    if push_to_hub:
        print(f"\n[grpo] Pushing to HuggingFace Hub: {push_to_hub}")
        trainer.push_to_hub()
        print(f"[grpo] Model available at: https://huggingface.co/{push_to_hub}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="NEXUS GRPO fine-tuning")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--url", default="http://localhost:7860", help="NEXUS server URL")
    parser.add_argument("--steps", type=int, default=200, help="GRPO update steps")
    parser.add_argument("--group-size", type=int, default=8, dest="group_size")
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--batch-size", type=int, default=1, dest="batch_size")
    parser.add_argument("--n-prompts", type=int, default=100, dest="n_prompts")
    parser.add_argument("--output-dir", default="./training_artifacts/grpo_checkpoint", dest="output_dir")
    parser.add_argument("--push-to-hub", default=None, dest="push_to_hub", help="HF repo ID")
    parser.add_argument(
        "--difficulties", default="easy,medium",
        help="Comma-separated difficulty list"
    )
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Verify config and dataset without training")
    args = parser.parse_args()

    run_grpo_training(
        model_id=args.model,
        server_url=args.url,
        n_steps=args.steps,
        group_size=args.group_size,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        n_prompts=args.n_prompts,
        output_dir=args.output_dir,
        push_to_hub=args.push_to_hub,
        difficulties=[d.strip() for d in args.difficulties.split(",")],
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
