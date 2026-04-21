"""
NEXUS Enhanced — Gradio Dashboard
Primary UI for the hackathon demo.
Falls back to vanilla HTML if broken.

Deployment:
  - Local: python gradio_app.py
  - Docker: docker build -t nexus . && docker run -p 7860:7860 nexus
  - HF Spaces: Build locally, push to HF via CLI or web UI
"""

import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import os
from typing import Dict, Any, Optional, List

# ============================================================================
# CONFIG
# ============================================================================

# Backend API base URL
# Local testing: http://localhost:7862
# HF Spaces: Use environment variable, fallback to localhost
API_BASE = os.getenv("API_BASE", "http://localhost:7862")

# ============================================================================
# STATE & CACHING
# ============================================================================

class AppState:
    """Maintains session state across Gradio interactions."""
    def __init__(self):
        self.session_id: Optional[str] = None
        self.current_obs: Optional[Dict] = None
        self.episode_data: List[Dict] = []
        self.metrics_cache: Optional[Dict] = None
        self.incidents_cache: List[Dict] = []

app_state = AppState()

# ============================================================================
# API HELPERS
# ============================================================================

def fetch_incidents() -> List[Dict]:
    """Fetch all incidents from backend."""
    try:
        response = requests.get(f"{API_BASE}/incidents", timeout=5)
        if response.status_code == 200:
            app_state.incidents_cache = response.json().get("incidents", [])
            return app_state.incidents_cache
        return app_state.incidents_cache
    except Exception as e:
        print(f"Error fetching incidents: {e}")
        return app_state.incidents_cache or []

