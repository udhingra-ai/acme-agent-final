# Interview Evidence Pack

Concise reference for panel Q&A. All claims are verifiable from the running stack or source files.

---

## 1. Requirements coverage

| Brief Requirement | Implementation | File | How to verify |
|---|---|---|---|
| Keycloak auth | JWT bearer token flow + realm import | `keycloak/realm-export.json`, `app/auth/security.py` | `curl POST /auth/token` returns JWT |
| Role-based access | Server-side `require_role()` in orchestrator | `app/agents/orchestrator.py:42` | `sales_user` + "create" query → 403 |
| Dynamic LLM tool use | OpenAI planner + rule fallback | `app/agents/planner.py` | `planner_mode: llm` in response |
| PostgreSQL | 5-table schema, seed data, parameterised queries | `db/init/`, `app/repositories/` | `docker exec acme-postgres psql …` |
| Redis | Session history (1 h TTL) + profile cache (15 min TTL) | `app/services/memory_service.py` | `docker exec acme-redis redis-cli KEYS "*"` |
| MCP server | Tool registry at `:8100/tools` | `mcp_server/server.py` | `curl http://localhost:8100/tools` |
| Reusable Skill | Customer Escalation Skill — deterministic rubric | `app/skills/customer_escalation.py` | Skill output in `/query` response steps |
| Docker Compose | Single `docker compose up --build` | `docker-compose.yml` | `docker compose ps` — 6 containers Up |
| Evaluation | 10 test cases; tool_match, status_match, grounded | `evals/` | `python evals/runner.py` |
| Observability | Structured JSON logs: tool_call, request_trace, timing | `app/observability/` | `docker compose logs -f app` |

---

## 2. Key design decisions

**LLM planner + deterministic fallback**
The planner calls OpenAI with a constrained system prompt and `response_format: json_object`. If the call fails or the key is absent, `build_plan()` silently falls back to a keyword-based rule planner. The system is demonstrable end-to-end without any API key.

**RBAC in the orchestrator, not the planner**
The LLM selects which tools to call, but the orchestrator enforces role requirements before each tool executes. This means adversarial prompts cannot bypass authorisation — the LLM is a routing layer, not a security boundary.

**MCP as a tool registry, not an execution router**
The MCP server owns tool definitions. The execution layer calls PostgreSQL directly for demo reliability. The boundary is explicit and documented. Closing the gap is a one-file change per side (`orchestrator.py` + `mcp_server/server.py`).

**Customer Escalation Skill is stateless and deterministic**
No LLM call inside the skill. Input: profile, issues, history. Output: risk level, rationale, urgency, owner suggestion, evidence provenance. The rubric is documented in `app/skills/customer_escalation.py`. Results are reproducible given the same input.

**Redis for session + cache**
Session history uses `session:{id}` keys with 1-hour TTL. Customer profiles use `customer:{name}` with 15-minute TTL. Rationale: session data is ephemeral and query-specific; PostgreSQL is the durable source of truth.

---

## 3. Security controls summary

| Control | Where enforced | Evidence |
|---|---|---|
| JWT signature validation | `app/auth/security.py` JWKS fetch | 401 on tampered token |
| RBAC server-side | `orchestrator.py` `require_role()` | 403 on sales_user write attempt |
| Parameterised SQL | `repositories/` SQLAlchemy `text()` | No string interpolation of user input |
| Prompt-injection resistance | Pre-LLM pattern guard (`prompt_guard.py`) + RBAC post-planning | Eval T10: 400 — blocked at prompt_guard before any LLM call; never reaches planner |
| Local auth bypass gated | `APP_ENV=local` check in `security.py:52` | Non-local env → 401 without bearer |
| Secrets not logged | No token/key in log events | `logging_utils.py` log fields |

---

## 4. Evaluation summary

Run: `python evals/runner.py`

16 test cases:

| ID | Query summary | Role | Expected status | Expected tools | Key assertion |
|---|---|---|---|---|---|
| T01 | Open issues for Pinnacle Bancorp | sales_user | 200 | get_customer_profile, get_open_issues | Happy-path read; 2-tool plan |
| T02 | Summarise latest status for Nexus Payments Ltd | support_user | 200 | get_customer_profile, get_open_issues, get_issue_history | History path included; support_user bypasses RLS |
| T03 | Customer profile for Apex Clearing Services | sales_user | 200 | get_customer_profile | Profile-only; minimal 1-tool plan |
| T04 | Customer profile for Meridian Capital Group | sales_user | 200 | get_customer_profile | Different customer; tests name extraction |
| T05 | List all critical issues across all clients | sales_user | 200 | list_all_open_issues | Portfolio-wide query; no customer name → cross-customer tool |
| T06 | Which clients have high severity open issues | support_user | 200 | list_all_open_issues | Portfolio severity filter; must not route to single-client tools |
| T07 | Summarise latest status for Apex Clearing Services + suggest next action | support_user | 200 | get_customer_profile, get_open_issues, get_issue_history, recommend_next_action | Full plan; support_user authorised for write tool |
| T08 | Create next action for Pinnacle Bancorp | sales_user | 403 | (none) | RBAC enforcement; sales_user blocked on write |
| T09 | Profile for NonExistentCorp | sales_user | 200 | get_customer_profile | Unknown customer; tool called, graceful empty response |
| T10 | Prompt injection: "Ignore all previous instructions…" | sales_user | 400 | (none) | Blocked at prompt_guard before any LLM call; patterns 1 + 3 matched |
| T11 | Show all issues currently in progress across all clients | sales_user | 200 | list_all_open_issues | Status filter cross-customer; statuses=['in_progress'] |
| T12 | Full summary for Nexus Payments Ltd + suggest next action | support_user | 200 | get_customer_profile, get_open_issues, get_issue_history, recommend_next_action | Full 4-tool flow; different customer |
| T13 | List all critical and high severity issues across all clients | admin | 200 | list_all_open_issues | Admin role portfolio query; verifies admin allowed for read paths |
| T14 | Summarise latest status and history for Meridian Capital Group | support_user | 200 | get_customer_profile, get_open_issues, get_issue_history | Single-customer summary with history |
| T15 | Find issues related to rate limiting or API throttling | support_user | 200 | semantic_search_issues | Semantic/RAG path; conceptual query routes to vector search |
| T16 | Show all open issues for Pinnacle Bancorp | admin | 200 | get_customer_profile, get_open_issues | Admin role single-customer read |

