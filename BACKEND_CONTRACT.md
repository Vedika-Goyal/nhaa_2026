# 📄 BACKEND_CONTRACT.md — Discovered Backend Contracts & Specification

> **Discovered on:** 2026-09-03  
> **Repository Target:** `d:\NHAA\vinit_repo` (`https://github.com/Vedika-Goyal/nhaa_2026.git`)  
> **Purpose:** Authoritative backend contract documentation mapping all real enums, database models, request/response schemas, API endpoints, authentication mechanisms, state transitions, and differences between codebase and project docs.

---

## 1. Enums

### A. `ChannelOrigin` (`app/models.py`, `app/schemas.py`)
Enum string representation of citizen complaint ingestion channels:
- `portal`
- `chatbot`
- `ivrs`
- `mobile_app`

### B. `CaseStatus` (`app/models.py`, `app/schemas.py`)
Enum string representation of case progression status:
- `new` *(default on creation)*
- `in_progress`
- `escalated`
- `resolved`
- `closed`

### C. `RiskTier` (`app/models.py`, `app/schemas.py`)
Enum string representation of AI/triage risk tiers:
- `low`
- `moderate`
- `high`
- `critical`

### D. `OfficerRole` (`app/models.py`, `app/schemas.py`)
Enum string representation of officer roles & responder specialties:
- `operator`
- `district`
- `state`
- `ministry`
- `police`
- `dlsa`
- `medical`
- `counselor`
- `witness_protection`

### E. `NotificationStatus` (`app/models.py`)
Enum string representation of notification dispatch status:
- `pending` *(held for confirmation gate)*
- `sent`
- `delivered`
- `failed`

---

## 2. Database Models (`app/models.py`)

### 1. `Cases` (`tablename: "cases"`)
- `id` (`BigInt`, Primary Key, Autoincrement)
- `channel_of_origin` (`Enum(ChannelOrigin)`, **Required**)
- `created_at` (`DateTime(tz=True)`, **Required**, Default: `now()`)
- `updated_at` (`DateTime(tz=True)`, **Required**, Default: `now()`, OnUpdate: `now()`)
- `status` (`Enum(CaseStatus)`, **Required**, Default: `"new"`)
- `district` (`String(100)`, Optional)
- `state` (`String(100)`, Optional)
- `incident_description` (`Text`, Optional)
- `incident_date` (`DateTime(tz=True)`, Optional)
- `language` (`String(10)`, **Required**, Default: `"en"`)
- `is_silent_signal` (`Boolean`, **Required**, Default: `False`)
- `victim_id` (`BigInt`, Foreign Key -> `victims.id`, Optional)
- `assigned_officer_id` (`BigInt`, Foreign Key -> `officers.id`, Optional)
- `svi_score` (`Numeric(4, 2)`, Optional)
- `risk_tier` (`Enum(RiskTier)`, Optional)
- `recommended_action` (`String(100)`, Optional)

### 2. `RiskAssessments` (`tablename: "risk_assessments"`)
- `id` (`BigInt`, Primary Key, Autoincrement)
- `case_id` (`BigInt`, Foreign Key -> `cases.id`, **Required**)
- `svi_score` (`Numeric(4, 2)`, **Required**)
- `risk_tier` (`Enum(RiskTier)`, **Required**)
- `flags` (`JSON`, Optional — e.g. `{"trauma": true, "suicidal_ideation": true, "recommended_action": "police_intervention"}`)
- `explanation_text` (`Text`, **Required**)
- `created_at` (`DateTime(tz=True)`, **Required**, Default: `now()`)
- `model_version` (`String(50)`, Optional)

### 3. `Victims` (`tablename: "victims"`)
- `id` (`BigInt`, Primary Key, Autoincrement)
- `pseudoid` (`String(100)`, **Required**, Unique, Comment: "Pseudonymous reference")
- `created_at` (`DateTime(tz=True)`, **Required**, Default: `now()`)
- `age_group` (`String(20)`, Optional)
- `gender` (`String(20)`, Optional)
- `caste_category` (`String(50)`, Optional)
- `language_preference` (`String(10)`, **Required**, Default: `"en"`)
- `consent_given` (`Boolean`, **Required**, Default: `False`)

### 4. `Officers` (`tablename: "officers"`)
- `id` (`BigInt`, Primary Key, Autoincrement)
- `name` (`String(200)`, **Required**)
- `role` (`Enum(OfficerRole)`, **Required**)
- `district` (`String(100)`, Optional)
- `state` (`String(100)`, Optional)
- `badge_id` (`String(50)`, Optional)
- `is_active` (`Boolean`, **Required**, Default: `True`)
- `created_at` (`DateTime(tz=True)`, **Required**, Default: `now()`)

