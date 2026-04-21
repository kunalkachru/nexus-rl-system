"""NEXUS Enhanced - Auto Demo UI for Hackathon Judges"""
import streamlit as st
import time
from server.environment import NexusEnvironment
from server.incidents import INCIDENT_LIBRARY
from server.reward import compute_total_reward
from server.data_models import RewardBreakdown

st.set_page_config(page_title="NEXUS Enhanced", layout="wide")

# ============================================================================
# PHASE & COLOR CONSTANTS
# ============================================================================
PHASES = ["detection", "triage", "investigation", "mitigation", "resolution", "postmortem"]
PHASE_COLORS = {
    "done": "#2ecc71",      # green
    "active": "#e67e22",    # orange
    "pending": "#95a5a6",   # grey
}

# ============================================================================
# TEST CASE LIBRARY - INC003 OPTIMAL 6-STEP PATH
# ============================================================================
TEST_CASE_LIBRARY = {
    "INC003_OPTIMAL": {
        "incident_id": "INC003",
        "label": "INC003 — Memory Leak (Optimal 6-Step)",
        "steps": [
            {
                "label": "Step 1: Query Datadog + Notify Customers + State Hypothesis",
                "narration": "🔍 Incident Commander queries Datadog to confirm memory issue in recommendation-service. Simultaneously notifies 320k affected customers. States initial hypothesis about cache eviction.",
                "why_it_scores": "Earns diagnosis evidence (tool query on root cause service), customer notification score (+0.5), and depth bonus from rich assessment.",
                "action": {
                    "situation_assessment": "recommendation-service memory utilization at 96% with GC pauses of 4.2 seconds. ML model v4 deployed April 20 with feature vector caching. Red herrings: search-service errors and ad-service CPU both marked as expected under load.",
                    "hypothesis": "Memory leak in ML model v4 feature vector cache. Cache has no eviction policy, causing unbounded heap growth until OOMKill.",
                    "resolution_confidence": 0.05,
                    "direct_tool": {"tool": "datadog", "action": "query", "parameters": {"service": "recommendation-service", "metric": "memory_utilization"}},
                    "l1_directive": {"action": "send_notification", "parameters": {"customers": "all_affected", "message": "Product recommendations unavailable. Engineering team investigating. ETA 15 min.", "severity": "high"}, "reasoning": "320k users affected. Proactive notification required."}
                }
            },
            {
                "label": "Step 2: Execute Runbook + Coalition Vote",
                "narration": "📊 SRE Agent executes first runbook step (heap profiler). L2 Engineer checks deploy history. Coalition votes on root cause with keyword alignment.",
                "why_it_scores": "Runbook execution advances mitigation phase. Coalition vote boosts coordination score. Rich narrative feeds depth bonus.",
                "action": {
                    "situation_assessment": "Heap profiler analysis confirms ML model v4 feature vector cache is the top memory consumer at 14.2GB. Cache objects show no eviction logic. Runbook rb_heap_profile results indicate clear memory growth pattern correlated with ML model v4 deployment on April 20. All 320k users affected in us-east-1 and eu-west-1 regions. Root cause hypothesis: cache missing LRU or similar eviction mechanism.",
                    "hypothesis": "ML model v4 FeatureVectorCache has no eviction policy. Unbounded growth in heap until OOMKill triggers pod restart cycle.",
                    "coalition_vote": "ML model v4 feature vector cache lacks LRU eviction — memory grows unbounded until OOMKill. Heap profiler shows cache objects at top. Root cause confirmed.",
                    "resolution_confidence": 0.35,
                    "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_heap_profile", "confirm": True}, "reasoning": "Capture heap profile to identify top memory consumer"}
                }
            },
            {
                "label": "Step 3: Check Cache Configuration",
                "narration": "🔧 SRE continues runbook. Inspects cache configuration. Confirms max_size=unlimited and eviction=none.",
                "why_it_scores": "Correct runbook execution (prerequisite chain). Evidence building toward resolution phase.",
                "action": {
                    "situation_assessment": "Runbook rb_check_cache_config reveals FeatureVectorCache max_size=unlimited with eviction_policy=none. This is the smoking gun. ML model v4 changelog shows cache size increased 10x for accuracy. No corresponding cache limits added.",
                    "hypothesis": "Cache eviction policy missing from ML model v4. max_size=unlimited allows unbounded growth.",
                    "resolution_confidence": 0.4,
                    "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_check_cache_config", "confirm": True}, "reasoning": "Verify cache configuration matches our hypothesis"}
                }
            },
            {
                "label": "Step 4: Set Cache LRU Eviction",
                "narration": "⚙️ SRE applies the fix: configures LRU eviction on cache with max_size=4096. Heap begins to stabilize.",
                "why_it_scores": "Correct mitigation step execution. Memory now stable.",
                "action": {
                    "situation_assessment": "Runbook rb_set_cache_eviction applied. FeatureVectorCache now configured with max_size=4096 and eviction=LRU. Heap memory usage drops from 14.2GB to stabilized <8GB. GC pauses reduce to normal levels. API latency improves. Evidence shows root cause addressed.",
                    "hypothesis": "LRU eviction successfully applied to cache. Unbounded growth stopped. Heap stable below 8GB.",
                    "resolution_confidence": 0.6,
                    "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_set_cache_eviction", "confirm": True}, "reasoning": "Apply LRU eviction with max_size=4096 to cache"}
                }
            },
            {
                "label": "Step 5: Controlled Rolling Restart",
                "narration": "🚀 SRE performs controlled rolling restart of recommendation-service with new cache configuration. Service recovers without downtime.",
                "why_it_scores": "Final runbook step (mitigation complete). Confidence > 0.80 triggers postmortem phase.",
                "action": {
                    "situation_assessment": "Runbook rb_controlled_restart: rolling restart of recommendation-service pods one by one with new cache config. Service available throughout restart. Memory stays stable. All 4 correct runbook steps completed. Episode moving to resolution phase.",
                    "hypothesis": "Root cause ML model v4 cache eviction fixed via LRU with max_size=4096. Service recovered and stable.",
                    "resolution_confidence": 0.85,
                    "sre_directive": {"action": "execute_runbook_step", "parameters": {"step_id": "rb_controlled_restart", "confirm": True}, "reasoning": "Rolling restart with new cache configuration — zero downtime recovery"}
                }
            },
            {
                "label": "Step 6: Resolve & Complete",
                "narration": "✅ Incident Commander confirms resolution. Episode complete. Final reward calculated.",
                "why_it_scores": "done=True triggers final reward computation. All dimensions score high: fast MTTR (12 min vs optimal 28 min), diagnosis evidence + hypothesis match, customer notification, runbook completion, zero violations.",
                "action": {
                    "situation_assessment": "All mitigation steps completed. Memory stable. GC pauses normal. API latency recovered. 320k users back online. Postmortem documented. Root cause: ML model v4 feature vector cache eviction policy missing. Fix: LRU cache with max_size=4096. Deployment validated. Coalition agreement reached on root cause and solution.",
                    "hypothesis": "Root cause confirmed and fixed: ML model v4 cache lacked eviction. LRU with bounded size resolves issue.",
                    "resolution_confidence": 0.9
                }
            }
        ]
    }
}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "env" not in st.session_state:
    st.session_state.env = NexusEnvironment()
    st.session_state.observation = None
    st.session_state.step_history = []
    st.session_state.demo_running = False
    st.session_state.demo_step_index = 0
    st.session_state.live_reward = None
    st.session_state.prev_live_reward = None
    st.session_state.final_breakdown = None
    st.session_state.episode_done = False

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_live_reward(env):
    """Get reward preview using compute_total_reward directly."""
    if env.current_state is None:
        return None
    try:
        breakdown = compute_total_reward(env.current_state)
        return {
            "mttr": breakdown.mttr,
            "diagnosis": breakdown.diagnosis,
            "customer": breakdown.customer,
            "coordination": breakdown.coordination,
            "oversight": breakdown.oversight,
            "depth_bonus": breakdown.depth_bonus,
            "expert_criteria": breakdown.expert_criteria,
            "total": breakdown.total,
        }
    except:
        return None

