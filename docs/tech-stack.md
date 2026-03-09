# Tech Stack — Reframing Retirement

## Infrastructure
- **Host:** AWS Lightsail (single instance)
- **Container runtime:** Docker + Docker Compose
- **Services in Docker:** FastAPI backend, Qdrant vector database

## Backend
- **Language:** Python 3.11
- **Web framework:** FastAPI — handles all HTTP routes, streaming, auth middleware
- **Server:** Uvicorn — runs FastAPI inside Docker
- **Session management:** Custom in-memory store with TTL expiry and per-key limits
- **Rate limiting:** slowapi — per-API-key, per-endpoint request caps
- **Authentication:** Custom API key middleware (X-API-Key header)

## AI / LLM
- **Provider:** OpenAI
- **Chat model:** GPT-4o-mini — generates all coaching responses
- **Embedding model:** text-embedding-3-large — converts text into vectors for search
- **Speech-to-text:** Whisper (via OpenAI API) — transcribes voice input
- **Text-to-speech:** OpenAI TTS — synthesizes coach voice replies

## RAG (Retrieval-Augmented Generation)
- **Vector database:** Qdrant — stores and searches embedded knowledge chunks
- **RAG framework:** LlamaIndex — manages ingestion, chunking, and retrieval
- **Collections:** 3 separate indexes (master course content, local activities, at-home resources)
- **Router:** Custom keyword/regex router that decides which index(es) to query
- **Cache:** In-memory LRU cache (256 entries) on the retriever to skip repeat Qdrant queries
- **Retrieval:** Parallel Qdrant queries via ThreadPoolExecutor for multi-collection lookups

## Coach Logic
- **Agent:** Custom CoachAgent class — orchestrates retrieval, prompt building, and streaming
- **Layer detection:** Heuristic system that infers where a user is in their behaviour change journey
- **State:** Per-session conversation history, message count, last activity timestamp
- **Prompts:** Dynamically assembled from user state, retrieved context, and lesson overviews

## Frontend
- **Type:** Static HTML/CSS/JS — no framework
- **Served by:** FastAPI's StaticFiles mount (same container as the API)
- **Voice UI:** Browser MediaRecorder API captures audio, sends to backend voice-chat endpoint
- **Streaming:** Server-Sent Events (SSE) — tokens stream from backend to browser in real time

## Data
- **Source files:** 3 plain text files in `/data/` (master, activities, at-home)
- **Ingestion:** `rag/ingest.py` script — chunks, embeds, and loads into Qdrant
- **Config:** All tuneable settings in `config/app_config.py`, secrets in `.env`

## Key Config / Settings
- `config/app_config.py` — single source of truth for all limits and thresholds
- `.env` — OpenAI API key, Qdrant URL/key, model names, rate limit overrides
- `requirements.txt` — all Python packages pinned to exact versions
