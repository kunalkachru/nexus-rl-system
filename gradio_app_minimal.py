"""
NEXUS Enhanced - Minimal Gradio Dashboard
Stripped-down version for HF Spaces deployment reliability.
"""

import gradio as gr
import requests
import os
from typing import Dict, Any

API_BASE = os.getenv("API_BASE", "http://localhost:7862")

def get_incidents():
    """Get incident list with fallback to hardcoded values."""
    fallback = [
        "INC001: Payment Service Timeout",
        "INC002: Database Pool Exhaustion",
        "INC003: Memory Leak Under Load",
        "INC004: Third-Party API Failure",
        "INC005: Config Deployment Error",
        "INC006: Multi-Region CDN Misrouting",
        "INC007: CrowdStrike-Scale Global Failure",
    ]
    try:
        r = requests.get(f"{API_BASE}/incidents", timeout=3)
        if r.status_code == 200:
            incidents = r.json().get("incidents", [])
            if incidents:
                return [f"{inc['case_id']}: {inc['title']}" for inc in incidents]
    except:
        pass
    return fallback

def start_episode(incident: str, difficulty: str) -> str:
    """Start a new episode."""
    try:
        case_id = incident.split(":")[0]
        r = requests.post(f"{API_BASE}/reset", json={"incident_id": case_id, "difficulty": difficulty}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return f"✅ Episode started\nSession: {data.get('session_id', 'N/A')}\n\n{data.get('observation', {}).get('incident_title', 'Starting...')}"
        return f"❌ Error: {r.status_code}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

try:
    incidents = get_incidents()

    with gr.Blocks(title="NEXUS Enhanced") as demo:
        gr.Markdown("# 🚨 NEXUS Enhanced\nMulti-Agent Enterprise Incident Response RL Environment")

        with gr.Row():
            incident_select = gr.Dropdown(incidents, value=incidents[0], label="Select Incident")
            difficulty_select = gr.Radio(["easy", "medium", "hard", "very_hard", "nightmare"], value="medium", label="Difficulty")

        start_btn = gr.Button("🚀 Start Episode", variant="primary")
        output = gr.Textbox(label="Status", interactive=False, lines=5)

        start_btn.click(start_episode, inputs=[incident_select, difficulty_select], outputs=output)

        gr.Markdown("---")
        gr.Markdown("**Status:** Ready")

    if __name__ == "__main__":
        print(f"[APP] Starting NEXUS Gradio on {API_BASE}")
        demo.launch(server_name="0.0.0.0", share=False, theme=gr.themes.Soft(primary_hue="blue"))

except Exception as e:
    print(f"[ERROR] Failed to create UI: {e}")
    import traceback
    traceback.print_exc()

    # Fallback: simple emergency interface
    with gr.Blocks(title="NEXUS Enhanced") as demo:
        gr.Markdown("# ⚠️ NEXUS Enhanced (Limited Mode)")
        gr.Markdown(f"Application error: {str(e)}")
        gr.Markdown("The backend may not be ready. Retrying...")

    if __name__ == "__main__":
        demo.launch(server_name="0.0.0.0", share=False)
