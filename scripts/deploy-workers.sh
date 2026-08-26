#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== 1. Syntax check ==="
cd "$REPO_ROOT/pipeline"
python3 -m py_compile worker_ticket.py worker_ingest.py worker_ml.py worker_agent.py main.py
echo "All files compile OK."

echo ""
echo "=== 2. Railway service variables ==="
cd "$REPO_ROOT"

# backend-worker → ticket workflow
railway variables --service backend-worker --set RAILWAY_DOCKERFILE_PATH=pipeline/Dockerfile.workers --set WORKER_MODULE=worker_ticket
echo "✓ backend-worker configured"

# ingest-worker → live stream ingest
railway variables --service ingest-worker --set RAILWAY_DOCKERFILE_PATH=pipeline/Dockerfile.workers --set WORKER_MODULE=worker_ingest
echo "✓ ingest-worker configured"

# ml-worker → risk scoring
railway variables --service ml-worker --set RAILWAY_DOCKERFILE_PATH=pipeline/Dockerfile.workers --set WORKER_MODULE=worker_ml
echo "✓ ml-worker configured"

# agent-worker → orchestrator
railway variables --service agent-worker --set RAILWAY_DOCKERFILE_PATH=pipeline/Dockerfile.workers --set WORKER_MODULE=worker_agent
echo "✓ agent-worker configured"

# Clean up stale var on backend
railway variables --service backend --unset NIXPACKS_CONFIG_FILE 2>/dev/null || true
echo "✓ backend NIXPACKS_CONFIG_FILE removed"

echo ""
echo "=== 3. Git commit & push ==="
cd "$REPO_ROOT"
git add pipeline/worker_ticket.py pipeline/worker_ingest.py pipeline/worker_ml.py pipeline/worker_agent.py pipeline/Dockerfile.workers pipeline/main.py .github/workflows/railway.yml
git status --short
git commit -m "Split 4 worker services with distinct roles + fix double-scheduling

- worker_ticket.py: ticket workflow advancement (backend-worker)
- worker_ingest.py: live stream batch ingestion (ingest-worker)
- worker_ml.py: LLM risk scoring of unscored feedback (ml-worker)
- worker_agent.py: multi-agent orchestrator pipeline (agent-worker)
- Dockerfile.workers: shared image with WORKER_MODULE build arg
- main.py: remove APScheduler auto-jobs from lifespan (fix double-scheduling)
- railway.yml: deploy all 6 services (frontend + backend + 4 workers)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"

git push origin main

echo ""
echo "=== DONE ==="
echo "Push complete. CI will now deploy all services."
echo "Verify with: railway logs --service backend-worker"
