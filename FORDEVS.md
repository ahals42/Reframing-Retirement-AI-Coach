# For developers: Full coach (lessons 1-10)

This document is for developers adding the Reframing Retirement coach to an app. It covers what this repo provides, how to run it, and how to call it.

## What this is

A chat backend (FastAPI) and reference web page for a physical activity coach limited to **all 10 lessons and The Science Behind Lessons 1-3, 4-6 and 7-10**. It replies in M-PAC aligned coaching style, grounded in the lesson material it has been given, and declines anything outside its scope.

## What to take from this repo

| Path | Purpose |
|---|---|
| `backend/app.py` | HTTP API: sessions, messages, health |
| `backend/voice/` | Voice chat route (same coach behind it) |
| `coach/` | Prompt, scope rules, reply logic, weekly focus tables |
| `rag/` | Retrieval over the lesson content in Qdrant |
| `data/` | Lesson content for this version: `New-RR-Master-File.txt` (all lessons and science modules), plus the activity and at-home resource lists |
| `frontend/` | Optional reference chat page |

## Running it locally

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. First time only: `scripts/run_local.sh --ingest` (builds this version's Qdrant collections).
3. Then: `scripts/run_local.sh`.
4. Open http://localhost:8000.

The script creates its own `.venv` and starts Qdrant in Docker if needed. Qdrant dashboard: http://localhost:6333/dashboard.

Collections for this version: `rr_master`, `rr_activities`, `rr_home`. They are separate from every other version, so ingesting here never changes another version's data.

## API

Base URL: `https://<lightsail-host>` (auto-deployed to an AWS Lightsail instance from `main`; host to be confirmed). Local: `http://localhost:8000`.

**Create a session**
```
POST /sessions
→ {"session_id": "..."}
```

**Send a message**
```
POST /sessions/{session_id}/messages
Content-Type: application/json

{"text": "What is physical activity?"}
```

The response is newline-delimited JSON, not Server-Sent Events. Each line is one event:

- `{"type": "token", "text": "..."}`: a partial piece of the reply, streamed as it is generated.
- `{"type": "done", "text": "...", "state": {...}, "retrieved_context": ...}`: the full reply, sent once at the end. Use `text` here if you don't want to join the token pieces.
- `{"type": "error", "error": "..."}`: the reply failed or timed out.

**Delete a session**
```
DELETE /sessions/{session_id}
```

**Health check**
```
GET /healthz
```

**Voice:** `POST /sessions/{session_id}/voice-chat` takes an audio upload and returns the spoken reply. See `backend/voice/routes.py` for the request format.

## Authentication

Send your API key in the `X-API-Key` header on every request, for example `X-API-Key: <key>`. Keys are issued by the team.

## Limits and behaviour to design around

- Messages are capped at 10,000 characters.
- A session expires after 90 minutes without use.
- Each session keeps up to 100 messages of history.
- Sessions are held in memory in the server process. A restart clears them, and running several server processes needs sticky routing or a shared store (not built here).
- Rate limits: 5,000 messages per hour and 1,000 session creations per hour.
- A streamed reply times out after 300 seconds.
- Conversations are not stored. The app does not keep transcripts.

## How scope works

- **In scope:** the coach answers and cites the matching lesson or science module.
- **Later content:** a question about a lesson or science module outside this version gets a specific decline that names the lesson and offers what it can cover. It does not explain the later content.
- **Out-of-range lesson or week requests:** get the same specific decline.
- **"Science behind lesson N":** cites the science module for that lesson's block. This version only has the modules within its scope.
- **Medical, mental health and emergency topics:** follow the safety rules in `coach/prompts.py`. These are identical across all versions and should stay that way.

## Where scope is set

Edit these when changing scope:

- `coach/prompts.py`: the topic-to-lesson map, the LATER CONTENT block and decline rules.
- `coach/weekly_focus.py`: lesson goals, week tables and the out-of-range message.
- `coach/agent.py`: lesson overview and science-for-lesson handling.
- `data/`: the lesson file used for this version (`rag/config.py` sets it by default).

## Known limits

- The decline wording comes from the model, so phrasing can vary slightly. Test a set of in-scope and out-of-scope questions before release.
- Follow-up questions such as "what is the science behind this lesson" use the last lesson the user named.
- Not production-ready as shipped: no transcript logging, in-memory sessions, and the local copies have no authentication.
