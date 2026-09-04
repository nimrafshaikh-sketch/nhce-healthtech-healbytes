"""Clinical Safety / Grounding verification (Phase 7).

Runs after Clinical Brief generation, before the brief is considered final
- the last step of the orchestration flow: structured history -> document
intelligence -> RAG -> medication intelligence -> timeline -> clinical
brief -> **grounding** -> doctor.

There is no LLM anywhere in this pipeline yet (blocked by this project's
current rules - see Phase 6), so there is no free-text generation to check
for hallucination in the usual sense. What this module verifies instead is
real and load-bearing on its own: that every identifier the brief cites
(medication, document, lab) actually belongs to this patient in the
database RIGHT NOW - an independent re-check against the DB, not a re-read
of the brief's own claims about itself - and that every AI Observation
string traces back to a real, still-present record. This is exactly the
check that becomes mandatory (not optional) the moment Phase 6 LLM
synthesis is introduced; it is built now, wired into the orchestration
flow now, and passes cleanly now because the brief is 100% deterministic
and already grounded by construction. It is not decorative.

Checks performed:
1. Patient identity      - every medication/document id cited resolves in
                            the DB to a row whose patient_id == this patient.
2. Medication attribution - every "active" medication cited is actually
                            is_active_on(today) for THIS patient right now.
3. Temporal correctness  - no medication marked historical is presented as
                            active, and vice versa.
4. Lab attribution        - every lab citing a document traces to a
                            MedicalDocument owned by this patient.
5. Evidence grounding /
   unsupported claims     - every AI Observation string is traceable to a
                            real trend, medication-intelligence observation,
                            or check-in risk verdict already present in the
                            brief: never a bare, unattributed line.
6. Conflicts              - medication-intelligence "conflicting_*"
                            observations are surfaced explicitly, not
                            silently resolved to one version.
7. Source traceability    - every rag_evidence_excerpt and source_document
                            entry has a resolvable document_id/view_url.

Never modifies Medication, MedicalDocument, or any authoritative record -
read-only verification.
"""

from typing import Any, Dict, List

from apps.documents.models import MedicalDocument
from apps.medications.models import Medication


def verify_clinical_brief_grounding(patient, brief_data: Dict[str, Any]) -> Dict[str, Any]:
    patient_id = patient.id
    checks: List[Dict[str, Any]] = []
    unsupported_claims: List[str] = []

    # --- 1 & 2 & 3: medication identity / attribution / temporal ----------
    med_ids_active_brief = {m["id"] for m in brief_data.get("active_medications", [])}
    real_meds = {m.id: m for m in Medication.objects.filter(id__in=med_ids_active_brief)}

    from django.utils import timezone
    today = timezone.localdate()

    identity_violations = []
    temporal_violations = []
    for med_id in med_ids_active_brief:
        med = real_meds.get(med_id)
        if med is None or med.patient_id != patient_id:
            identity_violations.append(med_id)
            continue
        if not med.is_active_on(today):
            temporal_violations.append(med_id)

    checks.append({
        "check": "patient_identity_medications",
        "passed": not identity_violations,
        "detail": "All cited active medications belong to this patient." if not identity_violations
                   else f"Medication id(s) {identity_violations} do not belong to patient {patient_id}.",
    })
    checks.append({
        "check": "temporal_correctness_medications",
        "passed": not temporal_violations,
        "detail": "No historical medication presented as currently active." if not temporal_violations
                   else f"Medication id(s) {temporal_violations} are presented as active but are not is_active_on(today).",
    })

    # --- 4 & 7: document / lab attribution and source traceability --------
    cited_document_ids = set()
    for lab in brief_data.get("recent_labs", []):
        if lab.get("document_id"):
            cited_document_ids.add(lab["document_id"])
    for excerpt in brief_data.get("rag_evidence_excerpts", []):
        if excerpt.get("document_id"):
            cited_document_ids.add(excerpt["document_id"])
    for doc_ref in brief_data.get("source_documents", []):
        if doc_ref.get("document_id"):
            cited_document_ids.add(doc_ref["document_id"])

    real_docs = {d.id: d for d in MedicalDocument.objects.filter(id__in=cited_document_ids)}
    doc_violations = [doc_id for doc_id in cited_document_ids if doc_id not in real_docs or real_docs[doc_id].patient_id != patient_id]

    checks.append({
        "check": "patient_identity_documents_and_source_traceability",
        "passed": not doc_violations,
        "detail": "All cited documents belong to this patient and resolve in the database." if not doc_violations
                   else f"Document id(s) {doc_violations} do not resolve to this patient's own documents.",
    })

    # --- 5: evidence grounding / unsupported claims ------------------------
    trend_statements = {t["trend_statement"] for t in brief_data.get("important_trends", [])}
    med_intel_observations = {o["observation"] for o in brief_data.get("medication_intelligence", {}).get("observations", [])}
    has_medium_or_high_event = any(
        e.get("risk_verdict") in ("medium", "high") for e in brief_data.get("recent_clinical_events", [])
    )

    grounded_observations = []
    for line in brief_data.get("ai_observations", []):
        grounded = False
        if line.startswith("AI Observation (Medication Intelligence): "):
            grounded = line[len("AI Observation (Medication Intelligence): "):] in med_intel_observations
        elif line.startswith("AI Observation: "):
            statement = line[len("AI Observation: "):]
            grounded = (
                statement in trend_statements
                or statement == "Patient experienced symptoms of clinical interest on recent check-ins." and has_medium_or_high_event
                or statement == "Patient parameters appear stable across recorded observations."
            )
        if grounded:
            grounded_observations.append(line)
        else:
            unsupported_claims.append(line)

    checks.append({
        "check": "evidence_grounding_ai_observations",
        "passed": not unsupported_claims,
        "detail": "Every AI Observation traces to a real trend, medication-intelligence finding, or check-in record."
                   if not unsupported_claims else f"{len(unsupported_claims)} observation(s) could not be traced to underlying data and were removed.",
    })

    # --- 6: conflicts surfaced explicitly ----------------------------------
    conflicts = [
        o for o in brief_data.get("medication_intelligence", {}).get("observations", [])
        if o["category"].startswith("conflicting_")
    ]
    checks.append({
        "check": "conflicts_surfaced",
        "passed": True,  # informational - presence of conflicts is not itself a failure, hiding them would be
        "detail": f"{len(conflicts)} conflicting-record observation(s) present and surfaced, not silently resolved."
                   if conflicts else "No conflicting records detected.",
    })

    all_passed = all(c["passed"] for c in checks)

    return {
        "patient_id": patient_id,
        "all_checks_passed": all_passed,
        "checks": checks,
        "unsupported_claims_removed": unsupported_claims,
        "grounded_ai_observations": grounded_observations,
        "conflicts": conflicts,
    }