### 5. `Notifications` (`tablename: "notifications"`)
- `id` (`BigInt`, Primary Key, Autoincrement)
- `case_id` (`BigInt`, Foreign Key -> `cases.id`, **Required**)
- `recipient_role` (`Enum(OfficerRole)`, **Required**)
- `channel` (`String(20)`, **Required**, Comment: `"sms"`, `"email"`, `"push"`, `"in_app"`)
- `sent_at` (`DateTime(tz=True)`, Optional)
- `status` (`Enum(NotificationStatus)`, **Required**, Default: `"pending"`)
- `message_template` (`JSON`, Optional)

### 6. `AuditLogs` (`tablename: "audit_logs"`, Append-Only)
- `id` (`BigInt`, Primary Key, Autoincrement)
- `actor` (`String(100)`, **Required**, Comment: `"operator:Central Delhi"`, `"ai_module"`, `"system"`)
- `action` (`String(100)`, **Required**, Comment: `"case_created"`, `"status_updated"`, `"risk_assessed"`, `"officer_decision_confirmed"`)
- `case_id` (`BigInt`, Foreign Key -> `cases.id`, Optional)
- `timestamp` (`DateTime(tz=True)`, **Required**, Default: `now()`)
- `details` (`JSON`, Optional)

### 7. `SlaDeadlines` (`tablename: "sla_deadlines"`)
- `id` (`BigInt`, Primary Key, Autoincrement)
- `case_id` (`BigInt`, Foreign Key -> `cases.id`, **Required**)
- `deadline_type` (`String(50)`, **Required**)
- `due_date` (`DateTime(tz=True)`, **Required**)
- `met` (`Boolean`, **Required**, Default: `False`)
- `resolved_at` (`DateTime(tz=True)`, Optional)

---

## 3. Discovered API Endpoints & Request / Response Schemas

### 1. `POST /api/cases/` (Create Case)
- **Prefix / Path:** `/api/cases/`
- **Request Body (`CaseCreate`):**
  - **Required:** `channel_of_origin` (`ChannelOrigin`)
  - **Optional:** `district` (`str`), `state` (`str`), `incident_description` (`str`), `incident_date` (`datetime`), `language` (`str`, default `"en"`), `is_silent_signal` (`bool`, default `False`), `victim_id` (`int`), `assigned_officer_id` (`int`)
- **Query Parameters:** `role` (`str`), `district` (`str`), `state` (`str`)
- **Response (`CaseOut`):** Status 201 Created. Returns serialized `CaseOut` object. Automatically logs `case_created` action to `audit_logs` and broadcasts WebSocket event `"case_created"`.

### 2. `GET /api/cases/` (List Cases)
- **Prefix / Path:** `/api/cases/`
- **Query Parameters:**
  - `role`: `"operator" | "district" | "state" | "ministry"` (default `"ministry"`)
  - `district`: `str` (optional)
  - `state`: `str` (optional)
  - `status`: `CaseStatus` (optional)
  - `risk_tier`: `RiskTier` (optional)
  - `limit`: `int` (default 100, max 500)
  - `offset`: `int` (default 0)
- **Response:** Status 200 OK. Returns `list[CaseOut]`.

### 3. `GET /api/cases/{case_id}` (Get Case Detail)
- **Prefix / Path:** `/api/cases/{case_id}`
- **Response (`CaseDetail`):** Status 200 OK. Returns `CaseDetail` containing full case fields plus nested `risk_assessments: list[RiskAssessmentOut]`. Returns 404 if not found.

### 4. `PATCH /api/cases/{case_id}` (Update Case / Transition Status)
- **Prefix / Path:** `/api/cases/{case_id}`
- **Request Body (`CaseUpdate`):**
  - **All Optional:** `status` (`CaseStatus`), `district` (`str`), `state` (`str`), `incident_description` (`str`), `assigned_officer_id` (`int`), `svi_score` (`float`), `risk_tier` (`RiskTier`), `recommended_action` (`str`)
- **Response (`CaseOut`):** Status 200 OK. Updates case fields, logs `status_updated` or `case_updated` to `audit_logs`, and broadcasts WebSocket event `"case_updated"`.

### 5. `POST /api/risk-assessments/` (Create Risk Assessment)
- **Prefix / Path:** `/api/risk-assessments/`
- **Request Body (`RiskAssessmentCreate`):**
  - **Required:** `case_id` (`int`), `svi_score` (`float`, bounds $[0.0, 100.0]$), `risk_tier` (`RiskTier`), `explanation_text` (`str`)
  - **Optional:** `flags` (`dict[str, Any]`), `model_version` (`str`)
- **Query Parameters:** `actor` (`str`, default `"ai_module"`)
- **Response (`RiskAssessmentOut`):** Status 201 Created. Links assessment to case, updates `case.svi_score` and `case.risk_tier`, extracts `flags["recommended_action"]` into `case.recommended_action` if present, logs `risk_assessed` to `audit_logs`, broadcasts `"risk_assessment_created"` via WebSocket, and triggers automated notification processing via `process_risk_assessment()`.

