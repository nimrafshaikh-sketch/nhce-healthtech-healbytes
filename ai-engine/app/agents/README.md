# Agent Foundation (Gemini)

Phase 1 of the HealBytes multi-agent system: the shared reasoning +
tool-calling foundation every role-specific agent sits on top of. Phase 2
(below) builds the first such agent - the Doctor Agent - without changing
anything in this section; everything here still describes the shared,
role-agnostic foundation only.

## Mental model

```
User/Frontend
    |
Role Agent            <- system instruction + a ToolRegistry (app/agents/agent.py)
    |
Gemini LLM             <- reasoning/decision layer only (app/agents/gemini_client.py)
    |
Tool / Function Calling <- Gemini picks a tool by name + arguments
    |
Tool Registry           <- validates the call, is the ONLY thing that executes it (app/agents/tools/)
    |
Existing Backend/Service <- source of truth: does the real work, enforces auth/RBAC (app/agents/backend_client.py -> Django REST API)
    |
Response
```

One line per layer, because it's easy to blur these together later:

- **Gemini = reasoning brain.** It decides *what* to do and drafts the
  final natural-language reply. It never touches a database, never runs
  code, and never calls anything except by naming a registered tool.
- **Agent = role-specific orchestration.** A system instruction + the
  subset of tools that role is allowed to use, plus the loop that shuttles
  messages and tool results back and forth with Gemini
  (`app/agents/agent.py::Agent`).
- **Tools = controlled actions.** A fixed, explicit, named, schema-checked
  set of functions (`app/agents/tools/`). If it isn't registered, Gemini
  cannot make it happen.
- **Backend = execution / source of truth.** The existing Django REST API
  does the actual work and enforces authentication/RBAC exactly as it
  does for the real frontend. Tools call it over HTTP; they never touch
  the database or bypass its permission checks.
- **Frontend = presentation.** Out of scope here; the frontend would call
  the FastAPI route in `app/agents/routes.py` the same way it calls
  `/analyze` today.

## Why the AI Engine calls the backend, not the other way around

Every other endpoint in this service (`/analyze`, `/history/summary`)
receives all its data in the request body and has zero I/O. The agent
foundation is the first thing in `ai-engine/` that makes an outbound call,
and it's deliberately narrow: `BackendClient` (`app/agents/backend_client.py`)
only ever forwards the *caller's own* bearer token to the existing Django
API. It never stores, mints, or elevates credentials, and it never opens a
direct database connection. If the backend's own RBAC would reject a
request from the real frontend, it rejects the agent's tool call the same
way - see `UnauthorizedError` in `app/agents/exceptions.py`.

## Files