def reset_episode(incident_id: str, difficulty: Optional[str]) -> Dict:
    """Start new episode."""
    try:
        payload = {"incident_id": incident_id}
        if difficulty:
            payload["difficulty"] = difficulty
        response = requests.post(f"{API_BASE}/reset", json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            app_state.session_id = data.get("session_id")
            app_state.current_obs = data.get("observation", {})
            app_state.episode_data = []
            return data
        return {"error": f"Status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def execute_step(assessment: str, hypothesis: str, confidence: float,
                 dispatch_l2: bool, dispatch_l1: bool, dispatch_sre: bool,
                 dispatch_pm: bool, sre_step: Optional[str]) -> Dict:
    """Execute one IC action."""
    if not app_state.session_id:
        return {"error": "No active session"}

    try:
        action = {
            "situation_assessment": assessment,
            "hypothesis": hypothesis,
            "resolution_confidence": float(confidence),
        }

        # Add specialist directives
        if dispatch_l2:
            action["l2_directive"] = {
                "action": "check_all_alerts",
                "parameters": {},
                "reasoning": "Investigate metrics and alerts"
            }
        if dispatch_l1:
            action["l1_directive"] = {
                "action": "check_customer_reports",
                "parameters": {},
                "reasoning": "Check customer impact and communicate"
            }
        if dispatch_sre and sre_step:
            action["sre_directive"] = {
                "action": "execute_runbook_step",
                "parameters": {"step_id": sre_step},
                "reasoning": "Execute infrastructure step"
            }
        if dispatch_pm:
            action["pm_directive"] = {
                "action": "track_revenue_impact",
                "parameters": {},
                "reasoning": "Track business impact"
            }

        response = requests.post(f"{API_BASE}/step/{app_state.session_id}",
                               json=action, timeout=10)
        if response.status_code == 200:
            data = response.json()
            app_state.current_obs = data.get("observation", {})
            app_state.episode_data.append(data)
            return data
        return {"error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def fetch_metrics() -> Dict:
    """Fetch training metrics from backend."""
    try:
        response = requests.get(f"{API_BASE}/training-metrics", timeout=10)
        if response.status_code == 200:
            app_state.metrics_cache = response.json()
            return response.json()
        return {"error": f"Status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# CHART BUILDERS
# ============================================================================

def build_reward_curve(metrics: Dict) -> go.Figure:
    """Build reward curve chart."""
    if "error" in metrics or not metrics.get("rewards"):
        fig = go.Figure()
        fig.add_annotation(text="No data available yet", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=16))
        return fig

    rewards = metrics.get("rewards", [])
    if not rewards:
        fig = go.Figure()
        fig.add_annotation(text="No data available yet", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    episodes = list(range(len(rewards)))

    # Calculate rolling average
    window = 5
    rolling = [
        sum(rewards[max(0, i-window):i+1]) / min(i+1, window)
        for i in range(len(rewards))
    ]

    fig = go.Figure()

    # Episode rewards
    fig.add_trace(go.Scatter(
        x=episodes, y=rewards,
        mode='lines+markers',
        name='Episode Reward',
        line=dict(color='#60a5fa', width=2),
        marker=dict(size=4, opacity=0.6)
    ))

    # Rolling average
    fig.add_trace(go.Scatter(
        x=episodes, y=rolling,
        mode='lines',
        name='5-Episode Rolling Avg',
        line=dict(color='#a78bfa', width=3, dash='dash')
    ))

    # Baseline
    baseline = metrics.get("baseline", {}).get("reward", 0.265)
    fig.add_hline(y=baseline, line_dash="dot", line_color="#94a3b8",
                  annotation_text="Baseline (Untrained)", annotation_position="right")

    fig.update_layout(
        title="Training Progress: Reward Curve",
        xaxis_title="Episode",
        yaxis_title="Total Reward",
        hovermode='x unified',
        template="plotly_dark",
        height=400,
        showlegend=True
    )

    return fig

def build_dimension_breakdown(metrics: Dict) -> go.Figure:
    """Build reward dimension breakdown chart."""
    if "error" in metrics or not metrics.get("rewards"):
        fig = go.Figure()
        fig.add_annotation(text="No data available yet", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    dimensions = metrics.get("dimensions", {})

    # Get last 5 episodes
    mttr = dimensions.get("mttr", [])[-5:] if dimensions.get("mttr") else []
    diagnosis = dimensions.get("diagnosis", [])[-5:] if dimensions.get("diagnosis") else []
    customer = dimensions.get("customer", [])[-5:] if dimensions.get("customer") else []
    coordination = dimensions.get("coordination", [])[-5:] if dimensions.get("coordination") else []
    oversight = dimensions.get("oversight", [])[-5:] if dimensions.get("oversight") else []
    depth = dimensions.get("depth", [])[-5:] if dimensions.get("depth") else []

    if not mttr:
        fig = go.Figure()
        fig.add_annotation(text="No dimension data yet", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False)
        return fig

    episodes = [f"Ep {i}" for i in range(len(mttr))]

    fig = go.Figure()

    fig.add_trace(go.Bar(x=episodes, y=mttr, name="MTTR (30%)", marker_color="#4ade80"))
    fig.add_trace(go.Bar(x=episodes, y=diagnosis, name="Diagnosis (25%)", marker_color="#60a5fa"))
    fig.add_trace(go.Bar(x=episodes, y=customer, name="Customer (20%)", marker_color="#f59e0b"))
    fig.add_trace(go.Bar(x=episodes, y=coordination, name="Coordination (15%)", marker_color="#a78bfa"))
    fig.add_trace(go.Bar(x=episodes, y=oversight, name="Oversight (5%)", marker_color="#ef4444"))
    fig.add_trace(go.Bar(x=episodes, y=depth, name="Depth Bonus", marker_color="#10b981"))

    fig.update_layout(
        title="Reward Dimension Breakdown (Last 5 Episodes)",
        barmode='stack',
        xaxis_title="Episode",
        yaxis_title="Reward Component",
        template="plotly_dark",
        height=400,
        showlegend=True
    )

    return fig

# ============================================================================
# GRADIO INTERFACE
# ============================================================================

def create_ui():
    """Build the complete Gradio interface."""

    with gr.Blocks(title="NEXUS Enhanced", theme=gr.themes.Soft(primary_hue="blue")) as demo:

        # =====================================================================
        # HEADER
        # =====================================================================
        gr.Markdown("""
        # 🚨 NEXUS Enhanced
        ### Multi-Agent Enterprise Incident Response RL Environment

        Train AI agents to coordinate incident response across 6 specialized roles.
        """)

        # =====================================================================
        # MAIN LAYOUT: Left sidebar + Right content
        # =====================================================================
        with gr.Row():

            # LEFT: CONTROLS
            with gr.Column(scale=1, min_width=300):
                gr.Markdown("### ⚡ Incident Selection")

                # Incident selector
                incidents = fetch_incidents()
                incident_choices = [f"{inc['case_id']}: {inc['title']}"
                                  for inc in incidents]

                if not incident_choices:
                    incident_choices = ["INC003: Cascading Microservices Failure"]

                selected_incident = gr.Dropdown(
                    choices=incident_choices,
                    value=incident_choices[0],
                    label="Select Incident",
                    interactive=True
                )

                # Difficulty selector
                difficulty = gr.Radio(
                    choices=["easy", "medium", "hard", "very_hard", "nightmare"],
                    value="medium",
                    label="Difficulty"
                )

                # Start button
                start_btn = gr.Button("🚀 Start Episode", variant="primary", size="lg")

                # Session display
                session_display = gr.Textbox(
                    label="Session ID",
                    interactive=False,
                    value="Waiting for start...",
                    scale=1
                )

                gr.Markdown("---")
                gr.Markdown("### 📊 Training Summary")

                # Metrics summary (grid)
                with gr.Row():
                    episodes_metric = gr.Number(label="Episodes", value=0, interactive=False, precision=0)
                    avg_reward_metric = gr.Number(label="Avg Reward", value=0.0, interactive=False, precision=4)

                with gr.Row():
                    best_reward_metric = gr.Number(label="Best Reward", value=0.0, interactive=False, precision=4)
                    improvement_metric = gr.Number(label="vs Baseline", value=0.0, interactive=False, precision=4)

                refresh_btn = gr.Button("🔄 Refresh Metrics", size="sm")

            # RIGHT: CHARTS & INFO
            with gr.Column(scale=2):
                gr.Markdown("### 📈 Training Progress")

                reward_curve_chart = gr.Plot(label="Reward Curve")
                dimension_chart = gr.Plot(label="Reward Breakdown by Dimension")

        # =====================================================================
        # EPISODE CONTROL
        # =====================================================================
        gr.Markdown("---")
        gr.Markdown("### 🎮 Episode Control")

        with gr.Row():
            with gr.Column():
                gr.Markdown("**Current Status**")
                phase_display = gr.Textbox(label="Phase", value="detection", interactive=False, scale=1)
                step_display = gr.Textbox(label="Step / Max", value="0 / 50", interactive=False, scale=1)

            with gr.Column():
                gr.Markdown("**Incident Context**")
                incident_title = gr.Textbox(label="Incident", value="Select and start", interactive=False, scale=1)
                elapsed_display = gr.Textbox(label="Elapsed (min)", value="0", interactive=False, scale=1)

        # Observations
        obs_display = gr.Textbox(
            label="🔍 Current Observations (from agents)",
            lines=4,
            interactive=False,
            value="Start an episode to see observations"
        )

        # =====================================================================
        # IC ACTIONS (Incident Commander)
        # =====================================================================
        gr.Markdown("---")
        gr.Markdown("### 💼 Your Actions (Incident Commander)")

        with gr.Row():
            assessment = gr.Textbox(
                label="📝 Situation Assessment",
                placeholder="Summarize your understanding of the incident...",
                lines=3,
                scale=1
            )

            hypothesis = gr.Textbox(
                label="🔍 Root Cause Hypothesis",
                placeholder="State your hypothesis for the root cause...",
                lines=3,
                scale=1
            )

        with gr.Row():
            confidence = gr.Slider(
                label="✅ Resolution Confidence",
                minimum=0.0,
                maximum=1.0,
                step=0.05,
                value=0.0,
                scale=2
            )

        # Agent dispatching
        gr.Markdown("### 👥 Dispatch Specialists")
        with gr.Row():
            dispatch_l2 = gr.Checkbox(label="L2 Engineer (logs, metrics)", value=False)
            dispatch_l1 = gr.Checkbox(label="L1 Support (customers, notifications)", value=False)

        with gr.Row():
            dispatch_sre = gr.Checkbox(label="SRE Agent (runbooks, infra)", value=False)
            dispatch_pm = gr.Checkbox(label="Product Manager (SLA, revenue)", value=False)

        # SRE runbook step (conditional visibility)
        sre_step = gr.Dropdown(
            choices=[
                "rb_heap_profile",
                "rb_check_cache_config",
                "rb_set_cache_eviction",
                "rb_controlled_restart",
                "rb_check_pod_restarts",
                "rb_rollback_recommendation",
            ],
            value="rb_heap_profile",
            label="📋 Runbook Step (when SRE selected)",
            visible=False
        )

        def toggle_sre(checked):
            return gr.Dropdown(visible=checked)

        dispatch_sre.change(toggle_sre, inputs=[dispatch_sre], outputs=[sre_step])

        # Action buttons
        with gr.Row():
            execute_btn = gr.Button("▶ Execute Step", variant="primary", size="lg", scale=2)
            end_btn = gr.Button("🏁 End Episode", variant="secondary", size="lg", scale=1)

        # Step result
        step_result = gr.Textbox(
            label="📤 Step Result",
            interactive=False,
            lines=2,
            value="Ready for first action"
        )

        # =====================================================================
        # EVENT HANDLERS
        # =====================================================================

        def on_start_episode(incident_str, diff):
            """Start a new episode."""
            try:
                incident_id = incident_str.split(":")[0]
                result = reset_episode(incident_id, diff if diff else None)

                if "error" in result:
                    return (
                        f"❌ Error: {result['error']}", "", "", "", "", "",
                        "Error", incident_id, "Unknown", 0,
                        0, 0.0, 0.0, 0.0, 0.0
                    )

                obs = result.get("observation", {})

                return (
                    f"✅ Episode started: {incident_id}",
                    obs.get("phase", "Unknown"),
                    f"{obs.get('step', 0)} / {obs.get('max_steps', 50)}",
                    obs.get("incident_title", incident_id),
                    str(obs.get("elapsed_minutes", 0)),
                    str(obs).replace("'", '"')[:300] + "...",
                    obs.get("phase", "detection"),
                    app_state.session_id or "None",
                    0, 0.0, 0.0, 0.0, 0.0
                )
            except Exception as e:
                return (f"Error: {str(e)}", "", "", "", "", "", "error", "None", 0, 0.0, 0.0, 0.0, 0.0)

        def on_execute_step(assess, hypo, conf, l2, l1, sre, pm, sre_step_id):
            """Execute one step."""
            try:
                result = execute_step(assess, hypo, conf, l2, l1, sre, pm, sre_step_id)

                if "error" in result:
                    return f"❌ Error: {result['error']}", "", "", "", "", ""

                obs = result.get("observation", {})
                reward = result.get("reward", 0.0)
                done = result.get("done", False)

                status = f"✅ Step {obs.get('step', 0)} complete. Reward: {reward:.4f}. "
                if done:
                    status += "🎉 Episode resolved!"
                else:
                    status += "Continue investigating..."

                return (
                    status,
                    obs.get("phase", "Unknown"),
                    f"{obs.get('step', 0)} / {obs.get('max_steps', 50)}",
                    obs.get("incident_title", ""),
                    str(obs.get("elapsed_minutes", 0)),
                    str(obs).replace("'", '"')[:300] + "...",
                    status
                )
            except Exception as e:
                return f"Error: {str(e)}", "", "", "", "", "", f"Error: {str(e)}"

        def on_refresh_metrics():
            """Refresh metrics from backend."""
            try:
                metrics = fetch_metrics()

                if "error" in metrics:
                    return (
                        "❌ Error fetching metrics",
                        build_reward_curve({}),
                        build_dimension_breakdown({}),
                        0, 0.0, 0.0, 0.0
                    )

                return (
                    f"✅ Updated {metrics.get('episode_count', 0)} episodes",
                    build_reward_curve(metrics),
                    build_dimension_breakdown(metrics),
                    metrics.get('episode_count', 0),
                    metrics.get('avg_reward', 0.0),
                    metrics.get('best_reward', 0.0),
                    metrics.get('avg_reward', 0.0) - 0.265
                )
            except Exception as e:
                return f"Error: {str(e)}", gr.Plot(go.Figure()), gr.Plot(go.Figure()), 0, 0.0, 0.0, 0.0

        # Wire up button clicks
        start_btn.click(
            on_start_episode,
            inputs=[selected_incident, difficulty],
            outputs=[
                step_result, phase_display, step_display, incident_title, elapsed_display,
                obs_display, phase_display, session_display, step_display,
                episodes_metric, avg_reward_metric, best_reward_metric, improvement_metric
            ]
        )

        execute_btn.click(
            on_execute_step,
            inputs=[assessment, hypothesis, confidence, dispatch_l2, dispatch_l1,
                   dispatch_sre, dispatch_pm, sre_step],
            outputs=[
                step_result, phase_display, step_display, incident_title, elapsed_display,
                obs_display, step_result
            ]
        )

        refresh_btn.click(
            on_refresh_metrics,
            outputs=[
                step_result, reward_curve_chart, dimension_chart,
                episodes_metric, avg_reward_metric, best_reward_metric, improvement_metric
            ]
        )

        # Load initial metrics on startup
        demo.load(
            on_refresh_metrics,
            outputs=[
                step_result, reward_curve_chart, dimension_chart,
                episodes_metric, avg_reward_metric, best_reward_metric, improvement_metric
            ]
        )

    return demo

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(f"Starting NEXUS Enhanced Gradio dashboard...")
    print(f"Backend API: {API_BASE}")
    print(f"Visit: http://localhost:7860")

    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
