## Local browser testing guide

Copy this file to `devops/local-browser-guide.md` (which is gitignored) if you want your own notes; the steps below describe the stock workflow for spinning up the FastAPI backend and static frontend locally.

1. **Ensure the quickstart script is executable** – from the repo root (`/Users/aidanhalley/Documents/Reframing-Retirement`) run:
   ```bash
   chmod +x scripts/quickstart.sh
   ```
   You only have to do this once per clone.
2. **Start the backend stack** – launch the API mode:
   ```bash
   ./scripts/quickstart.sh api
   ```
   The script creates/activates `.venv`, installs dependencies, ensures the `rr-qdrant` Docker container is running and healthy, then starts `uvicorn backend.app:app --host 127.0.0.1 --port 8000`. Leave this terminal open.
3. **Verify FastAPI health (optional but recommended)** – in a second terminal:
   ```bash
   curl http://127.0.0.1:8000/healthz
   ```
   You should see `{"status":"ok"}` coming from `backend/app.py`.
4. **Serve the frontend** – from a third terminal:
   ```bash
   cd frontend
   python -m http.server 4173
   ```
   Visit `http://localhost:4173` in your browser. `index.html` already sets `window.API_BASE_URL` to `http://localhost:8000`, so the UI will talk to the backend immediately.

### Quick checklist

- [ ] `.env` has valid OpenAI + (optional) Qdrant overrides.
- [ ] `./scripts/quickstart.sh api` is running and logging `[run] Starting FastAPI server at http://127.0.0.1:8000`.
- [ ] `curl http://127.0.0.1:8000/healthz` returns `{"status":"ok"}`.
- [ ] Static server is running inside `frontend/` (e.g., `python -m http.server 4173`).
- [ ] Browser is open to `http://localhost:4173` and can send/receive chat messages.
