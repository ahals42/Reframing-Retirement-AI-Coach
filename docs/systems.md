# System Overview

This document describes each component of the system, what it does, and how it connects to the rest.

---

## Coach Agent (`coach/`)

The central coordinator of the system. It receives the user's message, decides what context is needed, assembles a prompt, and streams the response back.

- Reads the user's message
- Detects behavioural layer (where the user is in their behaviour change journey)
- Decides what content to retrieve from the knowledge base
- Assembles a prompt from session context, retrieved content, and base instructions
- Streams the response back token by token

**Connects to:** RAG pipeline (requests context), API layer (receives messages, sends stream), frontend (stream ends up on screen)

---

## RAG Pipeline (`rag/`)

Handles all retrieval from the knowledge base. When the coach needs relevant content, it calls this system, which searches the vector database and returns the most relevant chunks.

- **Router** (`router.py`) - decides which knowledge collection to query: course content, local activities, or at-home resources
- **Retriever** (`retriever.py`) - queries Qdrant, ranks results, returns the most relevant chunks
- **Qdrant** - the vector database where all knowledge is stored and searched
- **Cache** - skips repeat Qdrant queries for recently seen inputs

**Connects to:** Coach agent (delivers retrieved context on request), Qdrant (queries vectors), ingestion script (receives new data when run)

---

## FastAPI Backend (`backend/`)

The API layer that everything connects through. It defines all HTTP routes, enforces authentication, manages session lifecycle, and streams responses back to clients.

- Defines every HTTP route (sessions, messages, voice, health check)
- Enforces authentication before anything else runs
- Applies rate limits at the entry points
- Manages session lifecycle (create, retrieve, expire, delete)
- Streams responses from the coach agent back to the client

**Connects to:** Frontend (receives requests, sends responses), coach agent (delegates message handling), voice pipeline (routes audio uploads)

---

## Voice Pipeline (`backend/voice/`)

Handles conversion between audio and text in both directions. Voice input from the participant is transcribed to text, passed to the coach, and the reply is converted back to audio before being returned.

- **STT** (`stt.py`) - audio in, Whisper transcription, text out
- **TTS** (`tts.py`) - text in, OpenAI TTS synthesis, audio out
- **Routes** (`routes.py`) - validates the audio file and coordinates the full exchange

**Connects to:** Frontend (receives audio, returns audio), coach agent (passes transcript in, receives reply text out), OpenAI API (both directions)

---

## Middleware (`backend/middleware/`)

Runs silently on every request before it reaches any route handler. Screens for valid API keys and enforces rate limits.

- **Auth** (`auth.py`) - validates the API key on every request
- **Rate limiting** (`rate_limit.py`) - counts requests per key per window, blocks excess traffic

**Connects to:** Every API route (wraps them all), config (reads limits from app_config)

---

## Session Store (`backend/session_store.py`)

Maintains state across requests. Without it, every message would arrive with no memory of what came before. Each session holds a coach agent instance and tracks activity, message count, and API key association.

- Holds the CoachAgent instance per user
- Tracks message count, last activity, API key association
- Expires sessions that have been inactive too long
- Enforces per-key session limits

**Connects to:** Coach agent (stores and retrieves the agent per session), API routes (every message request goes through it), rate limiter (shares API key identity)

---

## Frontend (`frontend/`)

The browser-based interface. Renders the chat UI, captures microphone audio, opens a streaming connection to receive tokens as they arrive, and sends text or audio to the backend.

- Renders the chat UI
- Captures microphone audio via the browser MediaRecorder API
- Opens an SSE connection to stream tokens as they arrive
- Sends text or audio to the backend and displays the response

**Connects to:** Backend API (all communication goes through HTTP), voice pipeline (audio in, audio out), session store (indirectly, session ID is held in the browser)

---

## Config and Data (`config/`, `data/`, `.env`)

The settings and raw content everything else is built from. Changing these values changes the behaviour of the whole system without touching any logic.

- `config/app_config.py` - all tuneable settings: limits, thresholds, timeouts
- `.env` - secrets and environment-specific values (API keys, URLs)
- `data/` - the raw knowledge files the RAG pipeline is built from

**Connects to:** Everything reads from config. Data connects only to the ingestion script and Qdrant.

---

## Data Flow Summary

| Interaction | Systems Involved |
|---|---|
| User message arrives | Frontend > Backend > Session Store > Coach Agent |
| Coach needs context | Coach Agent > RAG Router > RAG Retriever > Qdrant |
| Response streams back | Coach Agent > Backend > Frontend (SSE) |
| Voice input | Frontend > Voice Routes > STT > Coach Agent > TTS > Frontend |
| Request is screened | Any route > Auth Middleware > Rate Limiter > Route handler |
| Session expires | Session Store > Coach Agent instance is discarded |
