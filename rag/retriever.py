"""Runtime retrieval helpers that connect to Qdrant via LlamaIndex."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from rag.config import RagConfig
from rag.router import ActivityFilters, RouteDecision


def _node_content(node: Any) -> str:
    if hasattr(node, "get_content"):
        try:
            return node.get_content(metadata_mode="all")
        except TypeError:
            return node.get_content()
    return getattr(node, "text", "")


def _truncate(text: str, limit: int = 1200) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


@dataclass
class RetrievedChunk:
    doc_type: str
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None

    def label(self) -> str:
        if self.doc_type == "master":
            lesson = self.metadata.get("lesson_number")
            slide = self.metadata.get("slide_number")
            title = self.metadata.get("slide_title") or ""
            return f"Lesson {lesson} Slide {slide}: {title}".strip()
        activity_name = self.metadata.get("activity_name", "Activity")
        location = self.metadata.get("location", "")
        return f"{activity_name} ({location})".strip()

    def reference(self) -> Optional[str]:
        if self.doc_type == "master":
            lesson = self.metadata.get("lesson_number")
            lesson_title = self.metadata.get("lesson_title") or "Untitled lesson"
            slide = self.metadata.get("slide_number")
            slide_title = self.metadata.get("slide_title") or "Untitled slide"
            return f"Lesson {lesson}: {lesson_title} -> Slide {slide} ({slide_title})"
        if self.doc_type == "activity":
            activity_id = self.metadata.get("activity_id")
            name = self.metadata.get("activity_name", "Activity")
            location = self.metadata.get("location", "Location TBD")
            schedule = self.metadata.get("schedule", "Schedule TBD")
            cost = self.metadata.get("cost_raw", "Cost unknown")
            return f"Activity {activity_id}: {name} — {location}, {schedule}, {cost}"
        return None


@dataclass
class RetrievalResult:
    master_chunks: Sequence[RetrievedChunk]
    activity_chunks: Sequence[RetrievedChunk]

    def _reference_sort_key(self, chunk: RetrievedChunk) -> tuple:
        if chunk.doc_type == "master":
            lesson = chunk.metadata.get("lesson_number") or 0
            slide = chunk.metadata.get("slide_number") or 0
            global_idx = chunk.metadata.get("global_slide_number") or 0
            return (0, int(lesson), int(slide), int(global_idx))
        if chunk.doc_type == "activity":
            activity_id = chunk.metadata.get("activity_id") or 0
            return (1, int(activity_id))
        return (2, 0)

    def build_prompt_context(self) -> str:
        sections: List[str] = []
        if self.master_chunks:
            sections.append(self._format_section("Master slides", self.master_chunks))
        if self.activity_chunks:
            sections.append(self._format_section("Local activities", self.activity_chunks))
        return "\n\n".join(sections)

    def _format_section(self, title: str, chunks: Sequence[RetrievedChunk]) -> str:
        lines = [f"{title}:"]
        for chunk in chunks:
            lines.append(f"- {chunk.label()}\n  {_truncate(chunk.text)}")
        return "\n".join(lines)

    def references(self) -> List[str]:
        refs: List[str] = []
        seen = set()
        chunks = list(self.master_chunks) + list(self.activity_chunks)
        for chunk in sorted(chunks, key=self._reference_sort_key):
            citation = chunk.reference()
            if citation and citation not in seen:
                seen.add(citation)
                refs.append(citation)
        return refs


class RagRetriever:
    """Builds query engines for the master and activity indexes."""

    def __init__(self, config: RagConfig) -> None:
        self.config = config
        Settings.embed_model = OpenAIEmbedding(model=config.embedding_model, api_key=config.openai_api_key)
        self.client = QdrantClient(url=config.qdrant_url, api_key=config.qdrant_api_key)
        self.master_index = self._build_index(config.master_collection)
        self.activity_index = self._build_index(config.activities_collection)

    def _build_index(self, collection_name: str) -> VectorStoreIndex:
        vector_store = QdrantVectorStore(client=self.client, collection_name=collection_name)
        return VectorStoreIndex.from_vector_store(vector_store=vector_store)

    def _build_retriever(self, index: VectorStoreIndex, top_k: int) -> VectorIndexRetriever:
        return index.as_retriever(similarity_top_k=top_k)

    def retrieve_master(self, query: str, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        retriever = self._build_retriever(self.master_index, top_k or self.config.master_top_k)
        nodes = retriever.retrieve(query)
        return [
            RetrievedChunk(
                doc_type=node.node.metadata.get("doc_type", "master"),
                text=_node_content(node.node),
                metadata=node.node.metadata,
                score=node.score,
            )
            for node in nodes
            if not node.node.metadata.get("do_not_reference", False)
        ]

    def retrieve_activities(
        self,
        query: str,
        *,
        filters: Optional[ActivityFilters] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        base_top_k = top_k or self.config.activity_top_k
        retrieval_top_k = max(base_top_k * 2, 8) if filters and filters.days else base_top_k
        retriever = self._build_retriever(self.activity_index, retrieval_top_k)

        nodes = retriever.retrieve(query)
        wrapped = [
            RetrievedChunk(
                doc_type=node.node.metadata.get("doc_type", "activity"),
                text=_node_content(node.node),
                metadata=node.node.metadata,
                score=node.score,
            )
            for node in nodes
        ]
        if filters:
            wrapped = self._apply_activity_filters(wrapped, filters)
        return wrapped[:base_top_k]

    def _apply_activity_filters(self, chunks: List[RetrievedChunk], filters: ActivityFilters) -> List[RetrievedChunk]:
        def matches(chunk: RetrievedChunk) -> bool:
            metadata = chunk.metadata
            if filters.cost_label:
                if metadata.get("cost_label") != filters.cost_label:
                    return False
            if filters.activity_type:
                if metadata.get("activity_type") != filters.activity_type:
                    return False
            if filters.location:
                location = (metadata.get("location") or "").lower()
                aliases = [alias.lower() for alias in metadata.get("aliases", [])]
                target = filters.location.lower()
                if target not in location and target not in aliases:
                    return False
            if filters.days:
                chunk_days = [day.lower() for day in metadata.get("days", [])]
                if not any(day.lower() in chunk_days for day in filters.days):
                    return False
            return True

        return [chunk for chunk in chunks if matches(chunk)]

    def gather_context(self, query: str, decision: RouteDecision) -> RetrievalResult:
        master_chunks: List[RetrievedChunk] = []
        activity_chunks: List[RetrievedChunk] = []

        if decision.use_master:
            master_chunks = self.retrieve_master(query)
        if decision.use_activities:
            activity_chunks = self.retrieve_activities(query, filters=decision.activity_filters)

        return RetrievalResult(master_chunks=master_chunks, activity_chunks=activity_chunks)
