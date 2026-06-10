# IQ Math AI Agent Backend

FastAPI backend for the live AI Agent Workspace.

## Run locally

```bash
cd backend
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The frontend expects the backend at `http://localhost:8000` unless `VITE_AGENT_API_URL` is set.

API keys are supplied by the browser at run time over the WebSocket request and are not persisted by the backend.

