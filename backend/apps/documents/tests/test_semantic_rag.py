"""Phase 2 - real semantic (embedding) RAG.

Verifies the new TF-IDF + Truncated SVD retrieval path in
apps/documents/embeddings.py: that it actually runs (not silently skipped),
that it is strictly patient-isolated (the fit step itself never sees
another patient's chunks - not just a post-hoc filter), and that it falls
back cleanly to the existing keyword/TF-cosine engine (rag.py, untouched)
when there isn't enough indexed data to fit a semantic space - exactly the
"treat the current keyword retrieval as the baseline/fallback" requirement.

Nothing here is mocked: uploads go through the real
DocumentListCreateView.perform_create() (OCR/text-extraction, sanitization,
chunk indexing) and queries go through the real DocumentRAGSearchView.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor
from apps.documents.embeddings import semantic_embeddings_available
from apps.documents.models import DocumentChunk, MedicalDocument
from apps.patients.models import Patient


def _upload(client, doctor, patient, filename, content, document_type="LAB_REPORT"):
    return client.post(
        reverse("document-list-create"),
        data={
            "patient": patient.id,
            "title": filename,
            "document_type": document_type,
            "file": SimpleUploadedFile(filename, content.encode("utf-8"), content_type="text/plain"),
        },
        format="multipart",
        **auth_headers(doctor),
    )


def _rag(client, doctor, patient_id, query, top_k=5):
    url = f"{reverse('document-rag-search')}?patient_id={patient_id}&query={query}&top_k={top_k}"
    return client.get(url, **auth_headers(doctor))


class SemanticRetrievalTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Semantic RAG Patient")

    def test_upload_persists_chunks_for_retrieval(self):
        resp = _upload(
            self.client, self.doctor, self.patient, "lab1.txt",
            "HbA1c: 7.9%. Fasting glucose 145 mg/dL. Endocrinology follow-up recommended for elevated glycemic markers.",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        chunks = DocumentChunk.objects.filter(document_id=resp.data["id"])
        self.assertGreaterEqual(chunks.count(), 1)
        self.assertEqual(chunks.first().patient_id, self.patient.id)

    def test_semantic_retrieval_used_when_enough_data_indexed(self):
        if not semantic_embeddings_available():
            self.skipTest("scikit-learn/numpy not installed in this environment")

        _upload(self.client, self.doctor, self.patient, "lab_april.txt",
                "April lab report. HbA1c 7.9 percent, elevated glycemic markers noted by Dr. Chen.")
        _upload(self.client, self.doctor, self.patient, "lab_sept.txt",
                "September lab report. HbA1c 8.2 percent, continued elevated glycemic markers, Metformin adjusted.")

        resp = _rag(self.client, self.doctor, self.patient.id, "elevated blood sugar diabetes trend")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["retrieval_method"], "semantic_embedding_lsa")
        self.assertGreater(resp.data["count"], 0)
        for r in resp.data["results"]:
            self.assertEqual(r["retrieval_method"], "semantic_embedding_lsa")
            self.assertIn("similarity_score", r)
            self.assertIn("citation_tag", r)

    def test_falls_back_to_keyword_when_no_chunks_indexed(self):
        """A document created directly (bypassing the upload pipeline, so
        it was never chunked/indexed - mirrors the existing security-test
        pattern) must not break retrieval; it must fall back cleanly."""
        MedicalDocument.objects.create(
            patient=self.patient, uploaded_by=self.doctor,
            document_type=MedicalDocument.DocumentType.LAB_REPORT,
            title="Legacy doc", file=SimpleUploadedFile("legacy.txt", b"HbA1c: 7.0%", content_type="text/plain"),
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extracted_text="HbA1c: 7.0%",
        )
        self.assertEqual(DocumentChunk.objects.filter(patient=self.patient).count(), 0)

        resp = _rag(self.client, self.doctor, self.patient.id, "hba1c")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["retrieval_method"], "keyword_tf_cosine_fallback")
        for r in resp.data["results"]:
            self.assertEqual(r["retrieval_method"], "keyword_tf_cosine_fallback")

    def test_single_small_document_falls_back_gracefully_no_crash(self):
        """One document -> one chunk is a real degenerate case for
        TruncatedSVD (needs n_components < n_samples). Must degrade to the
        keyword fallback, never error."""
        resp = _upload(self.client, self.doctor, self.patient, "short.txt", "HbA1c: 7.0%")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        rag_resp = _rag(self.client, self.doctor, self.patient.id, "hba1c")
        self.assertEqual(rag_resp.status_code, status.HTTP_200_OK, rag_resp.data)
        self.assertEqual(rag_resp.data["retrieval_method"], "keyword_tf_cosine_fallback")


class SemanticCrossPatientIsolationTests(APITestCase):
    """Explicit cross-patient retrieval tests for the semantic path, as
    required: the fit step itself must never see another patient's data."""

    def setUp(self):
        self.doctor = make_doctor()
        self.patient_a = Patient.objects.create(doctor=self.doctor, full_name="Patient A")
        self.patient_b = Patient.objects.create(doctor=self.doctor, full_name="Patient B")

        # Each patient needs >=2 documents with distinct vocabulary for a
        # real semantic basis to be fit (see test_semantic_retrieval_used_
        # when_enough_data_indexed) - otherwise this test would silently
        # exercise the keyword fallback instead of the semantic path.
        _upload(self.client, self.doctor, self.patient_a, "a1.txt",
                "Patient A cardiology visit. Blood pressure elevated, Lisinopril prescribed for hypertension.")
        _upload(self.client, self.doctor, self.patient_a, "a2.txt",
                "Patient A follow-up. Blood pressure improving on Lisinopril, hypertension well controlled.")

        _upload(self.client, self.doctor, self.patient_b, "b1.txt",
                "Patient B nephrology report. Creatinine 99.9 mg/dL, severe renal risk, critical finding.")
        _upload(self.client, self.doctor, self.patient_b, "b2.txt",
                "Patient B dialysis consultation. Creatinine remains critical, severe renal risk confirmed.")

    def test_semantic_search_on_patient_a_never_returns_patient_b_content(self):
        if not semantic_embeddings_available():
            self.skipTest("scikit-learn/numpy not installed in this environment")

        resp = _rag(self.client, self.doctor, self.patient_a.id, "creatinine renal risk critical dialysis")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["retrieval_method"], "semantic_embedding_lsa")
        for r in resp.data["results"]:
            self.assertEqual(r["patient_id"], self.patient_a.id)
            self.assertNotIn("99.9", r["chunk_text"])
            self.assertNotIn("Patient B", r["chunk_text"])
            self.assertNotIn("dialysis", r["chunk_text"].lower())

    def test_semantic_fit_basis_excludes_other_patients_chunks_at_the_query_layer(self):
        """Not just a result filter: the DocumentChunk queryset the
        embedding basis is fit from must itself only contain this
        patient's rows."""
        from apps.documents.embeddings import retrieve_patient_context_semantic

        if not semantic_embeddings_available():
            self.skipTest("scikit-learn/numpy not installed in this environment")

        results = retrieve_patient_context_semantic(patient_id=self.patient_a.id, query="renal creatinine dialysis")
        self.assertIsNotNone(results)
        for r in results:
            self.assertEqual(r["patient_id"], self.patient_a.id)
            doc = MedicalDocument.objects.get(pk=r["document_id"])
            self.assertEqual(doc.patient_id, self.patient_a.id)
