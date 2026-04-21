"""
NEXUS Enhanced — Streamlit Validation UI (Calls FastAPI Backend)
3 modes: Auto Demo | Guided Test | Raw API

This is an INTERNAL validation tool that calls the FastAPI backend.
Judges see the FastAPI dashboard (/). This Streamlit app is for developer testing.
"""

import streamlit as st
import requests
import json
import time

# FastAPI backend URL
BACKEND_URL = "http://localhost:7860"

st.set_page_config(page_title="NEXUS Enhanced — Validation", layout="wide")

# ============================================================================
# SESSION STATE
# ============================================================================
if "mode" not in st.session_state:
    st.session_state.mode = "auto_demo"
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "observation" not in st.session_state:
    st.session_state.observation = None
if "step_history" not in st.session_state:
    st.session_state.step_history = []
if "demo_running" not in st.session_state:
    st.session_state.demo_running = False

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def call_reset(incident_id="INC003"):
    """Call POST /reset on FastAPI backend"""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/reset",
            json={"incident_id": incident_id, "difficulty": None, "seed": None}
        )
        return resp.json()
    except Exception as e:
        st.error(f"Error calling /reset: {e}")
        return None

def call_step(session_id, action_dict):
    """Call POST /step on FastAPI backend"""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/step/{session_id}",
            json=action_dict
        )
        return resp.json()
    except Exception as e:
        st.error(f"Error calling /step: {e}")
        return None

def call_learning_curve():
    """Get learning curve data"""
    try:
        resp = requests.get(f"{BACKEND_URL}/learning-curve")
        return resp.json()
    except Exception as e:
        st.error(f"Error fetching learning curve: {e}")
        return {"episodes": []}

# ============================================================================
# HEADER
# ============================================================================
st.markdown("# 🚨 NEXUS Enhanced — Validation UI")
st.markdown("### Internal Testing Tool (Calls FastAPI Backend)")
st.markdown("**This is for developer validation. Judges see the dashboard at `/`**")

st.divider()

# ============================================================================
# SIDEBAR: MODE SELECTOR
# ============================================================================
with st.sidebar:
    st.markdown("## ⚡ Control Panel")

    mode = st.radio(
        "Select Mode",
        ["🎬 Auto Demo", "🧪 Guided Test", "🔧 Raw API"],
        key="mode_selector"
    )

    if mode == "🎬 Auto Demo":
        st.session_state.mode = "auto_demo"
    elif mode == "🧪 Guided Test":
        st.session_state.mode = "guided_test"
    else:
        st.session_state.mode = "raw_api"

    st.markdown("---")

    if not st.session_state.session_id:
        if st.button("▶️ Start Episode", use_container_width=True, key="start_btn"):
            result = call_reset("INC003")
            if result:
                st.session_state.session_id = result.get("session_id")
                st.session_state.observation = result.get("observation")
                st.success("✅ Episode started")
                st.rerun()
    else:
        st.info(f"🔄 Active session: `{st.session_state.session_id[:8]}...`")
        if st.button("⏹️ End Episode", use_container_width=True, key="end_btn"):
            st.session_state.session_id = None
            st.session_state.observation = None
            st.session_state.step_history = []
            st.success("Episode ended")
            st.rerun()

    st.markdown("---")

    if st.session_state.observation:
        st.markdown("### 📊 Current State")
        obs = st.session_state.observation
        st.metric("Phase", obs.get("phase", "N/A").upper())
        st.metric("Step", f"{obs.get('step', 0)}")
        st.metric("Notifications", obs.get("notifications_sent", 0))

# ============================================================================
# MAIN CONTENT
# ============================================================================

if not st.session_state.session_id:
    st.info("👈 Click **Start Episode** to begin validation")