def render_phase_tracker(current_phase):
    """Render 6 phase pills with HTML styling."""
    cols = st.columns(6)
    current_idx = PHASES.index(current_phase) if current_phase in PHASES else 0

    for i, (col, phase) in enumerate(zip(cols, PHASES)):
        if i < current_idx:
            color = PHASE_COLORS["done"]
            icon = "✓"
        elif i == current_idx:
            color = PHASE_COLORS["active"]
            icon = "●"
        else:
            color = PHASE_COLORS["pending"]
            icon = ""

        with col:
            st.markdown(
                f'<div style="background:{color};padding:8px;border-radius:8px;text-align:center;'
                f'color:white;font-size:13px;font-weight:bold;border:2px solid {color}">'
                f'{icon} {phase.capitalize()}</div>',
                unsafe_allow_html=True
            )

def render_reward_panel(live, prev):
    """Render 7 reward metrics with delta arrows."""
    if not live:
        st.info("No reward data yet. Start episode to begin.")
        return

    cols = st.columns(7)

    metrics = [
        ("MTTR", "mttr"),
        ("Diagnosis", "diagnosis"),
        ("Customer", "customer"),
        ("Coordination", "coordination"),
        ("Oversight", "oversight"),
        ("Depth Bonus", "depth_bonus"),
        ("TOTAL", "total"),
    ]

    for col, (label, key) in zip(cols, metrics):
        with col:
            value = live.get(key, 0.0)
            delta = None
            if prev and key in prev:
                delta = value - prev.get(key, 0.0)

            st.metric(label, f"{value:.2f}", delta=f"{delta:+.2f}" if delta else None)

