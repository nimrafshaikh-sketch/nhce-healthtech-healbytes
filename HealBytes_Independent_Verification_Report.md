# HealBytes Independent Verification Report

**Scope audited:** uncommitted working-tree changes on `feature/ai-history` implementing "Phase 2" — `backend/apps/documents/` (models, OCR, RAG, views, serializers, migrations), `backend/apps/patients/clinical_brief.py`, `backend/apps/core/middleware.py`, `backend/verify_e2e_live.py`, plus diffs to `qr/views.py`, `qr/tests/test_qr.py`, `accounts/urls.py`/`views.py`, `medications/serializers.py`, `patients/analytics_views.py`, `patients/tests/test_ai_summary.py`, `config/settings/base.py`, `config/urls.py`, and new frontend files (`documents.api.js`, `DocumentUploadModal.jsx`, `PrescriptionVerificationModal.jsx`, `pages/lab/`, `pages/receptionist/`).

**Method:** static code reading (every new/changed file read in full, diffed against git HEAD), dependency inventory (`requirements.txt`), and **live dynamic execution** — both venvs rebuilt from scratch in an isolated sandbox, Django + FastAPI servers actually started, the project's own `verify_e2e_live.py` actually run against them, and an independent adversarial script (patient isolation, IDOR, image-OCR, QR-permanence, malicious-upload probes) actually run against the live API. Nothing in this report is inferred from comments or claims alone unless explicitly marked `NOT VERIFIED`.

---

## Executive Verdict

**FAIL — CRITICAL SECURITY/ARCHITECTURE ISSUE**

The RAG patient-isolation filter is real and held under live adversarial testing. OCR-style text entity extraction is real (not hard-coded) for machine-readable text. The human-in-the-loop prescription flow is real. Second-visit patient continuity is real. But the "Phase 2" changes **deleted the only authorization check that gated QR-based clinical access**, and this was live-confirmed: any authenticated doctor account — including one registered seconds earlier with no relationship to the patient — can scan a patient's QR and receive that patient's full profile (including the `medical_notes` field), active medications, check-ins, and complete Clinical Brief, and can then stream that patient's original uploaded documents **indefinitely**, because the document-access check has no expiry and no re-verification. The regression test that used to catch this (`test_unassigned_doctor_forbidden`) was renamed and its assertion flipped to expect success instead of `403`. Separately, the RAG endpoint's own intended fallback authorization path is dead code that live-crashes with an unhandled `FieldError` (HTTP 500) rather than denying access, querying model fields that do not exist. "OCR/Vision" does not process images at all — a real PNG upload is live-confirmed to produce zero extracted findings. These are the exact P0 categories the audit brief calls "QR bypass," "unauthorized medical document access," and "cross-patient data leakage."

---

## 1. What Actually Works (verified)

