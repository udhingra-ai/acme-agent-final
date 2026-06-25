# Atlas — Agentic Operations Assistant

A production-pattern agentic assistant for enterprise operations teams.

---

## Requirements coverage

| Brief requirement | Implementation | Evidence | How to verify |
|---|---|---|---|
| Keycloak authentication | JWT bearer token flow; realm import at startup | `keycloak/realm-export.json`, `app/auth/security.py` | `curl POST /auth/token` |
| Role-based access control | Server-side `require_role()` in orchestrator | `app/agents/orchestrator.py` | `sales_user` + write query → 403 |
| Bounded 3-agent workflow | Planning → Risk/Action → Response agents with clear boundaries | `app/agents/` | `agent_stage` fields in logs |
| Dynamic LLM tool use | OpenAI planner + rule-based fallback | `app/agents/planner.py` | `planner_mode` field in response |
| Deterministic primary-issue selection | Severity → status → newest ID | `app/agents/risk_action_agent.py` | `selected_primary_issue` in response steps |
| PostgreSQL | 5 tables, parameterised queries, seed data | `db/init/`, `app/repositories/` | `docker exec acme-postgres psql …` |
| Redis | Session history (1 h TTL) + profile cache (15 min TTL) | `app/services/memory_service.py` | `docker exec acme-redis redis-cli KEYS "*"` |
| MCP server | Tool registry + 4 read endpoints | `mcp_server/server.py` | `curl http://localhost:8100/tools` |
| Reusable Skill | Customer Escalation Skill — deterministic risk rubric | `app/skills/customer_escalation.py` | `skill: risk_action_agent` in response steps |
| Docker Compose | Single command; 6 services (nginx, app, postgres, redis, keycloak, mcp-server) | `docker-compose.yml` | `docker compose ps` |
| Evaluation | 14 test cases; tool_match, status_match, grounded, latency | `evals/` | `python evals/runner.py` |
| Observability | Structured JSON: agent_output (trace_id), tool_call (via), request_trace | `app/observability/` | `docker compose logs -f app` |

---

## Quick start

```bash
cp .env.example .env
# Optional: add a real OPENAI_API_KEY to .env for LLM planning
# The system runs fully in deterministic fallback mode without one

docker compose up --build
```

Open **https://localhost** — the UI loads with demo credentials pre-filled.

> **Browser certificate warning expected.** The TLS cert is self-signed. In Chrome: click *Advanced → Proceed to localhost*. In Firefox: click *Advanced → Accept the Risk and Continue*.

Port 8000 remains available for direct HTTP access and is used by the eval harness.

---

## Environment setup

Copy `.env.example` to `.env`. The only variable that needs a real value for full LLM behaviour is:

| Variable | Required | Default / Placeholder |
|---|---|---|
| `OPENAI_API_KEY` | Optional | `replace_me` — falls back to rule planner |
| `OPENAI_MODEL` | No | `gpt-4.1-mini` |
| `DATABASE_URL` | No | pre-wired to Postgres container |
| `REDIS_URL` | No | `redis://:acme-redis-local@redis:6379/0` — includes password |
| `REDIS_PASSWORD` | No | `acme-redis-local` — injected into Redis container at startup |
| `KEYCLOAK_SERVER_URL` | No | pre-wired to Keycloak container |
| `KEYCLOAK_CLIENT_SECRET` | No | not needed (public client) |
| `APP_ENV` | No | `local` — enables x-role header auth for quick testing |

**LLM mode:** If `OPENAI_API_KEY` is set to a valid key, the planner calls GPT to build a structured tool plan. If the key is absent or the call fails, the system automatically falls back to a deterministic rule-based planner. All other functionality is identical.

---

## Demo users

All passwords: `Password123!`

| Username | Role | Can do |
|---|---|---|
| `alice.sales` | `sales_user` | Profile lookups, issue lists, issue history |
| `bob.support` | `support_user` | All of the above + recommend/create next actions |
| `carol.admin` | `admin` | All of the above |

**RBAC note:** Queries that include "suggest", "recommend", "next action", or "create" will trigger `recommend_next_action` in the plan, which requires `support_user` or `admin`. A `sales_user` sending such a query receives HTTP 403. Pure read queries (profile, issues, history) always succeed for `sales_user`.

---

## Auth modes

### Mode 1 — Keycloak bearer token (production flow)

```bash
# 1. Acquire a token
curl -X POST http://localhost:8000/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"bob.support","password":"Password123!"}'

# 2. Use the access_token in subsequent requests
TOKEN=<paste access_token here>
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"user_query":"Summarise the latest status for Pinnacle Bancorp and suggest the next action.","session_id":"demo-session"}'
```

### Mode 2 — Local header override (quick testing, APP_ENV=local only)

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -H 'x-role: support_user' \
  -H 'x-user: bob.support' \
  -d '{"user_query":"Summarise the latest status for Pinnacle Bancorp and suggest the next action.","session_id":"demo-session"}'
