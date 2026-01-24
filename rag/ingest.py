"""
RAG INGEST INSTRUCTIONS
1) Start Qdrant locally (e.g. `docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant`).
2) Run `python -m rag.ingest` to parse the datasets and upsert them into Qdrant.
3) Run `python main.py` and confirm retrieval works inside the CLI.
"""

from __future__ import annotations

import logging
import uuid
from typing import Sequence

from dotenv import load_dotenv
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from rag.config import RagConfig, load_rag_config
from rag.parsing_activities import ActivityChunk, parse_activity_file
from rag.parsing_master import MasterChunk, parse_master_file

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _stable_uuid(value: str) -> str:
    """Return a deterministic UUID for a given chunk id."""

    return str(uuid.uuid5(uuid.NAMESPACE_URL, value))


def _to_nodes(chunks: Sequence[MasterChunk | ActivityChunk]) -> Sequence[TextNode]:
    return [
        TextNode(
            text=chunk.text,
            id_=_stable_uuid(chunk.chunk_id),
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]


def _ensure_collection(client: QdrantClient, name: str, vector_size: int) -> None:
    logger.info("Creating collection %s (size=%s)", name, vector_size)
    client.recreate_collection(
        collection_name=name,
        vectors_config={
            "text-dense": VectorParams(size=vector_size, distance=Distance.COSINE),
        },
    )


def _upsert_nodes(config: RagConfig, client: QdrantClient, collection: str, nodes: Sequence[TextNode]) -> None:
    node_list = list(nodes)
    vector_store = QdrantVectorStore(client=client, collection_name=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(nodes=node_list, storage_context=storage_context)
    logger.info("Inserted %s nodes into %s", len(node_list), collection)


def run_ingest() -> None:
    load_dotenv()
    config = load_rag_config()

    Settings.embed_model = OpenAIEmbedding(model=config.embedding_model, api_key=config.openai_api_key)

    logger.info("Parsing master dataset from %s", config.master_data_path)
    master_chunks = parse_master_file(config.master_data_path)
    logger.info("Parsing activity dataset from %s", config.activity_data_path)
    activity_chunks = parse_activity_file(config.activity_data_path)

    client = QdrantClient(url=config.qdrant_url, api_key=config.qdrant_api_key)

    _ensure_collection(client, config.master_collection, config.embedding_dimensions)
    _ensure_collection(client, config.activities_collection, config.embedding_dimensions)

    _upsert_nodes(config, client, config.master_collection, _to_nodes(master_chunks))
    _upsert_nodes(config, client, config.activities_collection, _to_nodes(activity_chunks))

    logger.info("Ingestion complete.")


if __name__ == "__main__":
    run_ingest()
