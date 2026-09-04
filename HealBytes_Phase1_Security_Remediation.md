# HealBytes Phase 1 — Security Remediation Report

Fixes applied for every P0/P1 finding in `HealBytes_Independent_Verification_Report.md`, §10, items 1–5. Nothing outside Django backend security/config was touched (no OCR, embeddings, or LLM work — that's Phase 2+, not started).

## What changed

**New: `apps/qr/models.py::QRAccessGrant`** — a bounded-duration authorization grant (`patient`, `doctor`, `expires_at`, `purpose`, `created_at`). This is now the only thing that authorizes a non-assigned doctor's access to a patient's documents/RAG. It never touches `patient.doctor_id`. Migration: `apps/qr/migrations/0003_qraccessgrant.py`.

**`apps/qr/views.py::QRVerifyView`** — the assigned doctor still gets full access with no grant needed. A doctor who is *not* assigned now still succeeds on a valid, signed, non-expired QR (this is the intended "patient shows QR to a new doctor" consult flow — the audit's problem was never that this should be impossible, it was that it produced *unbounded* access). What's different: verifying now calls `QRAccessGrant.grant(patient, doctor)`, creating a grant that expires after `QR_ACCESS_GRANT_HOURS` (default 24h, env-configurable) — not a permanent audit-log row.

**`apps/documents/views.py`** — `DocumentStreamView` and `DocumentRAGSearchView` now check `QRAccessGrant.has_active_grant(patient, doctor)` instead of (respectively) an unbounded `QRScanLog.exists()` and a query against fields (`doctor`, `status`, `scanned_at`) that don't exist on `QRScanLog` — the latter was the exact cause of the live-reproduced `500 FieldError` on unauthorized RAG requests. Both now fail closed with `403`.

**`docker-compose.yml`** — `DJANGO_DEBUG` for the `backend` service now defaults to `False` (was `True`, even under the `prod` settings module). Added `CORS_ALLOWED_ORIGINS` and `QR_ACCESS_GRANT_HOURS` passthrough.

**`apps/core/middleware.py::SimpleCorsMiddleware`** — replaced the wildcard `Access-Control-Allow-Origin: *` with an explicit, env-configurable allow-list (default: the local Vite dev origins only). Origin is checked and echoed back only on a match, with `Vary: Origin`.

**Data hygiene** — `backend/.gitignore` now excludes `protected_documents/` (uploaded patient files were previously unprotected against `git add -A`). Ran `makemigrations` for real, which also closed the pre-existing `documents` migration drift (`extraction_status` "completed" choice) found in the original audit.

**Tests** — `apps/qr/tests/test_qr.py`: the flipped regression test (`test_unassigned_doctor_forbidden` → `test_unassigned_doctor_can_verify_valid_qr`) is now `test_unassigned_doctor_with_valid_qr_gets_a_bounded_grant_not_permanent_access`, which asserts a real invariant again (a grant is created, it's active, it expires on schedule, and `patient.doctor_id` is untouched) instead of just asserting `200`. Added `test_expired_grant_no_longer_authorizes_document_or_rag_access`. New file `apps/documents/tests/test_documents_security.py` (18 tests): assigned-doctor access, unassigned-without-grant → 403, unassigned-with-grant → 200, expired-grant → 403, grant-for-patient-A-doesn't-leak-to-patient-B, receptionist/lab-tech/unauthenticated → 403, patient-to-patient IDOR, document-list queryset scoping, RAG cross-patient isolation, and — the specific regression test for the crash — unauthorized RAG search returns `403`, not `500`.

## Verification (all live, this session)

- **Django suite: 134/134 pass** (115 original + 19 new), run from a clean venv.
- **AI-Engine suite: 303/303 pass**, unaffected (nothing there was touched).
- **`verify_e2e_live.py`: all 37 steps still pass** against fresh, live-started servers — the existing workflow (receptionist → patient → appointment → lab → check-in → AI → documents → OCR-text-extraction → prescription verification → RAG → Clinical Brief → second visit → QR) is unbroken.
- **Fix-specific live re-verification, 7/7 pass:**
  - Unrelated doctor, no QR scan ever → document stream `403` ✅ (was previously reachable via any prior scan with no expiry)
  - Unrelated doctor, no grant → RAG search `403` ✅ (was `500 FieldError`)
  - Unrelated doctor presents valid QR → verify still `200` (intended consult flow, now bounded)
  - ...immediately after, document stream and RAG search now succeed via the fresh grant
  - CORS: an unrecognized `Origin` gets no `Access-Control-Allow-Origin` header at all (no wildcard); `http://localhost:5173` is allowed

## What this does *not* claim to fix

TF-cosine "RAG" isn't embeddings, prompt-injection sanitization on persisted text is still superficial, file validation is still extension-only, and condition-inference is still a shallow keyword match. Unchanged, out of scope for this phase.

---

# Phase 2A — Real Image OCR (time-boxed addendum)

Closes §10 item 6 from the original audit ("No OCR/Vision exists for images — a real PNG upload produced zero findings").

**What changed:** `apps/documents/ocr.py::extract_text_from_file()` now detects real images by magic bytes (PNG/JPEG signatures, not filename/content-type) and runs them through actual Tesseract OCR (`pytesseract` + `Pillow`), with standard preprocessing (grayscale, 2x upscale, autocontrast) that measurably improves accuracy on scanned/photographed documents. Everything downstream (the existing `KNOWN_LAB_PATTERNS`/`KNOWN_DRUGS` regex entity extraction, confidence scoring, `REVIEW_REQUIRED` gating for prescriptions) is unchanged and now simply runs on real OCR output instead of garbage decoded pixel bytes. One small, narrowly-scoped regex addition tolerates a specific, reproducible Tesseract misread of "HbA1c" (observed directly against this project's own OCR output) — it doesn't loosen matching for anything else. Added `pytesseract`/`Pillow` to `requirements.txt` and `tesseract-ocr` to the Dockerfile's apt install.

**Verified live:** uploaded a genuine rendered PNG (drawn text, not a fixture) through the real API — Tesseract actually read the pixels and the pipeline extracted `HbA1c: 8.2%` and `Fasting Blood Glucose: 165 mg/dL` as real structured findings with correct values, units, and reference-range status. New permanent regression test (`apps/documents/tests/test_ocr.py`) asserts this end to end through the same upload endpoint used in production, so this can't silently regress back to zero-findings-on-images. Full suite: **135/135 Django tests pass** (134 + this new one). Full **37/37 `verify_e2e_live.py` steps still pass** — zero regression to the existing workflow.

**Still honest about what this is not:** this is dictionary/regex entity extraction (a fixed list of lab tests and drug names) running on top of real OCR text — not a trained vision/NER model. A lab value or drug name outside `KNOWN_LAB_PATTERNS`/`KNOWN_DRUGS` still won't be recognized. That's a reasonable, demoable next increment, not "AI Engine" work, and not what Phase 2B (real embeddings) or 2C (LLM) would add.

**Not started, by design, given the time-box:** Phase 2B (semantic embeddings/vector retrieval), 2C (LLM Clinical Brief — also still blocked by this project's "no LLM at this stage" rule), 2D (formal RAG evaluation harness).