### 6. `GET /api/risk-assessments/case/{case_id}` (List Case Risk Assessments)
- **Prefix / Path:** `/api/risk-assessments/case/{case_id}`
- **Response:** Status 200 OK. Returns `list[RiskAssessmentOut]` ordered by `created_at desc`.

### 7. `POST /api/cases/{case_id}/officer-decision` (Officer Decision & Confirmation Gate)
- **Prefix / Path:** `/api/cases/{case_id}/officer-decision`
- **Request Body (`OfficerDecisionIn`):**
  - **Required:** `confirmed_by` (`str` — name/ID of officer confirming action)
- **Response:** Status 200 OK. Returns `list[NotificationOut]`. Dispatches pending critical notifications via `confirm_and_dispatch()`, logs `officer_decision_confirmed` to `audit_logs`, and broadcasts WebSocket event `"notifications_dispatched"`.

### 8. `GET /api/cases/{case_id}/notifications` (List Case Notifications)
- **Prefix / Path:** `/api/cases/{case_id}/notifications`
- **Response:** Status 200 OK. Returns `list[NotificationOut]`.

### 9. `POST /api/risk-assessments/{risk_assessment_id}/dispatch` (Trigger Dispatch)
- **Prefix / Path:** `/api/risk-assessments/{risk_assessment_id}/dispatch`
- **Response:** Status 200 OK. Returns `list[NotificationOut]`. Idempotently creates notifications for recipient roles based on risk tier.

---

## 4. Authentication & Authorization Requirements

- **Current Implementation:** Query parameter based role simulation (`role: "operator" | "district" | "state" | "ministry"`).
- **Row-Level Access Rules:**
  - `operator`: Filtered by `district` (only sees cases in operator's district).
  - `district`: Filtered by `district` (sees all cases in district).
  - `state`: Filtered by `state` (sees all cases in state).
  - `ministry`: Sees all national cases.
- **JWT Specification Contract (`docs/data_contract.md` section 7):**
  - Login endpoint: `POST /auth/login` accepting `{ "username", "password" }`.
  - Returns: `{ "token": "jwt...", "role": "operator", "name": "...", "district": "...", "state": "..." }`.

---

## 5. Notification & Dispatch Logic (`app/services/notifications.py`)

- **Risk Tier Dispatch Rules:**
  - **`low`**: No notifications created.
  - **`moderate`**: Creates `in_app` notification for `counselor` (auto-sent/delivered).
  - **`high`**: Creates `sms`/`in_app` notifications for `district` officer, `police`, `dlsa`, `medical` (auto-sent/delivered).
  - **`critical`**: Creates `pending` notifications for `district`, `police`, `dlsa`, `medical`. **Requires explicit confirmation gate (`POST /api/cases/{case_id}/officer-decision`)** before status converts from `pending` to `delivered`/`sent`.

---

## 6. Discrepancies & Differences Report

| Document / Prompt Reference | Actual Codebase Implementation | Discrepancy & Action Report |
|---|---|---|
| **`POST /api/risk-assessments`** | `POST /api/risk-assessments/` | Path is mounted with trailing slash under `/api` router in `main.py`. |
| **`POST /transition`** | **Not Present** | The backend uses `PATCH /api/cases/{case_id}` for case status updates & transitions. |
| **`GET /cases/{id}/history`** | **Not Present** | The backend uses `GET /api/cases/{case_id}` (returns `CaseDetail` with `risk_assessments`), `GET /api/risk-assessments/case/{case_id}`, and `GET /api/cases/{case_id}/notifications`. |
| **`POST /api/officer-decision`** | `POST /api/cases/{case_id}/officer-decision` | Endpoint path includes `{case_id}` prefix and accepts body `OfficerDecisionIn(confirmed_by: str)`. |
| **`current_level` enum** | **Not Present in DB Schema** | In `app/models.py`, `Cases` uses `status: CaseStatus` and `risk_tier: RiskTier`. Role filtering is driven by `OfficerRole` and query parameters. |
| **`recommended_action`** | Stored in `Cases.recommended_action` | When posting a risk assessment (`POST /api/risk-assessments/`), if `flags` contains `"recommended_action"`, it is extracted and persisted into `Cases.recommended_action`. |

---

## 7. Verification of Test Suite (`tests/`)

- `tests/test_sync.py`: Verifies 4-channel ingestion (`portal`, `chatbot`, `ivrs`, `mobile_app`), WebSocket broadcasts (`case_created`, `case_updated`, `risk_assessment_created`), role-based filtering, `RiskAssessments` creation, append-only `audit_logs`, `PATCH /cases/{id}` status updates, and end-to-end pipeline execution.
- `tests/test_notifications.py`: Verifies notification creation for moderate, high, and critical risk tiers, and confirmation gate execution.
- `tests/test_e2e_channels.py`: Verifies E2E channel ingestion flows.
