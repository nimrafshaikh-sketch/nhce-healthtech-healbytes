# HealBytes Multi-Agent Clinical Intelligence — Audit & Architecture Plan

**No code was changed to produce this document.** It's a read-only audit (git status, file reads, existing test/audit reports already in the repo) plus a plan, per the request. Sources: direct repository inspection (`git log`, `ai-engine/`, `backend/apps/documents/`, `backend/apps/qr/`) and the two audit docs already committed at repo root — `HealBytes_Independent_Verification_Report.md` (live-adversarial security audit) and `HealBytes_Phase1_Security_Remediation.md` (fixes + Phase 2A OCR addendum). Where this plan relies on those reports rather than a fresh read of the underlying code, it says so.

---

## 0. The headline finding

This is not a from-scratch build. The repo already implements most of what the request calls for — across two teams, over several merged branches (`feature/ai-engine`, `feature/ai-history`, `feature/m3-database`, `feature/backend`, `feature/frontend-implementation`). Specifically:

- **Agents 1–6** (Risk, Trend, Medication Adherence, Follow-up, Clinical Explanation, Longitudinal History) are fully implemented in `ai-engine/`, deterministic, with 303 passing tests.
- **Document Foundation (P1)**, **Document Intelligence / OCR (P2)**, and a **patient-scoped retrieval layer (P3-lite)** are implemented in `backend/apps/documents/`, with a live-run security audit and a remediation pass already on record.
- The backend team's own remediation doc explicitly says LLM-based Clinical Brief synthesis is **"still blocked by this project's 'no LLM at this stage' rule"** — the same rule this project's instructions place on the AI Engine. That rule is being actively honored by both sides of the codebase right now, not just a stale setting.

So the real gap between what exists and what the request asks for is narrower than it looks, and it is concentrated in exactly two places: **real semantic retrieval (embeddings/vector DB)** and **LLM synthesis + grounding** — both explicitly out of scope under current project rules, and both living in the backend `documents`/`patients` apps, not the AI Engine.

---

## 1. Capability matrix

| Capability | Status | Where | Reuse | Required changes |
|---|---|---|---|---|
| Frontend (React/Vite) | Existing | `src/` | Yes | Out of scope for me (project rule); not independently audited here |
| Django backend / RBAC / auth | Existing, security-audited | `backend/apps/accounts`, `apps/core` | Yes | Out of scope for me (project rule) |
| Database (SQLite dev / Postgres prod) | Existing | `database/schema.sql`, Django models | Yes | Out of scope for me (project rule) |
| Daily check-ins | Existing | `backend/apps/checkins` | Yes | None |
| **Risk Analysis** | **Existing, complete** | `ai-engine/app/analysis/risk_engine.py` + `risk_assessor.py` | Yes | None — deterministic, 100-point scale, Low/Medium/High bands |
| **Historical Trend Analysis** | **Existing, complete** | `ai-engine/app/analysis/trend_detector.py` | Yes | None — bounded ±4/±8 adjustment, evidence-gated |
| **Medication Adherence Analysis** | **Existing, complete** (two independent implementations) | `ai-engine/app/analysis/medication_adherence.py` (consumes known status) + `ai-engine/app/history/summary_service.py` (computes status from reminder logs) | Yes | None |
| **Follow-up Recommendation** | **Existing, complete** | `ai-engine/app/analysis/follow_up_recommender.py` | Yes | None — pure mapping from final risk level |
| **Clinical Explanation** | **Existing, complete** | `ai-engine/app/analysis/explanation_service.py` | Yes | None — deterministic fallback + pluggable (currently unused) provider hook, strict contradiction/forbidden-content checks |
| **Longitudinal History Summary** | **Existing, complete** | `ai-engine/app/history/summary_service.py`, `/api/v1/history/summary` | Yes | None |
| Document upload / storage / metadata (P1) | **Existing** | `backend/apps/documents/models.py` (`MedicalDocument`), `views.py` | Yes | Two known gaps: persisted `extracted_text` is unsanitized for future LLM consumption (§7e of the verification report); upload validation is extension-only, no magic-byte check (item 9) |
| OCR / text extraction (P2) | **Partial** | `backend/apps/documents/ocr.py` | Yes | Real Tesseract OCR for images (added in Phase 2A) + regex entity extraction against a **fixed dictionary** of known lab tests/drugs. Anything outside that dictionary isn't recognized — not a trained NER/vision model |
| Embeddings | **Missing** | — | — | No embedding model or library anywhere in either `requirements.txt` |
| Vector store / semantic RAG | **Missing** (a keyword-search stand-in exists) | `backend/apps/documents/rag.py` | Partial | What exists is a **per-request TF/cosine keyword search**, correctly patient-isolated, not embeddings-based RAG. Won't match paraphrases ("diabetes" vs. "elevated glycemic markers") |
| LLM integration | **Missing — by design** | — | — | Explicitly forbidden right now, both by this project's rules and by the backend team's own stated Phase 2B/2C plan |
| Clinical Brief (synthesis) | **Existing, but template not LLM** | `backend/apps/patients/clinical_brief.py` | Yes | 100% deterministic string templating over ORM data — good for grounding, mislabeled if called "AI-generated." One heuristic risk: condition tagging is a shallow drug/test-name keyword match (item 13) |
| Medication Intelligence (reconciliation, duplicates, conflicts) | **Missing** | — | — | Not implemented anywhere. `active_medications` in the Clinical Brief comes straight from the `Medication` table with no cross-check against document-derived candidates |
| Lab Intelligence (longitudinal, multi-test) | **Partial** | `clinical_brief.py` trend calc | Partial | Trend logic exists but is built into the brief template for the tests it already knows about; not a general, reusable service |
| Patient Timeline | **Missing as a feature** | Data exists, no unified view | Partial | Every model carries `patient_id`/timestamps; no endpoint assembles them into one chronological view |
| Clinical Safety / Grounding Agent | **Missing** | — | — | Currently low-stakes because there's no LLM output to verify. Becomes mandatory the moment LLM synthesis is introduced |
| QR / consult-based access | **Existing, security-remediated** | `backend/apps/qr/`, `QRAccessGrant` | Yes | P0 vulnerability (unbounded access after any QR scan) found and fixed; verified live |
| Security controls (patient isolation, IDOR, CORS, RBAC) | **Existing, live-verified** | across `apps/documents`, `apps/qr`, `apps/core/middleware.py` | Yes | Two P2 items still open (magic-byte validation, persisted-text sanitization) |
| Tests | **Existing, substantial** | 135/135 Django, 303/303 AI-Engine, 18 dedicated document-security tests | Yes | None required to reach current claims; more needed for any new feature |
| Live E2E | **Existing, real** | `backend/verify_e2e_live.py`, 37/37 steps, live HTTP against real running servers | Yes | Would need new steps for any new agent (Medication Intelligence, Timeline, etc.) |