- **RAG server-side patient isolation, live-tested.** `retrieve_patient_context()` (`backend/apps/documents/rag.py:66`) filters `MedicalDocument.objects.filter(patient_id=patient_id, ...)` **before** any tokenizing/scoring happens — there is no code path where another patient's rows enter the candidate set. Live test: created Patient A (HbA1c 7.9) and Patient B (HbA1c 99.9, "Severe Renal Risk"), queried Patient A's RAG endpoint with Patient B's exact keywords ("99.9 metformin critical") — zero Patient-B content returned. The project's own `verify_e2e_live.py` step 33 confirms the same independently.
- **OCR-style text entity extraction is real, not hard-coded**, for machine-readable text. `backend/apps/documents/ocr.py` regex-parses `KNOWN_LAB_PATTERNS`/`KNOWN_DRUGS` dynamically against whatever text is supplied. Live test: uploaded a plain-text lab report containing `HbA1c: 7.9%` → API returned `numeric_value: 7.9` computed live from the document body, not a fixture. A second document with `HbA1c: 8.2%` produced `8.2` at a later date, and the trend computation in `clinical_brief.py` correctly derived `"increased from 7.9% to 8.2%"`.
- **Human-in-the-loop prescription verification is real.** `DocumentListCreateView.perform_create` never creates a `Medication` row on upload — it only sets `extraction_status = REVIEW_REQUIRED` for prescriptions. A `Medication` row is created only via a doctor's explicit `POST /api/documents/<id>/verify-prescription/` (`PrescriptionVerifyView`), live-confirmed.
- **Second-visit patient continuity is real** — searching for the same phone number twice returns exactly one `Patient` row across two appointments (`verify_e2e_live.py` steps 25–26, live-reproduced).
- **Graceful AI-engine-down degradation is real**, not aspirational: `apps/patients/tests/test_ai_summary.py::test_ai_engine_unavailable_returns_graceful_structured_fallback` passed live — when `get_patient_history_summary` returns `None`, the endpoint still returns `200` with a full structured `clinical_brief`, because `clinical_brief.py` never touches the FastAPI AI Engine at all (it reads only Django ORM data + the local RAG function).
- **File size and extension limits work as coded**: a 16 MB upload was rejected (15 MB cap enforced), a `.exe` extension was rejected, and path-traversal filenames (`../../../../etc/passwd.txt`) are neutralized because `document_file_path()` (`models.py:9`) discards the original filename entirely and writes to `protected_documents/patient_<id>/<uuid4>.ext`.
- **Backend test suite: 115/115 pass, live-run** in this sandbox from a clean install. **AI-Engine test suite: 303/303 pass, live-run.** Both numbers in the "previous report" are independently reproduced. (Frontend build could not be verified in this sandbox — see §9.)

## 2. What Is Partially Working