def render_sidebar_status(obs):
    """Render live status in sidebar."""
    if not obs:
        return

    st.markdown("### 📊 LIVE STATUS")
    st.metric("Phase", obs.get("phase", "N/A").upper())
    st.metric("Step", f"{obs.get('step', 0)} / 28")
    st.metric("Elapsed (min)", f"{obs.get('elapsed_minutes', 0):.1f}")
    st.metric("Notifications", obs.get("notifications_sent", 0))
    st.metric("Violations", obs.get("oversight_violations", 0))

    st.markdown("---")
    st.markdown("### ✅ RUNBOOK CHECKLIST")
    runbooks = [
        ("rb_heap_profile", "Heap Profile"),
        ("rb_check_cache_config", "Cache Config"),
        ("rb_set_cache_eviction", "Set Eviction"),
        ("rb_controlled_restart", "Rolling Restart"),
    ]

    completed = obs.get("runbook_steps_completed", [])
    for step_id, label in runbooks:
        status = "✓" if step_id in completed else "○"
        st.write(f"{status} {label}")

# ============================================================================
# MAIN HEADER
# ============================================================================
st.markdown("# 🚨 NEXUS Enhanced")
st.markdown("### Multi-Agent Enterprise Incident Response RL Environment")
st.markdown("**Auto Demo: CrowdStrike-Scale Memory Leak (INC003)**")

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("## ⚡ DEMO CONTROL")

    if not st.session_state.observation:
        if st.button("▶️ START AUTO DEMO", use_container_width=True, key="start_demo"):
            with st.spinner("Initializing episode..."):
                obs = st.session_state.env.reset(incident_id="INC003")
                st.session_state.observation = obs
                st.session_state.demo_running = True
                st.session_state.demo_step_index = 0
                st.success("✅ Episode started. Launching demo...")
                st.rerun()
    else:
        if st.button("⏹️ END DEMO", use_container_width=True, key="end_demo"):
            st.session_state.observation = None
            st.session_state.demo_running = False
            st.session_state.step_history = []
            st.success("Demo ended.")
            st.rerun()

        if not st.session_state.episode_done:
            st.info(f"Demo running... Step {len(st.session_state.step_history)} of 6")

    st.markdown("---")
    render_sidebar_status(st.session_state.observation)