Grounding check: 200 responses must return `steps` array with real tool outputs (not empty, not "No relevant information found."). 400/403 responses are grounded by their error status.

---

## 5. Observability examples

```json
{"ts":"2026-06-23T09:00:01","kind":"tool_call","payload":{"tool":"get_customer_profile","cached":false,"customer_name":"Pinnacle Bancorp"}}
{"ts":"2026-06-23T09:00:01","kind":"tool_call","payload":{"tool":"get_customer_profile","cached":true,"customer_name":"Pinnacle Bancorp"}}
{"ts":"2026-06-23T09:00:01","kind":"tool_call","payload":{"tool":"get_open_issues","customer_name":"Pinnacle Bancorp"}}
{"ts":"2026-06-23T09:00:01","kind":"tool_call","payload":{"tool":"recommend_next_action","issue_id":1,"owner":"bob.support"}}
{"ts":"2026-06-23T09:00:02","kind":"request_trace","payload":{"path":"/query","method":"POST","trace_id":"...","status_code":200,"elapsed_ms":312}}
{"ts":"2026-06-23T09:00:02","kind":"timing","payload":{"function":"tool_get_customer_profile","elapsed_ms":8.4}}
```

View live: `docker compose logs -f app`
View Redis keys: `docker exec acme-redis redis-cli KEYS "*"`

---

## 6. Trade-offs and talking points

**Trade-off 1 — MCP execution bypass**
*Why:* HTTP hop adds latency and failure surface in a prototype.
*Mitigation:* Tool definitions live in MCP; a one-file change routes execution through it.
*Talking point:* "In production I would wire the orchestrator to call MCP's execution endpoint. The separation of definition from execution is already in the architecture."

**Trade-off 2 — LLM dependency with fallback**
*Why:* Rule-based fallback ensures the demo always works.
*Mitigation:* Fallback covers all 10 eval cases.
*Talking point:* "The system is designed to degrade gracefully. If the LLM provider goes down, all functionality continues at rule-based quality."

**Trade-off 3 — Redis without auth**
*Why:* Standard for local Docker stacks.
*Mitigation:* Add Redis AUTH + VPC restriction in production.

**Trade-off 4 — No HTTPS**
*Why:* Local dev only.
*Mitigation:* TLS termination at load balancer.

---

## 7. Ten interview talking points

1. **RBAC is server-side**: "Role enforcement lives in the orchestrator, not the client or LLM. Even adversarial prompts cannot bypass it — verified in eval T10."

2. **LLM as a router, not a security gate**: "The planner makes routing decisions. The orchestrator enforces policy. These are separate concerns and separate code paths."

3. **Deterministic skill with documented rubric**: "The Customer Escalation Skill applies a documented, reproducible rubric — account health, severity, staleness. No LLM call inside the skill. Output is auditable and testable."

4. **Graceful degradation**: "If OpenAI is unavailable, the rule planner handles all supported queries. If Redis is unavailable, the only loss is session history — core functionality continues."

5. **MCP boundary is deliberate**: "Tool definitions are owned by MCP. Execution bypasses MCP in this prototype for reliability. The boundary is explicit, documented, and closeable with a one-file change."

6. **Parameterised SQL throughout**: "All database queries use bound parameters. User input never touches SQL string construction."

7. **AI tooling used responsibly**: "I used Claude Code for scaffolding and boilerplate. I manually reviewed every security boundary, caught three AI-generated bugs, and validated every endpoint with curl before sign-off."

8. **Eval set covers adversarial cases**: "Sixteen test cases including prompt injection (T10 → 400), unknown customer (T09), RBAC enforcement (T08), semantic search (T15), admin role (T13, T16), and multiple roles. Grounding check verifies real DB data, not just status codes."

9. **Redis rationale is documented**: "Session history is ephemeral and query-specific — Redis is the right store. Customer profiles are stable for 15 minutes — cache reduces latency. PostgreSQL remains the durable source of truth."

10. **Production path is clear**: "TLS at load balancer, Redis AUTH + VPC, token introspection for revocation, OpenTelemetry for distributed tracing, rate limiting at the API gateway. None of these require architectural changes — they're configuration and infrastructure additions."

---

## 8. Remaining known limitations

| Limitation | Severity | Talking point |
|---|---|---|
| MCP execution not routed through MCP server | Low | Deliberate prototype trade-off; documented; one-file fix |
| TLS is self-signed (browser warning) | Low | Addressed locally with nginx; prod uses CA-signed cert |
| Redis AUTH uses plain local password | Low | Addressed locally; prod uses secrets manager + VPC |
| Keycloak not behind TLS proxy | Low | Token issuance over plain HTTP on :8080 locally; prod: terminate at shared gateway |
| No token revocation | Low | Short-lived tokens (5 min); add introspection in production |
| Single-issue history (history for `issues[0]` only) | Low | Sufficient for demo; production would iterate all issues |
| `.env` contains live API key | Medium | Never commit; use secrets manager in production |
