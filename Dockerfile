FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps (CPU-only for HF Space; GPU training runs in Colab)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make startup script executable
RUN chmod +x start.sh

# Smoke test on build
RUN python -c "from server.environment import NexusEnvironment; env = NexusEnvironment(); obs = env.reset(incident_id='INC003'); print('✅ Build smoke test passed:', obs['incident_id'])"

# Expose both FastAPI (7860, public) and Streamlit (8501, internal validation)
EXPOSE 7860 8501

# Health check on FastAPI endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["bash", "start.sh"]