---

## 2. Why I'm not implementing this as written

Two independent constraints intersect on almost every "new agent" in the request:

**A. Module ownership.** This project's instructions restrict me to `ai-engine/` only — no frontend, no Django backend, no database, no auth, no other team-member modules. But Document Intelligence, RAG, Clinical Brief, Medication Intelligence, Lab Intelligence, Patient Timeline, and the Safety/Grounding agent all live (or would need to live) in `backend/apps/documents/` and `backend/apps/patients/` — Django territory, already owned and actively worked by another teammate (the branch history shows a separate contributor driving `feature/ai-history`, with its own independent security audit and remediation cycle).

**B. The no-LLM rule.** Clinical Brief synthesis-with-citations, Medication Intelligence's "reconcile and flag conflicts," and the Safety/Grounding Agent as specified all assume an LLM in the loop. This project's instructions say no LLM at this stage. The backend team's own remediation report independently states the same restriction blocks their Phase 2C. This isn't a stale rule I'd be right to route around — it's a live, cross-team constraint both sides are currently honoring.

What's left after removing (A) and (B) is: nothing new for the AI Engine to build right now. The AI Engine module itself is feature-complete for what it was scoped to do (Phases 0–5 + history summary), and everything the mega-prompt asks for beyond that is either someone else's module, blocked by the LLM rule, or both.

---

## 3. What's actually still open (independent of the ai-engine/no-LLM question)

Carried forward from the existing audit reports, still unresolved as of the latest commit:

| # | Item | Severity | Note |
|---|---|---|---|
| 1 | Persisted `extracted_text` is unsanitized | P2 | Sanitization only runs on an ephemeral local copy used for regex matching; the stored/retrieved text a future LLM would consume is raw. Low-impact today (nothing consumes it as instructions yet) but should be fixed *before* any LLM is wired up, not after |
| 2 | Upload validation is extension-only | P2 | No magic-byte/content sniffing; an executable renamed `.txt` is accepted (though not executable server-side — storage paths are randomized and Django never executes stored files) |
| 3 | Condition-inference is a shallow keyword heuristic | P3 | Any Metformin/Glipizide/insulin or "hba1c" → tagged "Type 2 Diabetes Mellitus" regardless of actual reason for the medication. Fine as a hackathon narrative, mislabeled if shown to a real clinician |
| 4 | "RAG" is TF-cosine keyword search, not embeddings | P2 | Real and patient-isolated, but will not generalize semantically. Should be relabeled if presented externally as vector/embedding RAG |

None of these require an LLM to fix, and none of them are in `ai-engine/` — they're backend items for whoever owns `apps/documents`.

---

