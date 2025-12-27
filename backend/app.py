"""FastAPI backend that exposes the coach over HTTP with streaming responses."""

from __future__ import annotations

import json
from typing import Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import OpenAI

from coach import CoachAgent, run_rag_sanity_check
from rag.config import load_rag_config
from rag.retriever import RagRetriever
from rag.router import QueryRouter

from .models import DeleteSessionResponse, MessageRequest, SessionCreateResponse
from .session_store import InMemorySessionStore

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


session_store = InMemorySessionStore(_agent_factory, ttl_minutes=90)

app = FastAPI(title="Reframing Retirement Coach API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/sessions", response_model=SessionCreateResponse)
def create_session() -> SessionCreateResponse:
    session_id = session_store.create()
    return SessionCreateResponse(session_id=session_id)


@app.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
def delete_session(session_id: str) -> DeleteSessionResponse:
    session_store.delete(session_id)
    return DeleteSessionResponse(message="Session cleared")


@app.post("/sessions/{session_id}/messages")
def stream_message(session_id: str, payload: MessageRequest) -> StreamingResponse:
    record = session_store.get(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Unknown session")

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
            yield _as_event("error", {"error": str(exc)})
            return

        state = record.agent.snapshot()
        yield _as_event("done", {"text": final_reply, "state": state})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _as_event(event_type: str, payload: dict) -> str:
    payload = {"type": event_type, **payload}
    return json.dumps(payload) + "\n"