| File | Responsibility |
|---|---|
| `gemini_client.py` | The only file that imports `google.genai`. Lazy API-key validation, one `generate()` call, normalizes the response into a `ModelTurn` (either final text or a list of function calls). |
| `tools/base.py` | `Tool` (name + description + JSON-schema args + handler), `ToolContext` (carries the caller's bearer token - nothing else), `ToolRegistry` (register/get/execute - the strict execution boundary). |
| `tools/patient_tools.py` | The Phase 1 proof-of-concept tool: `get_patient_basic_info`, calling the existing `GET /api/patients/{id}/`. Reused unchanged by the Doctor Agent. |
| `tools/default_registry.py` | `build_default_registry()` - the Phase 1 demo agent's one-tool registry. |
| `tools/doctor_tools.py` | Phase 2: the five additional Doctor Agent tools (medications, adherence, risk, history, RAG search). |
| `tools/doctor_registry.py` | Phase 2: `build_doctor_registry()` - all six tools the Doctor Agent may use. |
| `backend_client.py` | Minimal `httpx` GET wrapper (`params=` supported) that forwards the bearer token and turns backend failures into `UnauthorizedError` / `ToolExecutionError`. |
| `agent.py` | `Agent.run()` - the system-instruction + message + history + tool-calling loop, bounded by `AGENT_MAX_TOOL_ITERATIONS`. Shared, unchanged, by both agents. |
| `routes.py` | `POST /api/v1/agents/patient-summary` - the Phase 1 demo endpoint. Maps every agent-foundation exception to a specific HTTP status. |
| `doctor_routes.py` | Phase 2: `POST /api/v1/agents/doctor` - the Doctor Agent endpoint, same exception-mapping pattern as `routes.py`. |
| `schemas.py` | `AgentChatRequest` / `AgentChatResponse` / `ToolCallRecord` - the HTTP contract for this capability (separate from the fixed `/analyze` contract in `app/schemas/`). |
| `exceptions.py` | One exception per failure mode: missing key, Gemini API failure, malformed Gemini response, unknown tool, invalid arguments, tool execution failure, unauthorized. |

## Configuration

All in `app/config.py` / `.env` (see `.env.example`):

- `GEMINI_API_KEY` - required for any `/agents/*` call. Never hardcoded,
  never sent to the frontend. Absent key -> `GeminiConfigError` -> `503`,
  not a crash; every other endpoint keeps working.
- `GEMINI_MODEL` - defaults to the `gemini-flash-latest` alias; pin an
  exact version string for production.
- `AGENT_MAX_TOOL_ITERATIONS` - caps Gemini <-> tool round-trips per
  request (default 4), so a confused model can't loop forever.
- `BACKEND_API_BASE_URL` / `BACKEND_API_TIMEOUT_SECONDS` - where the
  existing Django backend lives, and how long a tool waits for it.

## Security boundaries (enforced, not just documented)

1. **No direct database access.** Every tool that needs data calls the
   existing backend's REST API over HTTP.
2. **No arbitrary code execution.** There is no "run this Python/shell"
   tool, and none is planned - the registry only ever executes a
   pre-registered, named, schema-checked function.
3. **Existing auth/RBAC is the only authority.** The agent forwards the
   caller's bearer token; it never impersonates a role or invents a
   service-account identity. A tool call with no token fails closed
   (`UnauthorizedError`) before any HTTP request is made.
4. **Least privilege beyond the backend's own.** `get_patient_basic_info`
   deliberately returns a smaller field set than the backend's
   `PatientSerializer` exposes (e.g. never `medical_notes`) - a tool can
   always narrow what it hands to Gemini further than the backend already
   does, never widen it.
5. **Every failure mode maps to a specific, non-leaking error**: missing
   key -> 503, Gemini call failure or unparseable response -> 502,
   invalid/unknown tool call or execution failure -> reported back to
   Gemini as a structured error (visible in `tool_calls` in the response)
   rather than crashing the request, orchestration-level failure (e.g.
   iteration cap) -> 500 with a generic message.

## Doctor Agent (Phase 2)

### Purpose

Lets an authenticated doctor ask a natural-language question about one of
their own patients - e.g. *"Give me a concise clinical summary for this
patient, including current medications, adherence, major risks, and
anything needing follow-up."* - and get a grounded answer built entirely
from real, authorized data, not invented by Gemini.

### Architecture

```
Doctor (JWT)
    |
Doctor Agent            <- app/agents/doctor_routes.py: DOCTOR_SYSTEM_INSTRUCTION + build_doctor_registry()
    |
Gemini                   <- reasoning/orchestration only - decides which tool(s) the question needs
    |
Tool / Function Calling
    |
Tool Registry             <- app/agents/tools/doctor_tools.py (6 tools, see below)
    |
Existing Django Backend + AI Engine  <- source of truth: real data, real auth/RBAC, real deterministic analysis
    |
Real authorized patient data
    |
Gemini                   <- synthesizes the tool result(s) into a grounded answer
    |
Doctor receives a concise, grounded response
```

Gemini never sees the database and never recomputes a clinical
calculation - it only chooses which existing capability to call and then
explains the result. The doctor's own JWT is forwarded on every tool
call, so the existing backend's authentication and RBAC decide what comes
back, exactly as if the doctor had called that API directly.

### Tools (reusing existing capabilities - nothing recalculated)

| Tool | Existing capability it wraps | Existing endpoint/service |
|---|---|---|
| `get_patient_basic_info` | Patient record (Phase 1, unchanged) | `GET /api/patients/{id}/` |
| `get_patient_medications` | Medication records | `GET /api/medications/?patient={id}` |
| `get_medication_adherence` | AI Engine's deterministic adherence calculation (`app/history/summary_service.py::compute_medication_adherence`) | `GET /api/analytics/patients/{id}/ai-summary/` -> `history.medication_adherence` |
| `get_patient_risk` | AI Engine's deterministic `/analyze` result, already computed at check-in time and stored on the check-in (`apps.checkins.ai_client.analyze_checkin`) | `GET /api/checkins/?patient={id}` -> most recent check-in's `ai_risk_*` fields |
| `get_patient_history` | AI Engine's deterministic `/history/summary` result (`app/history/summary_service.py`) | `GET /api/analytics/patients/{id}/ai-summary/` -> `history` (minus `medication_adherence`, which has its own tool) |
| `search_patient_records` | Existing patient-scoped RAG (semantic embedding retrieval, keyword/TF-cosine fallback - `apps.documents.embeddings` / `apps.documents.rag`) | `GET /api/documents/rag-search/?patient_id={id}&query={q}` |

No new calculation, no new vector store, no new database access was
added anywhere - every tool is a thin, least-privilege HTTP wrapper (see
`app/agents/tools/doctor_tools.py` for the exact field filtering each one
applies) around an endpoint that already existed before Phase 2.

Gemini is never forced to call every tool. It sees all six as available
functions and picks only the ones the doctor's actual question needs -
"is this patient's adherence okay?" calls just `get_medication_adherence`;
"show me their basic details" calls just `get_patient_basic_info`. This
falls straight out of how Gemini function calling already works in the
shared foundation (`agent.py`); nothing in this phase forces a fixed tool
sequence.

### RAG flow

`search_patient_records(patient_id, query)` calls the existing
`GET /api/documents/rag-search/` endpoint unchanged.
`apps.documents.views.DocumentRAGSearchView` independently re-verifies
that the requesting doctor is authorized for that specific patient
(including the existing QR-grant fallback) before running any retrieval,
and the retrieval itself is already patient-isolated at the query level.
This tool adds no new authorization logic and no new retrieval engine -
it is a pass-through to a system that was already correct.

### Authorization flow

Identical to Phase 1's model, applied to every one of the six tools: the
Doctor Agent extracts the caller's bearer token from the
`Authorization: Bearer <token>` header and forwards it as-is to whichever
backend endpoint a tool calls. Two differences from the generic Phase 1
demo agent, specific to a doctor-facing, always-patient-scoped agent:

- `patient_id` is required on the request (`422` if missing) - a Doctor
  Agent question is always about a specific patient.
- A missing/malformed `Authorization` header is rejected immediately with
  `401`, before any Gemini call is made - every Doctor Agent tool needs
  real credentials, so there's no useful turn that doesn't.

Because the existing backend endpoints enforce doctor-patient ownership
in two different (both correct) ways, the *failure mode* for "wrong
doctor" varies by tool, though the security property - no cross-doctor
data ever returned - holds for all of them:

- `get_patient_basic_info` / `search_patient_records` -> explicit `403`
  (object-level permission check) -> surfaced as `UnauthorizedError`.
- `get_medication_adherence` / `get_patient_history` -> `404` (the
  analytics views use `get_object_or_404(doctor=request.user)`, a
  non-enumeration pattern that doesn't reveal whether the patient exists
  at all) -> surfaced as `ToolExecutionError`.
- `get_patient_medications` / `get_patient_risk` -> the list endpoints are
  pre-filtered to the doctor's own patients, so an unowned `patient_id`
  simply returns an empty list, not an error.

### Example request

```bash
curl -X POST http://localhost:8001/api/v1/agents/doctor \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <doctor-access-token>" \
  -d '{
        "request_id": "doc-turn-1",
        "patient_id": "7",
        "message": "Give me a concise clinical summary for this patient. Include their current medications, adherence status, major risks, and anything that may require follow-up."
      }'
```

### Example response shape

```json
{
  "request_id": "doc-turn-1",
  "reply": "Patient 7 is on Metformin 500mg (active). Adherence is partially adherent. Most recent check-in (2026-09-01) shows High risk - prompt physician review is recommended. No open follow-up appointment is scheduled.",
  "tool_calls": [
    {"tool_name": "get_patient_medications", "arguments": {"patient_id": "7"}, "succeeded": true, "summary": "'get_patient_medications' completed successfully."},
    {"tool_name": "get_medication_adherence", "arguments": {"patient_id": "7"}, "succeeded": true, "summary": "'get_medication_adherence' completed successfully."},
    {"tool_name": "get_patient_risk", "arguments": {"patient_id": "7"}, "succeeded": true, "summary": "'get_patient_risk' completed successfully."}
  ],
  "model_version": "gemini-flash-latest"
}
```

`reply` is the only field meant for display; `tool_calls` is a
transparency/debugging trace (which controlled action actually ran, not
raw patient data) and never includes an API key, internal token, or
database credential - see `ToolCallRecord` in `schemas.py`.

### Running / testing the Doctor Agent

Same process as the rest of the foundation:

```bash
cd ai-engine
pip install -r requirements-dev.txt
cp .env.example .env   # fill in GEMINI_API_KEY and BACKEND_API_BASE_URL
uvicorn app.main:app --reload
pytest tests/agents/test_doctor_tools.py tests/agents/test_doctor_registry.py \
       tests/agents/test_doctor_agent_flow.py tests/agents/test_doctor_routes.py
```

`test_doctor_agent_flow.py` runs the real `Agent` and the real doctor tool
handlers against a mocked Gemini client and a mocked backend HTTP layer -
the closest thing to the live flow this suite can exercise without real
credentials/services. For an actual live run (real Gemini, real backend),
see "Manual smoke test" above - point it at `/api/v1/agents/doctor` with a
`patient_id` in the body instead of `/api/v1/agents/patient-summary`.

## Adding a new agent (Phase 3+ guidance)

A role-specific agent is just a different system instruction plus a
different (possibly larger) `ToolRegistry` - nothing in `agent.py`,
`gemini_client.py`, or `tools/base.py` needs to change. The Doctor Agent
above (`doctor_tools.py`, `doctor_registry.py`, `doctor_routes.py`) is a
worked example of every step below - copy its shape for the next agent
(e.g. Receptionist), not this generic description.

1. **Write the tool(s) first**, in a new module under `app/agents/tools/`
   (e.g. `doctor_tools.py`). Each tool is a `Tool(name=..., description=...,
   parameters_json_schema=..., handler=...)`. The handler receives
   `(arguments: dict, context: ToolContext)` and must return a JSON-serializable
   `dict`. Call the existing backend via `BackendClient`/`httpx`, or reuse
   an existing `ai-engine/app/analysis` or `app/history` function directly
   if the data is already local to this service - never add new business
   logic that duplicates what the backend already owns.
2. **Register it** in a new registry-building function (copy the shape of
   `tools/default_registry.py`) rather than editing the shared default
   registry, unless the tool is genuinely meant to be available to every
   agent.
3. **Write the system instruction.** Be explicit about what the agent may
   and may not do, and repeat the "you may only act through your tools"
   and "never provide a diagnosis/treatment" constraints from
   `routes.py::_SYSTEM_INSTRUCTION` - Gemini only respects boundaries it's
   told about.
4. **Add a route** (or reuse `routes.py`'s pattern) that builds
   `ToolContext(bearer_token=...)` from the incoming request the same way,
   constructs an `Agent(system_instruction, your_registry)`, and maps
   exceptions to HTTP status codes the same way. Copy the try/except block
   in `run_patient_summary_agent` - it already covers every failure mode
   above.
5. **Test the tool and the route with a mocked `GeminiClient`/`Agent`**,
   the same way `tests/agents/` does - no test in this codebase makes a
   real Gemini or backend call.

## Running

```bash
cd ai-engine
pip install -r requirements-dev.txt
cp .env.example .env   # then fill in GEMINI_API_KEY and BACKEND_API_BASE_URL
uvicorn app.main:app --reload
pytest
```

## Manual smoke test (once a real `GEMINI_API_KEY` is available)

With the Django backend running locally and a valid patient + doctor JWT:

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "<doctor-username>", "password": "<password>"}'
# -> copy the "access" token from the response

curl -X POST http://localhost:8001/api/v1/agents/patient-summary \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access-token-from-above>" \
  -d '{
        "request_id": "smoke-1",
        "message": "Can you look up the basic info for patient 1?"
      }'
```

Expected: a `200` with a natural-language `reply` and a `tool_calls` entry
for `get_patient_basic_info` with `"succeeded": true`. A missing/invalid
token should show up as `"succeeded": false` with an unauthorized summary,
not a crash.