```

---

## Demo queries

| Query | Role | Expected behaviour |
|---|---|---|
| `"Show me open customer issues for Pinnacle Bancorp"` | any | Profile + issues |
| `"Summarise the latest status for Nexus Payments Ltd"` | any | Profile + issues + history |
| `"Summarise the latest status for Pinnacle Bancorp and suggest the next action."` | support_user / admin | Full plan with recommend_next_action |
| `"Summarise the latest status for Pinnacle Bancorp and suggest the next action."` | sales_user | 403 Insufficient role |
| `"Give me the customer profile for Meridian Capital Group"` | any | Profile only |

---

## Services

| Service | URL | Notes |
|---|---|---|
| App UI + API (HTTPS) | https://localhost | Primary user-facing endpoint (nginx TLS) |
| App UI + API (HTTP) | http://localhost:8000 | Direct — used by eval harness |
| API docs (Swagger) | http://localhost:8000/docs | Auto-generated |
| MCP tool registry | http://localhost:8100/tools | Tool definitions |
| Keycloak admin | http://localhost:8080 | admin / admin |

---

## Architecture overview

See [`docs/architecture.md`](docs/architecture.md) for the full diagram and component table.

**Bounded 3-agent workflow:**

```
User → nginx :443 (TLS) → FastAPI app :8000 → JWT validation + RBAC
                                             ↓
                                [Agent 1 — Planning Agent]
                                  OpenAI LLM → structured plan {steps, reasoning}
                                  (rule-based fallback if LLM unavailable)
                                             ↓
                                [Tool Execution — orchestrator/app layer]
                                  RBAC enforced here (not by LLMs)
                                  → get_customer_profile  (Redis cache → MCP → DB fallback)
                                  → get_open_issues       (MCP → DB fallback)
                                  → get_issue_history     (MCP → DB fallback)
                                  → list_all_open_issues  (MCP → DB fallback)
                                  → recommend_next_action (direct DB, role-gated)
                                             ↓
                                [Agent 2 — Risk/Action Agent]
                                  Deterministic primary-issue selection
                                  Risk rubric (severity, health, staleness)
                                  Structured output {selected_primary_issue, risk_level, urgency}
                                             ↓
                                [Agent 3 — Response Agent]
                                  LLM synthesis (or rule-based fallback)
                                  Never invents facts outside tool outputs
                                             ↓
                                  Redis session write + structured log with trace_id
```

6 services: nginx (TLS), app, postgres, redis, keycloak, mcp-server.

### MCP server

The MCP server at `:8100` exposes the canonical tool registry (`GET /tools`) and 4 read endpoints: `GET /customer/{name}`, `GET /issues/{name}`, `GET /history/{issue_id}`, and `GET /issues?severity=&statuses=`. All read tools attempt MCP first (3 s timeout) and fall back to direct PostgreSQL on failure. The `via` field in `tool_call` log events shows `"mcp"`, `"cache"`, or `"direct_db_fallback"` per request. See `docs/architecture.md` for the full routing diagram.

---

## Evaluation

```bash
# Install eval dependencies (one-time)
pip install -r evals/requirements.txt

# Run from the project root
python evals/runner.py
```

Results are written to `evals/reports/results.json`. Expected: **14/14 tool_match, 14/14 status_match, 14/14 grounded**.

---

## Observability

Every request emits structured JSON logs to stdout:

- `agent_output` — agent stage (`planning_agent` / `risk_action_agent` / `response_agent`), `trace_id`, key outputs
- `tool_call` — tool name, `via` (`mcp` / `cache` / `direct_db_fallback`), latency
- `request_trace` — path, method, elapsed_ms
- `timing` — function-level latency (via `@timed` decorator)

Example (single request, trace_id threads all 3 agent stages):
```json
{"ts":"2026-06-25T13:13:38","kind":"agent_output","payload":{"agent_stage":"planning_agent","trace_id":"cbcc32f7","planner_mode":"llm","selected_tools":["get_customer_profile","get_open_issues"]}}
{"ts":"2026-06-25T13:13:38","kind":"tool_call","payload":{"tool":"get_customer_profile","via":"mcp","customer_name":"Pinnacle Bancorp"}}
{"ts":"2026-06-25T13:13:38","kind":"agent_output","payload":{"agent_stage":"risk_action_agent","trace_id":"cbcc32f7","primary_issue_id":1,"risk_level":"Critical","urgency":"immediate"}}
{"ts":"2026-06-25T13:13:41","kind":"agent_output","payload":{"agent_stage":"response_agent","trace_id":"cbcc32f7","via":"llm","model":"gpt-4.1-mini"}}
```

View live: `docker compose logs -f app`

---

## Known limitations

| Item | Status | Mitigation |
|---|---|---|
| MCP tool execution bypass | Deliberate prototype trade-off | Documented in `docs/architecture.md` |
| LLM planner requires external API key | By design | Rule-based fallback covers all demo queries |
| Keycloak `service_started` dependency (not `service_healthy`) | Low risk in practice | App calls Keycloak lazily; local header mode works immediately |
| TLS is self-signed (browser warning) | Addressed locally | Prod: use CA-signed cert or Let's Encrypt |
| `alice.sales` blocked on next-action queries | Correct RBAC enforcement | Use `bob.support` or `carol.admin` for full-plan demos |

---

## AI tool usage

See [`docs/ai-usage-notes.md`](docs/ai-usage-notes.md) for a full account of:
- how AI tooling was used
- bugs found during validation (including two runtime bugs and one test design bug)
- hallucinations corrected
- validation methodology

---

## Additional documentation

| Document | Purpose |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System diagram with trust boundaries, RBAC matrix, Redis key patterns, MCP trade-off |
| [`docs/SECURITY.md`](docs/SECURITY.md) | JWT validation, RBAC, SQL injection prevention, log redaction, known limitations |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | 15-minute panel walkthrough with exact commands |
| [`docs/INTERVIEW_EVIDENCE.md`](docs/INTERVIEW_EVIDENCE.md) | Requirements coverage table, design decisions, 10 talking points, trade-offs |
| [`docs/ai-usage-notes.md`](docs/ai-usage-notes.md) | AI tool usage, bugs found and corrected, validation methodology |
