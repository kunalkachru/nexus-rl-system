---
title: NEXUS Enhanced
emoji: ⚡
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
tags:
  - reinforcement-learning
  - multi-agent
  - incident-response
  - openenv
  - grpo
  - pytorch
  - deployed
---

# ⚡ NEXUS Enhanced

**Multi-Agent Enterprise Incident Response RL Environment**  
*Meta PyTorch OpenEnv Hackathon Grand Finale — Team Falcons*

NEXUS Enhanced trains an AI Incident Commander to orchestrate 5 specialist agents across 7 production incident scenarios, culminating in a CrowdStrike-scale global failure affecting 8.5 million machines.

## Quick Start

```bash
pip install -r requirements.txt

# Run all tests (~220+)
pytest tests/ -q

# Start the server
uvicorn server.app:app --reload --port 7860

# Open the incident command dashboard
open http://localhost:7860/web

# Auto-demo (no server needed)
python -c "from server.app import run_demo; import json; print(json.dumps(run_demo('INC003'), indent=2))"
```

## Architecture

6 agents | 5 enterprise tools | 7 incident cases | OpenEnv v0.2.3

```
Incident Commander (IC)    ← trained via GRPO on Qwen2.5-1.5B
├── L1 Support             → SimSlack + SimCustomerPortal
├── L2 Engineer            → SimDatadog (rate-limited)
├── SRE Agent              → SimRunbook (schema drift v1→v2 in INC007)
├── Product Manager        → SimJira (VP approval + change freeze)
└── Oversight Agent        → monitor() + analyse() + explain()
```

Each agent has **partial observability** — only sees its role-scoped tool outputs. The IC synthesizes partial views into a coordinated incident response.

## Reward Model

```
episode_reward = (
    0.30 × mttr_score       # faster resolution
  + 0.25 × diagnosis_score  # root cause + evidence (anti-shortcut)
  + 0.20 × customer_score   # proactive notification required
  + 0.15 × coordination     # no duplicate tool queries
  + 0.05 × oversight        # protocol compliance
  + depth_bonus             # UNCAPPED reasoning quality (Mercor)
)
```

Expert criteria rotate every 4 episodes (speed/communication/technical/cost) — Snorkel AI sub-theme.

## Incident Library

| ID | Difficulty | Key Challenge |
|----|------------|---------------|
| INC001 | Easy | Payment service timeout |
| INC002 | Easy | DB pool exhaustion, cascade |
| **INC003** | **Medium** | **Red herrings + ML memory leak** ← primary demo |
| INC004 | Hard | Vendor retry storm, masked root cause |
| INC005 | Hard | JWT key mismatch, conflicting signals |
| INC006 | Very Hard | Multi-region CDN misrouting |
| INC007 | Nightmare | CrowdStrike-scale + live schema drift |

## Training

```bash
# GRPO fine-tuning (run in Colab with GPU)
# Open notebooks/grpo_colab.ipynb

# Pre-event baseline (30 episodes, avg reward 0.265)
python training/train.py --episodes 30 --difficulties easy,medium
```

## BRD hard gate — OpenEnv (reproduce)

Per [`../design/hackathon_brd.md`](../design/hackathon_brd.md) Section 17, judges expect **OpenEnv (latest release)** usage, not only a custom HTTP server.

**Local (dev machine, after `pip install "openenv>=0.2.3"`):**

```bash
cd nexus-enhanced
openenv validate .
pytest tests/ -q
uvicorn server.app:app --host 127.0.0.1 --port 7860
# second terminal:
openenv validate --url http://127.0.0.1:7860
```

**HF Space (after `openenv push`):** use your Space URL, e.g. `https://kunalkachru23-nexus-enhanced-stage.hf.space`:

```bash
openenv validate --url https://kunalkachru23-nexus-enhanced-stage.hf.space
./gate.sh --skip-regression --skip-local-api --hf-url https://kunalkachru23-nexus-enhanced-stage.hf.space
```

`requirements.txt` **omits** `openenv` on the Space Docker image to keep builds reliable; the **Colab notebook** installs `openenv>=0.2.3` for the training hard gate. Contract-only routes (`/metadata`, `/schema`, `GET /state`, `POST /mcp`) satisfy `openenv validate --url`; episode logic uses **`/reset`**, **`/step/{session_id}`**, **`/state/{session_id}`** only.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Start new episode |
| POST | `/step/{session_id}` | Execute IC action |
| GET | `/state/{session_id}` | Full episode state |
| GET | `/reward/{session_id}` | Live reward breakdown |
| POST | `/demo/run/{incident_id}` | Auto-demo mode |
| GET | `/web` | Incident command dashboard |
| GET | `/health` | Health (`status: healthy` for OpenEnv CLI) |
| GET | `/metadata` | OpenEnv discovery stub |
| GET | `/schema` | OpenEnv schema stub |
| GET | `/state` | OpenAPI stub (use `/state/{session_id}` for data) |
| POST | `/mcp` | OpenEnv JSON-RPC stub |
| GET | `/metrics` | Training metrics |

## Sub-Theme Coverage

- **Scaler AI Labs** — 5 enterprise tools with business rule nuances
- **Fleet AI** — OversightAgent: monitor + analyse + explain
- **Halluminate** — 6 agents + coalition debate + partial observability
- **Scale AI** — IT incident management domain
- **Mercor** — Uncapped reasoning depth bonus
- **Snorkel AI** — Rotating expert review board (4 criteria)
- **Patronus AI** — Live schema drift in INC007 at step 18

## Pitch, plan, and BRD evidence

Documentation lives under [`docs/`](docs/) (guides, deployment, project status, pitch/demo scripts, blog drafts).

- **[`docs/pitch/PITCH.md`](docs/pitch/PITCH.md)** — 3-minute spoken script + 2-minute Q&A bullets (BRD §18.1).
- **[`docs/project/PLAN_OF_ACTION.md`](docs/project/PLAN_OF_ACTION.md)** — BRD compliance matrix + prioritized todo table.
- **`scripts/export_reward_plot.py`** — export reward curve PNG from `--url` or `episode_rewards.json` (Criterion 3 slides).

## Blog Post

See [`docs/blog/blog_post.md`](docs/blog/blog_post.md) for the full HuggingFace blog post (1,300+ words, includes reward model deep-dive, training methodology, and demo walkthrough). **Publish** on HuggingFace and add the public URL for BRD §17.3.

## Team

Team Falcons — [kunalkachru23@gmail.com](mailto:kunalkachru23@gmail.com)
