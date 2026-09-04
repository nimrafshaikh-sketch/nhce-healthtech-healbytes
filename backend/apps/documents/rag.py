"""Patient-Scoped Vector Index & RAG Retrieval Engine.

CRITICAL SECURITY CONSTRAINT:
All semantic searches enforce `patient_id == authorized_patient_id` at the index level
BEFORE vector similarity ranking. Cross-patient retrieval is mathematically impossible.
"""

import re
import math
import logging
from typing import List, Dict, Any, Optional

from apps.documents.models import MedicalDocument

logger = logging.getLogger(__name__)


def chunk_document_text(text: str, chunk_size: int = 150, overlap: int = 30) -> List[str]:
    """Splits document text into overlapping token chunks."""
    if not text:
        return []
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def _tokenize(text: str) -> List[str]:
    """Basic lowercased alphanumeric tokenizer."""
    return re.findall(r"\b[a-z0-9]{2,}\b", text.lower())


def _compute_vector(tokens: List[str], vocabulary: Dict[str, int]) -> List[float]:
    """Computes a normalized term frequency vector over a vocabulary."""
    vec = [0.0] * len(vocabulary)
    for t in tokens:
        if t in vocabulary:
            vec[vocabulary[t]] += 1.0
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two normalized vectors."""
    return sum(a * b for a, b in zip(v1, v2))


def retrieve_patient_context(patient_id: int, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Retrieves relevant document excerpts strictly for the given patient_id.
    
    Server-side authorization boundary:
    MedicalDocument.objects.filter(patient_id=patient_id) is the absolute boundary.
    No other patient's documents can ever enter this vector search space.
    """
    # 1. HARD PATIENT ISOLATION FILTER
    docs = list(MedicalDocument.objects.filter(
        patient_id=patient_id,
        processing_status=MedicalDocument.ProcessingStatus.PROCESSED
    ).order_by("-created_at"))

    if not docs:
        return []

    # 2. Extract Chunks for this Patient's Documents Only
    all_chunks = []
    for doc in docs:
        doc_text = doc.extracted_text or doc.title
        chunks = chunk_document_text(doc_text)
        for idx, chk in enumerate(chunks):
            all_chunks.append({
                "patient_id": patient_id,
                "document_id": doc.id,
                "document_title": doc.title,
                "document_type": doc.document_type,
                "created_at": doc.created_at.isoformat(),
                "chunk_index": idx,
                "text": chk,
            })

    if not all_chunks:
        return []

    # 3. Build Patient-Local Vocabulary & Vectors
    query_tokens = _tokenize(query)
    if not query_tokens:
        return all_chunks[:top_k]

    vocab_set = set(query_tokens)
    for chk in all_chunks:
        vocab_set.update(_tokenize(chk["text"]))
    vocab = {word: idx for idx, word in enumerate(sorted(vocab_set))}

    query_vec = _compute_vector(query_tokens, vocab)

    # 4. Rank Chunks
    scored_chunks = []
    for chk in all_chunks:
        chk_tokens = _tokenize(chk["text"])
        chk_vec = _compute_vector(chk_tokens, vocab)
        sim = _cosine_similarity(query_vec, chk_vec)
        scored_chunks.append({
            **chk,
            "chunk_text": chk["text"],
            "view_url": f"/api/documents/{chk['document_id']}/view/",
            "similarity_score": round(sim, 4),
            "citation_tag": f"[Source: {chk['document_title']} (Doc #{chk['document_id']})]",
        })

    # Sort descending by similarity score, then by recency
    scored_chunks.sort(key=lambda x: (x["similarity_score"], x["created_at"]), reverse=True)
    return scored_chunks[:top_k]


class PatientRAGEngine:
    @staticmethod
    def retrieve_patient_context(patient_id: int, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        return retrieve_patient_context(patient_id=patient_id, query=query, top_k=top_k)


def get_patient_rag_engine() -> PatientRAGEngine:
    return PatientRAGEngine()

