#!/bin/bash
cd "$(dirname "$0")"

if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

if [ -z "$GEMINI_API_KEY" ]; then
  echo "GEMINI_API_KEY is not set."
  echo "Add it to .env or export it before running: export GEMINI_API_KEY=..."
  exit 1
fi

export GEMINI_MODEL="${GEMINI_MODEL:-gemini-3-pro-preview}"

echo "Starting MedGuard AI backend on http://localhost:8000"
echo "Gemini model: $GEMINI_MODEL"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
