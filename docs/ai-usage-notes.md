# AI Usage Notes

## How AI tooling was used

- Used AI assistance to accelerate scaffolding, boilerplate, docs, and repetitive integration code.
- Reviewed generated code manually against the assessment brief and adjusted auth, RBAC, schema, planner behavior, and evaluation logic.
- Did not trust AI outputs blindly for security boundaries, bearer-token validation, token claims parsing, or production-readiness assumptions.
- Added an LLM-backed planner only behind a safe fallback design so the system remains demoable even if an external model is unavailable.

## Bugs found and corrected during validation

### 1. Keycloak realm-export missing user profile fields (runtime)
**What happened:** Users created in `keycloak/realm-export.json` without `email`, `emailVerified`, or `firstName`/`lastName` fields. Keycloak 25 enforces a User Profile schema that requires `email` for the `user` role. Token acquisition returned `{"error":"invalid_grant","error_description":"Account is not fully set up"}`.

**How found:** Running `POST /auth/token` end-to-end; raw Keycloak error surfaced the exact cause.

**Fix:** Added `email`, `firstName`, `lastName`, `emailVerified: true`, `requiredActions: []` to all three users in `realm-export.json`.

**Validated by:** All three users now return valid JWTs with correct realm_access roles.

### 2. Greedy customer-name regex in rule planner (logic)
**What happened:** `infer_customer_name` used `[A-Za-z0-9\s&-]+` which matches any character including spaces and lowercase letters. For the query `"Summarise the latest status for Client X and suggest the next action"`, it extracted `"Client X and suggest the next action"` as the customer name. PostgreSQL found no match, `issues = []`, and the orchestrator raised HTTP 400 "No issue available for next action".

**How found:** Eval harness test 3 (`support_user` with full-plan query) returned status 400 instead of 200; stepping through the planner logic revealed the regex was consuming trailing lowercase words.

**Fix:** Changed to `[A-Z][A-Za-z0-9&-]*(?:\s+[A-Z][A-Za-z0-9&-]*)*` — matches only sequences of title-cased words, stopping at the first lowercase conjunction ("and", "or", etc.).

**Validated by:** Eval harness 6/6 PASS after fix; customer name extracts as `"Client X"` for all test queries.

### 3. Eval YAML contradictory expectations for RBAC-blocked test (test design)
**What happened:** `evals/test_queries.yaml` test 4 set `expected_tools: ["get_customer_profile", "get_open_issues", "recommend_next_action"]` together with `expect_status: 403`. A 403 response carries no `steps` field, so `actual_tools` is always `[]`, making `tool_match` permanently false for that test.

**How found:** Eval summary showed `tool_match 4/6`; inspecting failing tests showed the 403 case was structurally impossible to pass.

**Fix:** Changed `expected_tools` to `[]` for the RBAC-block test case. The `status_match` (403) and `grounded` checks remain meaningful.

**Validated by:** Eval harness 6/6 PASS.

## Hallucinations / incorrect outputs caught

- Initial architecture diagram implied MCP handles all tool execution; corrected to reflect that tool functions currently call PostgreSQL directly. Architecture doc now includes an explicit trade-off section.
- Initial README implied `docker compose up --build` would work without any setup beyond copying `.env.example`. This was true for the rule-based planner path (no LLM key needed), but Keycloak user account setup was silently broken. Now documented and fixed at the realm-export level.

## How generated code was validated

- Every API endpoint tested with `curl` before sign-off.
- JWT claims decoded manually to verify role extraction.
- SQL queries run directly against the container database to verify schema alignment.
- Redis session accumulation verified by sending two identical queries and confirming history grows.
- Evaluation harness used as the automated regression layer throughout development.
