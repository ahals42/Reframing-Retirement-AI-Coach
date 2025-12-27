# Reframing Retirement Coach

Conversational CLI agent that embodies a non-clinical, autonomy-supportive physical-activity coach for newly retired adults. It wraps the OpenAI Chat Completions API with a carefully crafted system prompt and lightweight heuristics to keep track of inferred user context (stage, barriers, preferred activities, time available).

## Setup

1. **Python**
   - Requires Python 3.10+.
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment variables**
   - Copy `.env.example` to `.env` (or create `.env`) with:
     ```
     OPEN_API_KEY=sk-...
     OPENAI_MODEL=gpt-4o          # optional override; defaults to gpt-4o if omitted
     ```
   - The application uses `python-dotenv` to load this file automatically.

## Usage (CLI)

Run the CLI:

```bash
python main.py
```

Type messages to converse with the coach. `exit`/`quit` (or Ctrl+C/D) cleanly stop the session.

## Project Layout

- `main.py` – CLI entry point, conversation loop, OpenAI integration, and heuristic state inference.
- `prompts/` – houses the base prompt and helper to inject inferred variables.
- `requirements.txt` – Python dependencies.
- `backend/` – FastAPI app + session store for streaming HTTP access.
- `frontend/` – Static vanilla-JS chat experience that talks to the API.
- `.env` – local secrets (never commit real keys).

## Backend API + Web UI

1. Ensure Docker Desktop is running (Qdrant dependency).
2. Start the API server (this also handles virtualenv + dependencies):
   ```bash
   ./scripts/quickstart.sh api
   ```
   Override host/port with `API_HOST`/`API_PORT` if needed.
3. Serve the static frontend (any static host works). During local dev you can run:
   ```bash
   cd frontend
   python -m http.server 4173
   ```
   Then visit `http://localhost:4173` in your browser. The page expects the API at `http://localhost:8000` by default; set `window.API_BASE_URL` in `index.html` if you deploy elsewhere.

The API exposes three endpoints:

- `POST /sessions` → create anonymous session
- `POST /sessions/{id}/messages` → stream assistant reply as newline-delimited JSON events
- `DELETE /sessions/{id}` → clear a session (used by the “Start fresh” button)

`GET /healthz` returns a simple readiness signal you can wire into uptime checks.

## Notes

- The agent intentionally avoids clinical/diagnostic guidance and keeps conversations autonomy-supportive.
- `main.py` currently uses the Chat Completions endpoint via `openai>=1.0.0`. Update `OPENAI_MODEL` if you prefer another compatible model (e.g., `gpt-4o-mini`).
