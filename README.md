# Reframing Retirement Coach

A calm, autonomy-supportive physical-activity coach for newly retired adults. It runs on OpenAI’s Chat Completions API with lightweight behavior heuristics, never gives medical advice or emergency help, and is deployed as a FastAPI service running in a container on cloud compute (with an optional local CLI for development).

## Components

- `prompts/` – base system prompt that defines tone, scope, and safety boundaries for the coach.  
- `coach/agent.py` – conversational brain: tracks inferred barriers/preferences/time, routes to retrieval, and streams OpenAI responses.  
- `rag/` – configuration + tools for building and querying a Qdrant vector store of activities/resources.  
- `backend/app.py` – FastAPI server with session storage and SSE endpoints (`/sessions`, `/sessions/{id}/messages`, `/healthz`).  
- `frontend/` – lightweight vanilla-JS chat UI that talks to the API (set `window.API_BASE_URL` to your container IP).  
- `main.py` – local CLI entry point that shares the same agent logic for offline testing.  
- `scripts/quickstart.sh` – bootstraps the virtualenv, installs deps, ensures Qdrant is running via Docker, and starts `uvicorn` (`API_HOST=0.0.0.0` for cloud).  
- `Data/` – curated text/activity references used to seed the RAG store.make th

## Run the coach in your browser

1. **Ensure the quickstart script is executable** – from the repo root (`/Users/aidanhalley/Documents/Reframing-Retirement`) run `chmod +x scripts/quickstart.sh` (only needed once per clone).
2. **Start the backend stack** – `./scripts/quickstart.sh api`. This creates/activates `.venv`, installs dependencies, boots/health-checks the `rr-qdrant` Docker container, and finally launches `uvicorn backend.app:app --host 127.0.0.1 --port 8000`. Leave this terminal open.
3. **Verify FastAPI health (optional but recommended)** – from a new terminal run `curl http://127.0.0.1:8000/healthz` and look for `{"status":"ok"}`.
4. **Serve the frontend** – `cd frontend && python -m http.server 4173` (or any static server). Visit `http://localhost:4173` in your browser. The page already targets `http://localhost:8000`, so chat messages will flow through the FastAPI backend you started above.

### Quick checklist

- [ ] `.env` present with valid OpenAI + Qdrant settings.
- [ ] `./scripts/quickstart.sh api` running and logging `[run] Starting FastAPI server at http://127.0.0.1:8000`.
- [ ] `curl http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`.
- [ ] Static server running inside `frontend/` (e.g., `python -m http.server 4173`).
- [ ] Browser pointed to `http://localhost:4173` and able to send/receive chat messages.
