"""FastAPI backend that exposes the coach over HTTP with streaming responses."""

from __future__ import annotations

import json
import os
import logging
from typing import Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from coach import CoachAgent, run_rag_sanity_check
from rag.config import load_rag_config
from rag.retriever import RagRetriever
from rag.router import QueryRouter

from .models import DeleteSessionResponse, MessageRequest, SessionCreateResponse
from .session_store import InMemorySessionStore
from .voice.routes import create_voice_router
from .middleware.auth import require_api_key
from .middleware.rate_limit import limiter, RATE_LIMITS

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

config = load_rag_config()
client = OpenAI(api_key=config.openai_api_key)

retriever = None
try:
    retriever = RagRetriever(config)
    run_rag_sanity_check(retriever)
except Exception as exc:
    print(f"[Warning] RAG initialization failed: {exc}. Continuing without vector context.")


def _agent_factory() -> CoachAgent:
    return CoachAgent(client=client, model=config.chat_model, retriever=retriever, router=QueryRouter())


session_store = InMemorySessionStore(_agent_factory, ttl_minutes=int(os.getenv("SESSION_TTL_MINUTES", "90")))

app = FastAPI(title="Reframing Retirement Coach API", version="0.1.0")

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS with restricted origins
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restricted origins from environment
    allow_credentials=False,  # No credentials with specific origins
    allow_methods=["GET", "POST", "DELETE"],  # Only needed methods
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],  # Only needed headers
)

# Include voice routes with authentication
app.include_router(create_voice_router(session_store, client))

logger.info("Application initialized successfully")


@app.get("/healthz")
@require_api_key
async def health_check(request: Request) -> dict:
    """
    Health check endpoint with authentication.
    Returns basic application status.
    """
    return {
        "status": "ok",
        "service": "reframing-retirement-coach",
        "version": "0.1.0",
        "rag_enabled": retriever is not None
    }


@app.post("/sessions", response_model=SessionCreateResponse)
@require_api_key
@limiter.limit(f"{RATE_LIMITS['session_creation_per_hour']}/hour")
async def create_session(request: Request) -> SessionCreateResponse:
    """
    Create a new anonymous coaching session.
    Requires API key authentication.
    Rate limited per API key.
    """
    try:
        # Pass API key hash to session store for tracking
        api_key_hash = request.state.api_key[:8] if request.state.api_key else None
        session_id = session_store.create(api_key_hash=api_key_hash)
        logger.info(f"Created session {session_id} for API key {api_key_hash}...")
        return SessionCreateResponse(session_id=session_id)
    except RuntimeError as exc:
        # Session limit exceeded
        logger.warning(f"Session creation failed (limit exceeded): {exc}")
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        logger.error(f"Failed to create session: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@app.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
@require_api_key
async def delete_session(request: Request, session_id: str) -> DeleteSessionResponse:
    """
    Delete a coaching session.
    Requires API key authentication.
    """
    try:
        session_store.delete(session_id)
        logger.info(f"Deleted session {session_id} for API key {request.state.api_key[:8]}...")
        return DeleteSessionResponse(message="Session cleared")
    except Exception as exc:
        logger.error(f"Failed to delete session {session_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@app.post("/sessions/{session_id}/messages")
@require_api_key
@limiter.limit(f"{RATE_LIMITS['messages_per_hour']}/hour")
async def stream_message(request: Request, session_id: str, payload: MessageRequest) -> StreamingResponse:
    """
    Stream coaching response for a message.
    Requires API key authentication.
    Rate limited per API key.
    """
    record = session_store.get(session_id)
    if not record:
        logger.warning(f"Session {session_id} not found")
        raise HTTPException(status_code=404, detail="Unknown session")

    # Log message request (without sensitive content)
    logger.info(
        f"Message request for session {session_id} "
        f"from API key {request.state.api_key[:8]}... "
        f"(length: {len(payload.text)} chars)"
    )

    def event_stream() -> Iterator[str]:
        stream = record.agent.stream_response(payload.text)
        final_reply = ""
        try:
            while True:
                chunk = next(stream)
                if not chunk:
                    continue
                yield _as_event("token", {"text": chunk})
        except StopIteration as stop:
            final_reply = stop.value or ""
        except Exception as exc:
            logger.error(f"Error during streaming for session {session_id}: {exc}")
            yield _as_event("error", {"error": "An error occurred during response generation"})
            return

        state = record.agent.snapshot()
        yield _as_event("done", {"text": final_reply, "state": state})

        logger.info(f"Completed message stream for session {session_id}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _as_event(event_type: str, payload: dict) -> str:
    payload = {"type": event_type, **payload}
    return json.dumps(payload) + "\n"
