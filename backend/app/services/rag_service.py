"""
RAG Service — ChromaDB + embedding + retrieval.

Manages the vector store for the knowledge base.
Uses ChromaDB's built-in sentence-transformer embeddings.
"""

import logging
import hashlib
from typing import List, Optional, Dict, Any

import chromadb

from app.config import settings

logger = logging.getLogger(__name__)


# ─── Lightweight Text Splitter (replaces langchain dependency) ──

class RecursiveTextSplitter:
    """
    Splits text recursively by separators, producing overlapping chunks.
    Same logic as LangChain's RecursiveCharacterTextSplitter but zero deps.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", ", ", " ", ""]

    def split_text(self, text: str) -> List[str]:
        return self._split(text, self.separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []

        # Find the best separator to split on
        sep = separators[-1] if separators else ""
        for s in separators:
            if s in text:
                sep = s
                break

        parts = text.split(sep) if sep else list(text)
        next_seps = separators[separators.index(sep) + 1:] if sep in separators else []

        chunks = []
        current = ""
        for part in parts:
            candidate = (current + sep + part) if current else part
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current.strip():
                    chunks.append(current.strip())
                # If this single part is too large, recurse with finer separator
                if len(part) > self.chunk_size and next_seps:
                    chunks.extend(self._split(part, next_seps))
                    current = ""
                else:
                    current = part

        if current.strip():
            chunks.append(current.strip())

        # Apply overlap by prepending tail of previous chunk
        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_tail = chunks[i - 1][-self.chunk_overlap:]
                overlapped.append(prev_tail + " " + chunks[i])
            chunks = overlapped

        return chunks


# ─── ChromaDB Client ─────────────────────────────────────────

_chroma_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None

COLLECTION_NAME = "campus_knowledge_base"


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
        )
    return _chroma_client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ─── Text Splitter Instance ─────────────────────────────────

text_splitter = RecursiveTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", ", ", " ", ""],
)


def _generate_chunk_id(source: str, index: int) -> str:
    """Generate a deterministic ID for a chunk to prevent duplicates on re-index."""
    content = f"{source}:{index}"
    return hashlib.md5(content.encode()).hexdigest()


# ─── Public API ──────────────────────────────────────────────

def add_document(
    entry_id: int,
    title: str,
    content: str,
    category: str,
    source_doc: Optional[str] = None,
) -> int:
    """
    Chunk, embed, and store a knowledge base entry.
    Returns the number of chunks created.
    """
    collection = get_collection()

    # First remove any existing chunks for this entry (for updates)
    remove_document(entry_id)

    # Create full text with title for better retrieval
    full_text = f"{title}\n\n{content}"

    # Split into chunks
    chunks = text_splitter.split_text(full_text)

    if not chunks:
        return 0

    # Prepare batch data
    ids = [f"kb_{entry_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "entry_id": entry_id,
            "title": title,
            "category": category,
            "source_doc": source_doc or "",
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    # Add to ChromaDB (embeddings are generated automatically)
    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    logger.info(f"Added {len(chunks)} chunks for KB entry {entry_id}: {title}")
    return len(chunks)


def remove_document(entry_id: int) -> None:
    """Remove all chunks for a knowledge base entry."""
    collection = get_collection()
    try:
        # Get existing chunks for this entry
        existing = collection.get(
            where={"entry_id": entry_id},
        )
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            logger.info(f"Removed {len(existing['ids'])} chunks for KB entry {entry_id}")
    except Exception as e:
        logger.warning(f"Could not remove chunks for entry {entry_id}: {e}")


def query(text: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Query the knowledge base for relevant chunks.
    Returns list of {content, title, category, score}.
    """
    collection = get_collection()

    if collection.count() == 0:
        return []

    try:
        results = collection.query(
            query_texts=[text],
            n_results=min(n_results, collection.count()),
        )

        chunks = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0
                chunks.append({
                    "content": doc,
                    "title": metadata.get("title", ""),
                    "category": metadata.get("category", ""),
                    "score": 1 - distance,  # Convert distance to similarity
                })

        return chunks

    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        return []


def ingest_text_content(text: str, title: str, entry_id: int, category: str = "general") -> int:
    """Ingest raw text content into the vector store."""
    return add_document(entry_id, title, text, category)


def get_collection_stats() -> Dict[str, Any]:
    """Get stats about the vector store."""
    collection = get_collection()
    return {
        "total_chunks": collection.count(),
        "collection_name": COLLECTION_NAME,
    }