else:
    obs = st.session_state.observation

    # ========================================================================
    # MODE 1: AUTO DEMO
    # ========================================================================
    if st.session_state.mode == "auto_demo":
        st.markdown("## 🎬 Auto Demo: INC003 (Memory Leak)")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Narration")
            st.info("""
            **Step 1:** IC queries Datadog + notifies customers + states hypothesis

            **Step 2:** L2 executes heap profiler + coalition votes on root cause

            **Step 3:** Check cache configuration

            **Step 4:** Apply LRU eviction fix

            **Step 5:** Rolling restart with new cache config

            **Step 6:** Final resolution (confidence > 0.80)
            """)

        with col2:
            st.markdown("### Phase Tracker")
            obs = st.session_state.observation
            phases = ["detection", "triage", "investigation", "mitigation", "resolution", "postmortem"]
            current_phase = obs.get("phase", "detection")
            current_idx = phases.index(current_phase) if current_phase in phases else 0

            phase_cols = st.columns(6)
            for i, (col, phase) in enumerate(zip(phase_cols, phases)):
                with col:
                    if i < current_idx:
                        color = "green"
                        icon = "✓"
                    elif i == current_idx:
                        color = "orange"
                        icon = "●"
                    else:
                        color = "gray"
                        icon = ""

                    st.markdown(
                        f'<div style="background:{color};padding:10px;border-radius:8px;text-align:center;'
                        f'color:white;font-weight:bold;">{icon} {phase.capitalize()}</div>',
                        unsafe_allow_html=True
                    )

        st.markdown("---")

        if st.button("▶️ Run Full Auto-Demo", use_container_width=True):
            st.session_state.demo_running = True

        if st.session_state.demo_running:
            progress_bar = st.progress(0)
            status_text = st.empty()

            actions = [
                {
                    "situation_assessment": "P1 memory issue detected. Datadog shows 96% utilization on recommendation-service.",
                    "hypothesis": "Memory leak in ML model v4 cache",
                    "l1_action": {"action": "send_notification", "parameters": {"tool": "portal"}, "reasoning": ""},
                    "l2_action": {"action": "query_logs", "parameters": {"tool": "datadog", "service": "recommendation-service"}, "reasoning": ""},
                    "sre_action": {"action": "list_runbooks", "parameters": {"tool": "runbook"}, "reasoning": ""},
                    "pm_action": {"action": "get_sla_status", "parameters": {"tool": "portal"}, "reasoning": ""},
                    "severity_assessment": "p2",
                    "resolution_confidence": 0.0,
                    "escalation_required": True,
                },
                {
                    "situation_assessment": "L2 confirms OOM restarts every 90s. Cache has no eviction policy.",
                    "hypothesis": "Cache eviction policy missing from ML model v4",
                    "coalition_vote": "Memory leak in ML model cache",
                    "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
                    "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
                    "sre_action": {"action": "execute_step", "parameters": {"step_id": "rb_heap_profile"}, "reasoning": ""},
                    "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
                    "severity_assessment": "p2",
                    "resolution_confidence": 0.4,
                    "escalation_required": True,
                },
                {
                    "situation_assessment": "Runbook confirmed cache config: max_size=unlimited, eviction=none",
                    "hypothesis": "Cache needs LRU eviction with bounded size",
                    "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
                    "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
                    "sre_action": {"action": "execute_step", "parameters": {"step_id": "rb_check_cache_config"}, "reasoning": ""},
                    "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
                    "severity_assessment": "p2",
                    "resolution_confidence": 0.55,
                    "escalation_required": True,
                },
                {
                    "situation_assessment": "Applying LRU eviction fix with max_size=4096. Memory stabilizing.",
                    "hypothesis": "LRU eviction resolves unbounded growth",
                    "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
                    "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
                    "sre_action": {"action": "execute_step", "parameters": {"step_id": "rb_set_cache_eviction"}, "reasoning": ""},
                    "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
                    "severity_assessment": "p2",
                    "resolution_confidence": 0.75,
                    "escalation_required": True,
                },
                {
                    "situation_assessment": "Rolling restart complete. Memory stable. Service recovered.",
                    "hypothesis": "Cache fix resolves incident",
                    "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
                    "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
                    "sre_action": {"action": "execute_step", "parameters": {"step_id": "rb_controlled_restart"}, "reasoning": ""},
                    "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
                    "severity_assessment": "p2",
                    "resolution_confidence": 0.90,
                    "escalation_required": False,
                },
            ]

            for step_idx, action in enumerate(actions):
                status_text.info(f"Executing step {step_idx + 1}/{len(actions)}...")
                time.sleep(2)

                result = call_step(st.session_state.session_id, action)
                if result:
                    st.session_state.observation = result.get("observation")
                    st.session_state.step_history.append({
                        "step": step_idx + 1,
                        "action": action,
                        "reward": result.get("reward", 0),
                        "done": result.get("done", False)
                    })

                progress_bar.progress((step_idx + 1) / len(actions))

            status_text.success("✅ Auto-demo complete!")
            st.session_state.demo_running = False
            st.rerun()

    # ========================================================================
    # MODE 2: GUIDED TEST
    # ========================================================================
    elif st.session_state.mode == "guided_test":
        st.markdown("## 🧪 Guided Test Mode")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Edit Action")

            situation = st.text_area("Situation Assessment", height=100)
            hypothesis = st.text_input("Hypothesis")
            coalition_vote = st.text_input("Coalition Vote (optional)")
            resolution_confidence = st.slider("Resolution Confidence", 0.0, 1.0, 0.0)

            if st.button("Execute This Step", use_container_width=True):
                action = {
                    "situation_assessment": situation,
                    "hypothesis": hypothesis,
                    "coalition_vote": coalition_vote if coalition_vote else None,
                    "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
                    "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
                    "sre_action": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
                    "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
                    "severity_assessment": "p2",
                    "resolution_confidence": resolution_confidence,
                    "escalation_required": False,
                }

                result = call_step(st.session_state.session_id, action)
                if result:
                    st.session_state.observation = result.get("observation")
                    st.session_state.step_history.append({
                        "step": len(st.session_state.step_history) + 1,
                        "action": action,
                        "reward": result.get("reward", 0),
                        "done": result.get("done", False)
                    })
                    st.success("✅ Step executed")
                    st.rerun()

        with col2:
            st.markdown("### Current Observation")
            obs = st.session_state.observation
            st.json({
                "incident": obs.get("incident_id"),
                "phase": obs.get("phase"),
                "step": obs.get("step"),
                "reward": 0.0 if not st.session_state.step_history else st.session_state.step_history[-1].get("reward", 0),
                "done": st.session_state.step_history[-1].get("done", False) if st.session_state.step_history else False,
            })

    # ========================================================================
    # MODE 3: RAW API
    # ========================================================================
    else:  # raw_api
        st.markdown("## 🔧 Raw API Mode")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Request JSON")
            json_input = st.text_area(
                "StepRequest (JSON)",
                value=json.dumps({
                    "situation_assessment": "Investigating incident",
                    "hypothesis": "root cause hypothesis",
                    "coalition_vote": None,
                    "l1_action": {"action": "send_notification", "parameters": {}, "reasoning": ""},
                    "l2_action": {"action": "query_logs", "parameters": {}, "reasoning": ""},
                    "sre_action": {"action": "list_runbooks", "parameters": {}, "reasoning": ""},
                    "pm_action": {"action": "get_sla_status", "parameters": {}, "reasoning": ""},
                    "severity_assessment": "p2",
                    "resolution_confidence": 0.0,
                    "escalation_required": False,
                }, indent=2),
                height=300
            )

            if st.button("Send Request", use_container_width=True):
                try:
                    action = json.loads(json_input)
                    result = call_step(st.session_state.session_id, action)
                    st.session_state.observation = result.get("observation")
                    st.success("✅ Request sent")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")

        with col2:
            st.markdown("### Response")
            if st.session_state.observation:
                st.json(st.session_state.observation)

    # ========================================================================
    # STEP HISTORY
    # ========================================================================
    st.markdown("---")
    st.markdown("## 📋 Step History")

    if st.session_state.step_history:
        for record in st.session_state.step_history:
            with st.expander(f"Step {record['step']}: Reward={record['reward']:.4f}"):
                st.json(record["action"])
    else:
        st.info("No steps executed yet")

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666;'>NEXUS Enhanced | This is a validation tool for developers</p>",
    unsafe_allow_html=True
)
