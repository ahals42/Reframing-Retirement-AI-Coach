"""CLI entry point for the physical-activity conversational agent."""

from __future__ import annotations

from dotenv import load_dotenv
from openai import OpenAI

from coach import CoachAgent, run_rag_sanity_check
from rag.config import load_rag_config
from rag.retriever import RagRetriever
from rag.router import QueryRouter


def build_agent() -> CoachAgent:
    load_dotenv()
    config = load_rag_config()
    client = OpenAI(api_key=config.openai_api_key)
    retriever = None
    router = QueryRouter()

    try:
        retriever = RagRetriever(config)
        run_rag_sanity_check(retriever)
    except Exception as exc:
        print(f"[Warning] RAG initialization failed: {exc}. Continuing without vector context.")

    return CoachAgent(client=client, model=config.chat_model, retriever=retriever, router=router)


def main() -> None:
    agent = build_agent()
    print(
        "What would you like to talk through today around being active? If you want to see where this lives in your app "
        "or learn about nearby activity options, just ask. (Type 'exit' or 'quit' to stop.)"
    )
    while True:
        try:
            user_text = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_text:
            continue

        if user_text.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            response = agent.generate_response(user_text)
        except Exception as exc:
            print(f"[Error contacting coach model: {exc}]")
            continue

        print(f"Coach: {response}\n")


if __name__ == "__main__":
    main()
