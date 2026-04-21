#!/bin/bash
# Start FastAPI (public) + Streamlit (internal validation)

# Function to cleanup child processes on exit
cleanup() {
    echo "Shutting down services..."
    kill $PID_FASTAPI $PID_STREAMLIT 2>/dev/null
    exit 0
}
trap cleanup EXIT INT TERM

echo "Starting FastAPI backend on port 7860..."
uvicorn server.app:app --host 0.0.0.0 --port 7860 &
PID_FASTAPI=$!

# Wait for FastAPI to be ready before starting Streamlit
sleep 3

echo "Starting Streamlit validation UI on port 8501..."
streamlit run streamlit_app_v2.py --server.port=8501 --server.address=0.0.0.0 &
PID_STREAMLIT=$!

echo "✅ Services running:"
echo "  • FastAPI (judge dashboard): http://0.0.0.0:7860"
echo "  • Streamlit (validation UI): http://0.0.0.0:8501"

# Keep script running
wait
