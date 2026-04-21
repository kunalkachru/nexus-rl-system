"""NEXUS Enhanced - Gradio UI with direct environment access"""
import sys
print("[START] Initializing Gradio app...", flush=True)

import gradio as gr
from server.environment import NexusEnvironment
from server.incidents import INCIDENT_LIBRARY

print("[1] Imports successful", flush=True)

# Create a single environment instance for all sessions
env = NexusEnvironment()

# Get incident list from the library directly
incidents_list = [f"{case.case_id}: {case.title}" for case in INCIDENT_LIBRARY.values()]
print(f"[2] Loaded {len(incidents_list)} incidents", flush=True)

session_state = {
    "session_id": None,
    "observation": None,
}

def start_episode(incident_str: str, difficulty: str) -> str:
    """Start a new episode."""
    try:
        case_id = incident_str.split(":")[0].strip()
        print(f"[ACTION] Starting episode: {case_id} ({difficulty})", flush=True)

        obs = env.reset(incident_id=case_id)
        session_state["observation"] = obs

        title = obs.get("incident_title", "Unknown")
        severity = obs.get("severity", "N/A")
        phase = obs.get("phase", "detection")

        return f"""✅ Episode Started

Incident: {title}
Severity: {severity}
Phase: {phase}
Elapsed: {obs.get('elapsed_minutes', 0):.1f} min

Ready to begin incident response coordination."""
    except Exception as e:
        print(f"[ERROR] Failed to start episode: {e}", flush=True)
        return f"❌ Error: {str(e)}"

def step_action(situation: str, hypothesis: str, confidence: float) -> str:
    """Execute one step of the episode."""
    if not session_state["observation"]:
        return "❌ No active episode. Start an episode first."

    try:
        print(f"[STEP] Assessment: {situation}, Hypothesis: {hypothesis}", flush=True)
        obs, reward, done, info = env.step({
            "situation_assessment": situation,
            "hypothesis": hypothesis,
            "resolution_confidence": confidence,
        })

        session_state["observation"] = obs

        result = f"✅ Step Complete\n\nPhase: {obs.get('phase')}\nStep: {obs.get('step')}/{obs.get('max_steps')}\nReward: {reward:.4f}"

        if done:
            result += "\n\n🎉 Episode Complete!"

        return result
    except Exception as e:
        print(f"[ERROR] Step failed: {e}", flush=True)
        return f"❌ Error: {str(e)}"

print("[3] Building UI...", flush=True)

with gr.Blocks(title="NEXUS Enhanced") as demo:
    gr.Markdown("# 🚨 NEXUS Enhanced\n### Multi-Agent Enterprise Incident Response RL Environment")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚡ Start Episode")
            incident = gr.Dropdown(incidents_list, value=incidents_list[2], label="Select Incident")
            difficulty = gr.Radio(["easy", "medium", "hard", "very_hard", "nightmare"], value="medium", label="Difficulty")
            start_btn = gr.Button("🚀 Start Episode", variant="primary", size="lg")
            status_output = gr.Textbox(label="Status", lines=6, interactive=False)

        with gr.Column(scale=1):
            gr.Markdown("### 🎮 Episode Control")
            situation = gr.Textbox(label="Situation Assessment", placeholder="Describe your understanding of the situation...")
            hypothesis = gr.Textbox(label="Root Cause Hypothesis", placeholder="What do you think caused this incident?")
            confidence = gr.Slider(0, 1, value=0.5, label="Confidence Level")
            step_btn = gr.Button("→ Execute Step", variant="secondary")
            step_output = gr.Textbox(label="Step Result", lines=6, interactive=False)

    gr.Markdown("---")
    gr.Markdown("**Status:** Ready to train incident response coordination")

    start_btn.click(start_episode, [incident, difficulty], status_output)
    step_btn.click(step_action, [situation, hypothesis, confidence], step_output)

print("[4] Launching server...", flush=True)
sys.stdout.flush()

demo.launch(server_name="0.0.0.0", server_port=7860, share=False)

print("[5] Server running", flush=True)
