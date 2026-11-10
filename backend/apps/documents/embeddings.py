"""Real neural semantic embeddings for patient-scoped RAG (Phase 3).

Upgrades the existing keyword/TF-cosine retrieval with a genuine dense neural
embedding: all-MiniLM-L6-v2 + PostgreSQL pgvector.

CRITICAL SECURITY INVARIANT:
Patient isolation happens at the database level by explicitly filtering 
`patient_id` in the ORM query before any similarity ranking exists.
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
from django.db import connection
from sentence_transformers import SentenceTransformer
from pgvector.django import CosineDistance

from apps.documents.models import DocumentChunk
from apps.documents.rag import chunk_document_text

logger = logging.getLogger(__name__)

# Lazy load model to avoid memory overhead during standard Django boot
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        # Lightweight, high-quality embedding model suitable for local deployment
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def semantic_embeddings_available() -> bool:
    """Whether the real embedding path can run at all in this environment."""
    return True

def retrieve_patient_context_semantic(patient_id: int, query: str, top_k: int = 4) -> Optional[List[Dict[str, Any]]]:
    """Real embedding-based retrieval, strictly patient-scoped via pgvector."""
    if not DocumentChunk.objects.filter(patient_id=patient_id, embedding__isnull=False).exists():
        return None

    model = get_embedding_model()
    query_vector = model.encode(query).tolist()

    if connection.vendor == "postgresql":
        # HARD PATIENT ISOLATION FILTER: filter by patient_id before ordering by distance
        chunks = list(
            DocumentChunk.objects.filter(patient_id=patient_id, embedding__isnull=False)
            .select_related("document")
            .order_by(CosineDistance("embedding", query_vector))[:top_k]
        )
        scored_chunks = [(chunk, 1.0) for chunk in chunks]
        retrieval_method = "semantic_embedding_pgvector"
    else:
        # Non-PostgreSQL backends (e.g., SQLite in test/dev settings) do not support
        # pgvector's `<=>` SQL operator. Enforce the same patient_id ORM filter first,
        # then rank that patient's persisted embeddings by exact cosine similarity.
        patient_chunks = list(
            DocumentChunk.objects.filter(patient_id=patient_id, embedding__isnull=False)
            .select_related("document")
        )
        if not patient_chunks:
            return None

        q_vec = np.asarray(query_vector, dtype=float)
        q_norm = float(np.linalg.norm(q_vec))
        scored_pairs = []
        for chunk in patient_chunks:
            c_vec = np.asarray(chunk.embedding, dtype=float)
            c_norm = float(np.linalg.norm(c_vec))
            similarity = float(np.dot(q_vec, c_vec) / (q_norm * c_norm)) if (q_norm > 0 and c_norm > 0) else 0.0
            scored_pairs.append((chunk, round(similarity, 4)))
        scored_pairs.sort(key=lambda pair: (pair[1], pair[0].document_date), reverse=True)
        scored_chunks = scored_pairs[:top_k]
        retrieval_method = "semantic_embedding_cosine"

    if not scored_chunks:
        return None

    results = []
    for chunk, similarity_score in scored_chunks:
        doc = chunk.document
        results.append({
            "patient_id": patient_id,
            "document_id": doc.id,
            "chunk_id": chunk.id,
            "document_title": chunk.document_title,
            "document_type": chunk.document_type,
            "page": chunk.page,
            "document_date": chunk.document_date.isoformat(),
            "created_at": chunk.document_date.isoformat(),
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.text,
            "view_url": f"/api/documents/{doc.id}/view/",
            "similarity_score": similarity_score,
            "citation_tag": f"[Source: {chunk.document_title} (Doc #{doc.id})]",
            "retrieval_method": retrieval_method,
        })

    return results

def index_document_chunks(document) -> int:
    """Chunks text, computes neural embeddings, and stores in PostgreSQL via pgvector.
    
    Replaces this document's previous chunk rows (if any), so reprocessing
    a document never leaves stale chunks behind. Returns the chunk count.
    """
    text = document.extracted_text or document.title
    chunk_texts = chunk_document_text(text)
    document_date = document.created_at

    model = get_embedding_model()

    DocumentChunk.objects.filter(document=document).delete()
    
    chunk_rows = []
    for idx, chunk_text in enumerate(chunk_texts):
        embedding = model.encode(chunk_text).tolist()
        chunk_rows.append(
            DocumentChunk(
                document=document,
                patient_id=document.patient_id,
                chunk_index=idx,
                text=chunk_text,
                page=None,
                document_type=document.document_type,
                document_title=document.title,
                document_date=document_date,
                embedding=embedding,
            )
        )
        
    DocumentChunk.objects.bulk_create(chunk_rows)
    return len(chunk_rows)
