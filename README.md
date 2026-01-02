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