## 4. If/when the scope is broadened — target architecture

This section is the "what it would look like" answer, held for a decision, not a commitment to build:

```
Doctor opens Patient Profile
  → Clinical Brief Orchestrator (new, backend)
      → structured history (existing: medications, labs, appointments, check-ins — reuse as-is)
      → Clinical Retrieval (existing rag.py, upgraded to real embeddings — new work)
      → Document Intelligence data (existing ocr.py — reuse, extend entity dictionary or replace with model-based extraction)
      → Medication Intelligence (new: reconcile Medication table vs. document-derived candidates)
      → Lab Intelligence (new: generalize the trend logic already in clinical_brief.py into a reusable service)
      → Clinical Brief generation (existing template retained as the deterministic fallback; LLM synthesis only if the no-LLM rule is lifted)
      → Safety/Grounding Agent (new, mandatory the moment LLM synthesis exists — verify every claim traces to a source, reject unsupported claims)
      → Doctor UI
```

Key design point carried over from what already exists and works: **patient_id filtering happens before ranking/scoring, at the database query level, never after.** `rag.py` already does this correctly and it's live-adversarially verified — any new retrieval code should copy that pattern exactly, not reinvent it.

Medication Intelligence and Lab Intelligence, notably, **do not strictly require an LLM** — they're pattern-matching / reconciliation logic (duplicate detection, date-range overlap, conflicting dosage strings) that could be built the same deterministic way as everything else in `ai-engine/`. If there's appetite to make progress without touching the LLM question, those two are the highest-value, lowest-risk additions — but they'd still need to live in the Django backend (they operate on `Medication`/`LabTestResult`/document models directly), so still outside my current module boundary.

---

## 5. Files (for whichever team member owns this work)

**Reusable as-is:** every `ai-engine/app/analysis/*` and `ai-engine/app/history/*` module; `backend/apps/documents/models.py` (MedicalDocument already has the full metadata/provenance shape the request asks for — document_type, processing_status, extraction_status, extracted_data, verified_by/verified_at); `QRAccessGrant` for bounded consult access; `clinical_brief.py`'s deterministic template as the safe fallback path.

**Would need modification:** `apps/documents/rag.py` (swap TF-cosine for real embeddings, *if* semantic retrieval is actually needed for the demo); `apps/documents/ocr.py` (extend `KNOWN_LAB_PATTERNS`/`KNOWN_DRUGS` or replace with a trained extractor); `apps/documents/serializers.py` (add magic-byte validation); `apps/documents/views.py`/`rag.py` (sanitize persisted `extracted_text`, not just the ephemeral copy); `clinical_brief.py` (only if LLM synthesis is approved — keep the current template as the fallback, never remove it).

**New files, only if scope is broadened:** a Medication Intelligence service (deterministic reconciliation), a Lab Intelligence service (generalized trend/abnormal-value detection), a Patient Timeline endpoint (aggregation query over existing models — no new tables needed), and — only if the LLM rule is lifted — a Safety/Grounding verifier module.

**New files in `ai-engine/`:** none identified. The module is complete for its current scope.

---

## 6. Dependencies, database, and test/E2E strategy — contingent

Dependencies (`sentence-transformers` or similar embedding lib, a vector index, an LLM SDK) would only be needed if the no-LLM/embeddings restriction is lifted — not recommended to add now. No new database tables are needed for anything except a real vector index (a chunk/embedding table) — the `MedicalDocument` schema already covers document metadata and provenance. Test/E2E strategy for any future addition should follow the pattern already established here, which is unusually rigorous for a hackathon project: live-started servers (not mocks), an adversarial cross-patient isolation test for every new patient-scoped endpoint (mirroring `test_documents_security.py`'s 18 tests), and an extension of `verify_e2e_live.py` covering the new step end-to-end.

---

## 7. Recommendation

Two decisions are needed before any code gets written, and neither is mine to make unilaterally:

1. **Update this project's saved instructions** to reflect that the AI Engine foundation is done (Phases 0–5 + history, 303 tests) — the current instructions describe a "from scratch" starting point that no longer matches the repo, so it's worth deciding what the AI Engine's *next* task actually is, if any.
2. **Coordinate with whoever owns `backend/apps/documents`/`apps/patients`** (this looks like a separate teammate's active work, with its own audit trail) before touching Medication Intelligence, Lab Intelligence, Patient Timeline, or the LLM/embeddings question — building any of those from the AI Engine side would mean working outside this project's module boundary and, for the LLM pieces, against a rule both teams are currently honoring.

If the answer to (2) is "yes, broaden scope," the lowest-risk next increment is Medication Intelligence + Lab Intelligence as deterministic services (no LLM needed, consistent with everything already built) — not the full RAG/LLM/Safety-Agent stack, which is the highest-risk, most rule-conflicting part of the request.