# ============================================================================
# MAIN CONTENT
# ============================================================================
if not st.session_state.observation:
    st.info("👈 Click **START AUTO DEMO** to launch the 6-step optimal INC003 response")
    with st.expander("📖 What You'll See"):
        st.markdown("""
        **6-Step Incident Response:**
        1. Query metrics + notify customers + state hypothesis
        2. Execute runbook + coalition vote
        3. Check cache configuration
        4. Apply LRU eviction fix
        5. Rolling restart
        6. Resolve + final reward

        **Live Dashboard:**
        - Phase tracker (detection → postmortem)
        - Reward breakdown (7 components with deltas)
        - Runbook checklist (4 steps)
        - Step-by-step narration with explanations

        **What Earns Reward:**
        - Diagnosis: tool query + correct hypothesis keywords
        - Customer: send notification (140k users affected)
        - Coordination: coalition vote alignment
        - Depth bonus: rich situation assessments
        - Oversight: zero violations
        """)

else:
    obs = st.session_state.observation

    # Phase tracker
    st.markdown("### 🔄 Phase Progression")
    render_phase_tracker(obs.get("phase", "detection"))

    st.markdown("---")

    # Current step narration
    if not st.session_state.episode_done:
        step_idx = st.session_state.demo_step_index
        steps = TEST_CASE_LIBRARY["INC003_OPTIMAL"]["steps"]

        if step_idx < len(steps):
            step = steps[step_idx]
            st.markdown(f"### 📍 {step['label']}")
            st.info(step['narration'])
            st.markdown(f"**Why it scores:** {step['why_it_scores']}")

    # Reward panel
    st.markdown("### 💰 Live Reward Breakdown")
    render_reward_panel(st.session_state.live_reward, st.session_state.prev_live_reward)

    st.markdown("---")

    # Episode complete
    if st.session_state.episode_done:
        st.balloons()
        st.success("✅ **EPISODE COMPLETE!**")

        if st.session_state.final_breakdown:
            bd = st.session_state.final_breakdown
            st.markdown("### 🏆 Final Reward Breakdown")
            col1, col2 = st.columns(2)
            with col1:
                st.json({
                    "MTTR": f"{bd.get('mttr', 0):.3f}",
                    "Diagnosis": f"{bd.get('diagnosis', 0):.3f}",
                    "Customer": f"{bd.get('customer', 0):.3f}",
                    "Coordination": f"{bd.get('coordination', 0):.3f}",
                })
            with col2:
                st.json({
                    "Oversight": f"{bd.get('oversight', 0):.3f}",
                    "Depth Bonus": f"{bd.get('depth_bonus', 0):.3f}",
                    "Expert Criteria": bd.get('expert_criteria', 'N/A'),
                    "TOTAL REWARD": f"{bd.get('total', 0):.3f}",
                })

        with st.expander("📋 Step Transcript"):
            for i, rec in enumerate(st.session_state.step_history):
                st.markdown(f"**Step {i+1}:** {rec['label']}")
                st.write(f"Live Reward: {rec['live_reward'].get('total', 0):.3f}")

# ============================================================================
# AUTO DEMO ADVANCEMENT LOOP
# ============================================================================
if st.session_state.demo_running and not st.session_state.episode_done:
    step_idx = st.session_state.demo_step_index
    steps = TEST_CASE_LIBRARY["INC003_OPTIMAL"]["steps"]

    if step_idx < len(steps):
        time.sleep(3)  # Pause for narration readability

        # Execute step
        action = steps[step_idx]["action"]
        obs, reward, done, info = st.session_state.env.step(action)
        st.session_state.observation = obs

        # Capture live reward
        live_reward = get_live_reward(st.session_state.env)
        st.session_state.prev_live_reward = st.session_state.live_reward
        st.session_state.live_reward = live_reward

        # Record step
        st.session_state.step_history.append({
            "label": steps[step_idx]["label"],
            "live_reward": live_reward or {},
            "obs": obs,
            "done": done,
        })

        # Advance index
        st.session_state.demo_step_index += 1

        # Check if done
        if done or step_idx == len(steps) - 1:
            st.session_state.episode_done = True
            st.session_state.demo_running = False
            if live_reward:
                st.session_state.final_breakdown = live_reward

        st.rerun()

st.markdown("---")
st.markdown("*Team Falcons | Meta PyTorch OpenEnv Hackathon Grand Finale | April 25–26, 2026*")