- **"RAG" is not vector/embedding search.** `rag.py` builds a **fresh, in-memory, per-request term-frequency vector** using `re.findall` tokenization and hand-rolled cosine similarity (`_compute_vector`, `_cosine_similarity`) — no embedding model, no ANN index, no vector database, nothing persisted between requests. It is real and it does isolate by patient correctly, but it is closer to keyword/TF search than "RAG" in the sense the audit brief means, and it will not scale or generalize semantically (e.g., a query for "diabetes" will not match a document that only says "elevated glycemic markers").
- **The Clinical Brief has no LLM anywhere.** `clinical_brief.py` is 100% deterministic Python string formatting (f-strings) over ORM data. This is actually good for factual grounding (nothing is generated that isn't in the data), but it also means "AI synthesis" is a misnomer — it's a template, and the "conditions" inference is a **shallow keyword rule** (any Metformin/Glipizide/insulin name or an "hba1c" test name → tags "Type 2 Diabetes Mellitus"; any Lisinopril/Amlodipine/Losartan → tags "Essential Hypertension"), not real clinical reasoning. A patient on Lisinopril for a non-hypertension reason would be mistagged.
- **File-upload validation is extension-only.** A file containing PE-executable magic bytes (`MZ\x90...`) with a `.txt` extension was **accepted** (HTTP 201) — there is no content/magic-byte sniffing, only `value.name.split(".")[-1]` against a whitelist. Not remotely executable server-side (Django never executes stored files, and the storage path is randomized), but it is a real gap against the audit's "renamed executable" test.
- **CORS is a hand-rolled wildcard.** The new `apps/core/middleware.py` sets `Access-Control-Allow-Origin: *` and `Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With` on every response, unconditionally. Because auth is Bearer-token (not cookies) the practical blast radius is smaller than a cookie-based wildcard, but it is not an allow-list and should not ship as-is.

## 3. What Is Missing

- No embeddings, no vector database, no external LLM/API client anywhere in the repo. Confirmed by dependency inventory: `backend/requirements.txt` and `ai-engine/requirements.txt` contain **no** `pytesseract`, `Pillow`, `pdf2image`, `PyPDF2`/`pdfplumber`, `sentence-transformers`, `faiss`, `chromadb`, `openai`, `anthropic`, or `langchain`. This is a hard architectural fact, not an opinion.
- **No actual OCR/Vision on images** — see §5. `extract_text_from_file()` (`ocr.py:83`) has exactly one non-plain-text branch: a regex-based PDF text-stream scraper for machine-generated PDFs. There is no image decoding path of any kind.
- **No consent step, no scoping, no expiry on the access a QR grant produces.** Once any doctor scans a patient's QR, there is no record of *which* Clinical Brief fields they saw, no re-authorization requirement, and (see §5) no time limit on the resulting document access.
- **No migration for the `extraction_status="completed"` value.** `views.py:97` sets `ExtractionStatus.COMPLETED`, but `documents/migrations/0001_initial.py` was generated before that choice was added — a fresh `makemigrations --check` fails (reproduced live). Harmless today only because Django doesn't enforce `choices` at the DB layer.

## 4. RAG Verification — the actual chain, with evidence

| Stage | Real or not | Evidence |
|---|---|---|
| Document stored | Real | `MedicalDocument` model + `FileField`, `backend/apps/documents/models.py:64` |
| Associated with patient | Real, server-set | `perform_create` resolves `patient` from the authenticated user or an explicit doctor-owned FK — never client-trusted (`views.py:58-71`) |
| "OCR"/text extraction | Real for text; **absent for images** | `ocr.py:83-108`; live PNG test produced 0 findings (§5) |
| Chunking | Real, naive | `chunk_document_text()`, word-count windows of 150 with 30 overlap, `rag.py:18` |
| Embedding | **Not real** | No embedding model. `_compute_vector` is a raw per-request term-frequency vector over a vocabulary built from that single query's candidate chunks (`rag.py:40-50`) |
| Vector index | **Not real / not persistent** | Nothing is stored between requests; the "index" is rebuilt from the DB every call. Multi-worker deployment is safe (no shared mutable state) precisely because there is no index to desync, but there is also no performance benefit an index would give, and reindexing/growth-over-time claims are moot — there is nothing to grow. |
| Patient metadata / patient-scoped retrieval | **Real, live-verified** | Hard DB filter before scoring (`rag.py:66-69`); cross-patient leak test failed to leak in live run |
| LLM context / LLM | **Does not exist** | No LLM call anywhere in `clinical_brief.py` or `rag.py`. The "Clinical Brief" is deterministic string templating. |
| Clinical Brief | Real (as a template), not AI-generated | `build_clinical_brief()`, `clinical_brief.py:20-234` |
| Source references | Real | Every RAG chunk carries `document_id`, `view_url`, `citation_tag` (`rag.py:113-117`); every lab point and trend carries source document IDs/URLs |

**Conclusion**: the patient-isolation boundary in RAG is real and correctly server-side/pre-ranking. Everything else the word "RAG" usually implies (embeddings, vector index, LLM-grounded generation) is absent — this is keyword search with a citation format, not retrieval-augmented generation.

## 5. OCR/Vision Verification — direct evidence

Live test: uploaded a genuine, minimally-valid PNG file (`image/png` content-type, real PNG magic bytes/IHDR/IDAT/IEND structure) as a `LAB_REPORT`.

- Upload succeeded (HTTP 201), `processing_status: "processed"`.
- `extracted_data.clinical_findings` = **`[]`** — zero findings.
- Why: `extract_text_from_file()` only branches on UTF-8-decodability and a `%PDF` signature check; for a PNG it falls through to `content.decode("utf-8", errors="ignore")`, which turns binary pixel/compression data into meaningless characters, so no regex in `KNOWN_LAB_PATTERNS`/`KNOWN_DRUGS` matches. There is no image library imported anywhere in the file (verified: no `PIL`, `cv2`, `pytesseract`, or any binary-image handling).

**By contrast**, plain-text and machine-generated-PDF-style content genuinely extracts real values dynamically (HbA1c 7.9 → 7.9, then 8.2 → 8.2, Metformin → Metformin) — this part is not mocked. But the claim "OCR/Vision implemented" is **false as a general claim** and **true only for already-machine-readable text**, which is the one input type where OCR isn't actually needed.

## 6. Clinical Brief Verification

Live-run against real data (Patient X, HbA1c 7.9% in April → 8.2% in September, Metformin 500 mg via verified prescription):

- `active_medications` sourced **only** from `Medication.objects.filter(patient=patient, is_active=True)` — the authoritative DB table, never from RAG/document text (`clinical_brief.py:28`). Verified structurally: a document mentioning a different dosage cannot overwrite this list; RAG excerpts are surfaced separately under `rag_evidence_excerpts` and never merged into `active_medications`. **Structured-vs-document conflict resolution is safe by construction** — the code has no path to let extracted document text silently replace or alter a DB medication record.
- Temporal trend correctly computed and source-cited: `"HbA1c (Glycated Hemoglobin) increased from 7.9% to 8.2% across historical records"`, live-reproduced word-for-word, with both source documents attached in `sources`.
- Trend direction is **not hard-coded to "increased."** The logic (`clinical_brief.py:119-133`) computes `diff = latest - first` and picks `increased`/`decreased`/`remained stable` accordingly — a decreasing or mixed series would produce a different label. (Not independently live-tested with a decreasing series in this pass — reasoned from code, which is unconditional on direction.)
- Hallucination risk: **low, by architecture**, because there is no generative model — `ai_observations` and `narrative` are template strings built only from data actually present (`if trends: ...`, `if active_meds: ...`). A patient with no diabetes-related medication or lab name will never get "Type 2 Diabetes Mellitus" injected — but see §2 for the shallow-keyword caveat (mis-tagging risk, not fabrication risk).
- Source grounding: every lab point, every trend, and every source document carries a `view_url`/`document_id`/citation. No claim in the brief lacks a traceable source, because the brief cannot express anything the underlying query didn't already produce.

## 7. Security Verification

### 7a. Patient isolation (RAG) — **HOLDS**, live-adversarially tested
Cross-patient keyword-collision query returned zero leaked content (§4). This is the one component that performed exactly as claimed.

### 7b. IDOR / document access — **HOLDS for the roles it's supposed to hold for**
Live-tested with real tokens: receptionist → `403` on document stream; lab tech → `403` on document stream and on document list (list returns empty via queryset scoping, `views.py:47-48`); unauthenticated → `401`. Doctor-owned-patient scoping on list/detail views is correctly implemented via `patient__doctor=user` / `patient__user=user` querysets.

### 7c. QR security — **P0 FAIL, live-confirmed**
`git diff backend/apps/qr/views.py` shows the previous authorization check was deleted:
```diff
-        if patient.doctor_id != request.user.id:
-            QRScanLog.objects.create(..., success=False, failure_reason="Doctor is not assigned to this patient.")
-            return Response(..., status=403)
-
         QRScanLog.objects.create(patient=patient, scanned_by=request.user, success=True)
```
Live reproduction: registered a brand-new doctor account with zero prior relationship to "Patient A," had it POST to `/api/qr/verify/` with Patient A's freshly-generated QR token → **HTTP 200**, response included Patient A's full `PatientSerializer` payload (which includes the `medical_notes` field, `backend/apps/patients/serializers.py:16`) plus the entire Clinical Brief. The regression test that used to catch this, `test_unassigned_doctor_forbidden`, was renamed to `test_unassigned_doctor_can_verify_valid_qr` and its assertion flipped from `403` to `200` (`git diff backend/apps/qr/tests/test_qr.py`) — the test suite was edited to certify the vulnerability as intended behavior rather than catching a regression.

**Worse — the resulting access has no expiry.** `DocumentStreamView.get()` (`views.py:146`) grants file access to any doctor for whom `QRScanLog.objects.filter(patient=patient, scanned_by=user).exists()` is true — no `success=True` filter, no time bound. Live reproduction: the same unrelated doctor, after that single QR scan, successfully streamed Patient A's original uploaded lab document (`HTTP 200`) via `GET /api/documents/<id>/view/`. Because `QRScanLog` rows are permanent audit records, this grant does not expire when the 15-minute QR token expires — it is **de facto permanent, unscoped document access** for any doctor who ever scans that patient's QR once.

### 7d. Broken-access-control failure mode — **P1 FAIL, live-confirmed**
`DocumentRAGSearchView` (`views.py:250-260`) attempts a "24-hour QR-scoped fallback" for doctors not directly assigned:
```python
QRScanLog.objects.filter(doctor=user, patient=patient, status="verified", scanned_at__gte=...)
```
But `QRScanLog` (`apps/qr/models.py`) has fields `patient`, `scanned_by`, `success`, `failure_reason`, `created_at`, `updated_at` — **no `doctor`, `status`, or `scanned_at` field exists.** Live reproduction: an unrelated, non-QR-verified doctor querying RAG search for a patient it has no access to gets **HTTP 500 (`FieldError`)**, not `403`. Combined with `docker-compose.yml`'s `DJANGO_DEBUG: ${DJANGO_DEBUG:-True}` default for the `backend` service (even though `config/settings/prod.py` would otherwise default `DEBUG=False`), an unhandled 500 in this deployment profile serves Django's full debug page — stack trace, file paths, and a dump of Django settings — to the attacker. This does not leak the specific patient's data (the request never reaches the data layer), but it is an availability/information-disclosure defect and it means the intended authorization fallback has never actually run successfully in any test — including `verify_e2e_live.py`, which never calls this endpoint as an unassigned, non-primary doctor (see §9).

### 7e. Prompt-injection defense — **superficial, verified by code path**
`sanitize_document_text()` (`ocr.py:74`) redacts injection-marker phrases, but only inside `extract_document_entities()`'s **local** `cleaned_text` variable used for regex matching. The persisted `doc.extracted_text` field (`views.py:90`, `doc.extracted_text = raw_text`) stores the **raw, un-sanitized** text, and `retrieve_patient_context()` chunks `doc.extracted_text` directly (`rag.py:77`) — so any RAG excerpt or future LLM context would receive the original injection payload unredacted. This is currently low-impact only because nothing in the codebase treats extracted text as instructions (no LLM exists to be manipulated) — but the "sanitization" provides no real defense-in-depth if an LLM is later wired to consume RAG excerpts or `extracted_text`, which is exactly the stated Phase-2+ direction.

### 7f. File upload — mixed
15 MB cap: enforced (live-tested at 16 MB → rejected). Extension allow-list: enforced (`.exe` rejected). Content/magic-byte validation: **absent** (executable bytes disguised as `.txt` accepted, live-tested). Path traversal: neutralized by design (randomized storage filename, `models.py:9-14`) — the "malicious filename" test passing with `201` is not itself a vulnerability once you check where the bytes actually land.

### 7g. Secrets — clean
`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, and email credentials are all environment-variable-driven (`config/settings/base.py`, `.env`), not hardcoded in source. No `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`/similar found anywhere (consistent with §3 — there is no LLM client to hold one). `backend/protected_documents/` (where uploaded documents physically live) is **not listed in `.gitignore`**, unlike `db.sqlite3`/`staticfiles`/`venv` — a real, easily-fixed data-hygiene gap: uploaded patient documents currently have no repository-level protection against being accidentally `git add -A`'d.

## 8. End-to-End Verification (live-run)

`verify_e2e_live.py` was executed against freshly-started, from-scratch Django + FastAPI servers in this sandbox (not assumed from the report) and printed **"ALL 37 MASTER LIVE VERIFICATION & SECURITY CHECKS PASSED WITH 100% SUCCESS"** — independently reproduced, not fabricated. `Patient.id` continuity was independently confirmed: the same `patient_x_id` is referenced by the invitation, both appointments, the lab request/result, the check-in, all three uploaded documents, and the QR scan log, with no duplicate `Patient` row created on the second receptionist search.

However, of the 37 steps, **steps 27–30 (the "multi-doctor QR access" section) assert the vulnerability in §7c as a passing feature**, not a security control — the script proves Doctor B *can* get Patient X's data via QR, and stops there; it never asserts that an unrelated doctor *should* be denied. The script also never once calls `DocumentRAGSearchView` as a non-primary, non-QR-verified doctor, so it never exercises the crash in §7d.

## 9. Test Quality

- **Real, non-mocked, meaningful assertions**: the 303 AI-Engine tests are pure deterministic unit tests with real boundary-condition assertions (score clamping, band boundaries, monotonic-trend detection) — high quality, not superficial `status_code == 200` checks.
- **A real regression test was repurposed to hide a regression**: `test_unassigned_doctor_forbidden` → `test_unassigned_doctor_can_verify_valid_qr` (§7c). This is the single most important test-quality finding in this audit: the test suite passing 115/115 is true, but it no longer encodes the security invariant it used to.
- **`verify_e2e_live.py` is a real, live HTTP integration script** (uses `requests` against real running servers, not Django's in-memory `TestClient`) — this is a stronger test than a typical mocked E2E test, but its security assertions are incomplete in exactly the way that matters (§8).
- **Frontend build: NOT VERIFIED** in this sandbox — `npm run build` failed on a `@rollup/rollup-linux-arm64-gnu` native-binding resolution error, a known npm optional-dependency platform issue (the `node_modules` were installed on an ARM Mac; this sandbox is a different Linux environment) unrelated to application code. This is an environment artifact, not evidence the frontend is broken, but it also means the "frontend build passed" claim could not be independently reproduced here.

## 10. Issues

| # | Severity | File / Function | Problem | Evidence | Recommended fix |
|---|---|---|---|---|---|
| 1 | **P0** | `apps/qr/views.py::QRVerifyView.post` | Doctor-assignment check removed; any authenticated doctor can verify any patient's QR and receive full profile + Clinical Brief | Live: unrelated fresh doctor got `200` + `medical_notes` field | Restore an authorization gate — e.g., require the *patient* to explicitly authorize the scanning doctor (a consent/accept step), or reintroduce assignment-or-explicit-grant, before returning clinical data |
| 2 | **P0** | `apps/documents/views.py::DocumentStreamView.get` | QR-derived document access has no expiry/scope — permanent after one scan | Live: doctor streamed original document long after the QR-verify call, via a permanent `QRScanLog` row with no time filter | Scope document access to a time-bounded, revocable grant record, not a permanent audit-log existence check |
| 3 | **P1** | `apps/documents/views.py::DocumentRAGSearchView.get` | Unauthorized RAG request crashes with `FieldError`/HTTP 500 instead of `403`; queries `QRScanLog.doctor/status/scanned_at`, none of which exist on the model | Live: unrelated doctor's RAG query returned `500` with a Django debug traceback | Fix the field names to match `QRScanLog` (`scanned_by`, `success`, `created_at`), add a test for this exact path, fail closed |
| 4 | **P1** | `docker-compose.yml` (backend service) | `DJANGO_DEBUG` defaults to `True` even when `DJANGO_SETTINGS_MODULE` defaults to `config.settings.prod`, so an unhandled 500 (like #3) leaks stack traces/settings | `docker-compose.yml`: `DJANGO_DEBUG: ${DJANGO_DEBUG:-True}` | Default to `False`; require an explicit opt-in for debug mode |
| 5 | **P1** | `apps/qr/tests/test_qr.py` | The regression test for #1 was edited to assert the vulnerable behavior is correct, instead of being flagged as a broken test | `git diff`: `test_unassigned_doctor_forbidden` → `test_unassigned_doctor_can_verify_valid_qr`, assertion `403`→`200` | Restore a real assignment/consent-based assertion once #1 is fixed |
| 6 | **P1** | `apps/documents/ocr.py` | No OCR/Vision exists for images; "OCR/Vision" claim is false for the exact use case (scanned prescriptions/labs) it's meant for | Live: real PNG upload → 0 findings | Either integrate real OCR (e.g., an actual image-to-text step) or relabel the feature as "text-document parsing," not OCR/Vision |
| 7 | **P2** | `apps/documents/rag.py` | "RAG"/"vector index" is per-request TF cosine similarity, not embeddings/vector DB; will not semantically match paraphrased queries | Code inspection, no embedding library in `requirements.txt` | Fine for a hackathon demo; relabel externally, or add a real embedding step before calling this "RAG" |
| 8 | **P2** | `apps/documents/ocr.py` (sanitize path) | Prompt-injection sanitization only affects internal regex matching, not the persisted/retrieved text | `views.py:90` stores raw `extracted_text`; `rag.py:77` chunks raw `extracted_text` | Sanitize (or clearly mark) the persisted/retrieved text itself, not just the ephemeral parsing copy, before any future LLM consumes it |
| 9 | **P2** | `apps/documents/serializers.py::MedicalDocumentUploadSerializer.validate_file` | Extension allow-list only, no content/magic-byte check | Live: executable bytes accepted under a `.txt` name | Add a magic-byte/MIME sniff (e.g. check real file signature) in addition to extension |
| 10 | **P2** | `.gitignore` | `backend/protected_documents/` (uploaded patient files) is not gitignored | `git ls-files`/`.gitignore` inspection | Add `protected_documents/` (and any media root) to `.gitignore` |
| 11 | **P2** | `apps/documents/migrations/` | Migration 0001 is out of sync with `models.py` (`extraction_status` "completed" choice missing) | Live `makemigrations --check` reproduces a pending migration | Run `makemigrations` and commit the resulting migration |
| 12 | **P3** | `apps/core/middleware.py::SimpleCorsMiddleware` | Wildcard `Access-Control-Allow-Origin: *` on every response | Code inspection | Replace with an explicit origin allow-list before any non-local deployment |
| 13 | **P3** | `apps/patients/clinical_brief.py` | Condition inference is a shallow drug/test-name keyword match, can mis-tag conditions | Code inspection (`clinical_brief.py:179-186`) | Fine for a hackathon narrative; label as heuristic, not diagnosis, if shown to real clinicians |

## 11. Demo Readiness

The **hackathon demo as scripted in `verify_e2e_live.py` can genuinely be performed live** — every step in that script is real, live-executed, non-mocked behavior (receptionist → patient creation → lab order → check-in → AI scoring → document upload → OCR text extraction → prescription verification → RAG retrieval → Clinical Brief with a real HbA1c trend → QR scan → document streaming). That is a legitimately impressive amount of working, wired-together functionality for a hackathon MVP.

What should **not** be claimed in the demo without a caveat: "OCR/Vision" (it doesn't process images), "RAG" in the vector/embedding sense, and "AI-generated" for the Clinical Brief (it's a template, which is actually a selling point for factual grounding — frame it that way rather than as generative AI). And the multi-doctor QR flow should be demoed carefully, or fixed first — as scripted, it demonstrates the exact vulnerability in §7c to anyone who thinks about it for 30 seconds ("wait, why did a doctor who was never assigned to this patient just get their whole chart?").

## 12. Recommended Remediation Plan

**P0 (before anyone else touches this branch):**
1. Restore an authorization boundary in `QRVerifyView` — at minimum, reinstate assignment-or-explicit-consent; do not ship "any doctor + a QR image = full chart access."
2. Time-bound and scope the access that a QR grant produces in `DocumentStreamView` — do not key permanent file access off a permanent audit-log row.

**P1 (before a demo to anyone outside the team, or before merge):**
3. Fix `DocumentRAGSearchView`'s QR-fallback query to reference real `QRScanLog` fields, and add a test that actually exercises an unassigned-non-QR doctor hitting this endpoint (it currently isn't tested at all).
4. Default `DJANGO_DEBUG` to `False` in `docker-compose.yml`.
5. Restore (don't delete) the security-invariant test for #1, once #1 is fixed.
6. Decide honestly whether to build real OCR or relabel the feature; don't let "OCR/Vision implemented" stand unqualified.

**P2 (before production, not before a hackathon demo):**
7. Add magic-byte file validation; gitignore `protected_documents/`; commit the missing migration; consider whether "RAG" needs real embeddings for your actual use case or whether keyword search is genuinely sufficient and should just be named accurately.

**P3:** replace wildcard CORS with an allow-list; label the condition-inference heuristic as such if it will ever be shown to a real clinician.

---

*This audit modified no source code. All servers were started, all test suites were run, and all adversarial scripts were executed against live, freshly-installed instances of this codebase in an isolated sandbox — not assumed from documentation or prior reports.*
