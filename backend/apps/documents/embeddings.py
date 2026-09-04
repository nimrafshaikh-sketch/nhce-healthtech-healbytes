"""Real semantic embeddings for patient-scoped RAG (Phase 2).

Upgrades the existing keyword/TF-cosine retrieval in `apps/documents/rag.py`
(kept exactly as-is, and used as the automatic fallback - see
`DocumentRAGSearchView` in `views.py`) with a genuine dense semantic
embedding: TF-IDF + Truncated SVD, i.e. Latent Semantic Analysis (LSA).

Why this technique, and not a hosted/LLM embedding API:
- This project's rules do not allow an LLM or an external AI API at this
  stage. A hosted embeddings API (OpenAI/Cohere/etc.) is the same category
  of dependency and is deliberately not used here.
- LSA is a real, well-established semantic embedding technique. It captures
  co-occurrence-based similarity beyond exact keyword overlap - the
  specific limitation the previous TF-cosine implementation had (documented
  in HealBytes_Independent_Verification_Report.md §2/§4: "a query for
  'diabetes' will not match a document that only says 'elevated glycemic
  markers'"). It is fully deterministic and offline (`scikit-learn`/`numpy`
  only, fixed `random_state`, no model download, no network call at
  inference time).
- It is honest about what it is: not a transformer/neural embedding. This
  module says so rather than overclaiming, matching the project's existing
  practice of not mislabeling capabilities (see the same audit report on
  the previous "OCR/Vision" and "RAG" claims).

CRITICAL SECURITY INVARIANT (identical pattern to rag.py): the TF-IDF/SVD
basis is fit ONLY over one patient's own persisted `DocumentChunk` rows.
Patient isolation happens at the fit step, before any similarity ranking
exists - it is not a filter applied after a shared index is searched.
"""

import logging
from typing import Any, Dict, List, Optional

from apps.documents.models import DocumentChunk
from apps.documents.rag import chunk_document_text  # existing chunker, reused as-is

logger = logging.getLogger(__name__)

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD

    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when deps are absent
    _SKLEARN_AVAILABLE = False

# Fixed so the same chunk corpus always produces the same embeddings, and a
# query embedded against that corpus is always comparable - no hidden
# randomness between runs.
_SVD_RANDOM_STATE = 42
_MAX_COMPONENTS = 32


def semantic_embeddings_available() -> bool:
    """Whether the real embedding path can run at all in this environment."""
    return _SKLEARN_AVAILABLE


def _fit_patient_embedding_space(chunk_texts: List[str]):
    """Fits a TF-IDF + Truncated SVD basis over one patient's chunk corpus.

    Returns (vectorizer, svd, chunk_vectors), or None when there isn't
    enough data to fit a meaningful space. This is a real mathematical
    guard, not a disguised fallback: TruncatedSVD requires
    n_components < n_features and n_components < n_samples, which a
    single-chunk or near-empty corpus cannot satisfy.
    """
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(chunk_texts)

    n_samples, n_features = tfidf_matrix.shape
    n_components = min(_MAX_COMPONENTS, n_samples - 1, n_features - 1)
    if n_components < 1:
        return None

    svd = TruncatedSVD(n_components=n_components, random_state=_SVD_RANDOM_STATE)
    chunk_vectors = svd.fit_transform(tfidf_matrix)
    return vectorizer, svd, chunk_vectors


def retrieve_patient_context_semantic(patient_id: int, query: str, top_k: int = 4) -> Optional[List[Dict[str, Any]]]:
    """Real embedding-based retrieval, strictly patient-scoped.

    Returns None - never an empty-but-misleading list - when semantic
    retrieval genuinely cannot run (missing dependency, or too little
    indexed data to fit a basis), so the caller can fall back to the
    existing keyword/TF-cosine retrieval instead of silently reporting
    "no results" when the real reason is "this method doesn't apply yet."
    """
    if not _SKLEARN_AVAILABLE:
        logger.info("scikit-learn/numpy not installed; semantic retrieval unavailable.")
        return None

    # HARD PATIENT ISOLATION FILTER - same pattern as rag.py: filter by
    # patient_id before anything else touches the data. No other patient's
    # chunks are ever loaded into memory for this call, let alone fit into
    # the embedding basis.
    chunks = list(
        DocumentChunk.objects.filter(patient_id=patient_id)
        .select_related("document")
        .order_by("document_id", "chunk_index")
    )
    if not chunks:
        return None

    chunk_texts = [c.text for c in chunks]
    fit_result = _fit_patient_embedding_space(chunk_texts)
    if fit_result is None:
        return None
    vectorizer, svd, chunk_vectors = fit_result

    query_tfidf = vectorizer.transform([query])
    query_vector = svd.transform(query_tfidf)[0]
    query_norm = np.linalg.norm(query_vector)

    results = []
    for chunk, vector in zip(chunks, chunk_vectors):
        vector_norm = np.linalg.norm(vector)
        if query_norm == 0 or vector_norm == 0:
            similarity = 0.0
        else:
            similarity = float(np.dot(query_vector, vector) / (query_norm * vector_norm))

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
            "similarity_score": round(similarity, 4),
            "citation_tag": f"[Source: {chunk.document_title} (Doc #{doc.id})]",
            "retrieval_method": "semantic_embedding_lsa",
        })

    results.sort(key=lambda r: (r["similarity_score"], r["document_date"]), reverse=True)
    return results[:top_k]


def index_document_chunks(document) -> int:
    """(Re)indexes one document's chunks into the persisted DocumentChunk
    store - the "chunking" + "index for retrieval" stages of the pipeline.
    Replaces this document's previous chunk rows (if any), so reprocessing
    a document never leaves stale chunks behind. Returns the chunk count.

    Does not itself compute or store embedding vectors - per the module
    docstring, embeddings are computed on demand from these rows at
    retrieval time (always scoped to one patient's own chunks), so a stored
    vector can never go stale relative to the chunk text it came from.
    """
    text = document.extracted_text or document.title
    chunk_texts = chunk_document_text(text)

    # extracted_data.extracted_date (apps/documents/ocr.py) is a raw regex
    # match, not a validated date - not trustworthy enough to use in place
    # of the real upload timestamp, so document_date stays created_at.
    document_date = document.created_at

    DocumentChunk.objects.filter(document=document).delete()
    chunk_rows = [
        DocumentChunk(
            document=document,
            patient_id=document.patient_id,
            chunk_index=idx,
            text=chunk_text,
            page=None,
            document_type=document.document_type,
            document_title=document.title,
            document_date=document_date,
        )
        for idx, chunk_text in enumerate(chunk_texts)
    ]
    DocumentChunk.objects.bulk_create(chunk_rows)
    return len(chunk_rows)
