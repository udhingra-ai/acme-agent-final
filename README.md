# Atlas — Agentic Operations Assistant

A production-pattern agentic assistant for enterprise operations teams.

---

## Requirements coverage

| Brief requirement | Implementation | Evidence | How to verify |
|---|---|---|---|
| Keycloak authentication | JWT bearer token flow; realm import at startup | `keycloak/realm-export.json`, `app/auth/security.py` | `curl POST /auth/token` |
| Role-based access control | Server-side `require_role()` in orchestrator | `app/agents/orchestrator.py:42` | `sales_user` + write query → 403 |
| Dynamic LLM tool use | OpenAI planner + rule-based fallback | `app/agents/planner.py` | `planner_mode` field in response |
| PostgreSQL | 5 tables, parameterised queries, seed data | `db/init/`, `app/repositories/` | `docker exec acme-postgres psql …` |
| Redis | Session history (1 h TTL) + profile cache (15 min TTL) | `app/services/memory_service.py` | `docker exec acme-redis redis-cli KEYS "*"` |
| MCP server | Tool registry at `:8100/tools`; customer lookup endpoint | `mcp_server/server.py` | `curl http://localhost:8100/tools` |
| Reusable Skill | Customer Escalation Skill — deterministic risk rubric | `app/skills/customer_escalation.py` | `steps[].skill` in `/query` response |
| Docker Compose | Single command; 5 services | `docker-compose.yml` | `docker compose ps` |
| Evaluation | 10 test cases; tool_match, status_match, grounded, latency | `evals/` | `python evals/runner.py` |
| Observability | Structured JSON: tool_call, request_trace, timing | `app/observability/` | `docker compose logs -f app` |

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

**Short summary:**

```
User → nginx :443 (TLS) → FastAPI app :8000 → JWT validation + RBAC
                                             → LLM Planner (OpenAI or rule fallback)
                                             → Tool Orchestrator
                                                 → get_customer_profile  (Redis cache → MCP :8100 → DB fallback)
                                                 → get_open_issues       (MCP :8100 → DB fallback)
                                                 → get_issue_history     (→ PostgreSQL direct)
                                                 → recommend_next_action (→ PostgreSQL, role-gated)
                                             → Customer Escalation Skill (stateless)
                                             → Redis session + cache write
```

6 services: nginx (TLS), app, postgres, redis, keycloak, mcp-server.

### MCP server

The MCP server at `:8100` exposes the canonical tool registry (`GET /tools`), customer lookup (`GET /customer/{name}`), and open issues (`GET /issues/{name}`). `get_customer_profile` and `get_open_issues` execute through MCP with a 3 s timeout and automatic direct-DB fallback. The `via` field in `tool_call` log events shows `"mcp"`, `"cache"`, or `"direct_db_fallback"` per request. See `docs/architecture.md` for the full routing diagram.

---

## Evaluation

```bash
# Install eval dependencies (one-time)
pip install -r evals/requirements.txt

# Run from the project root
python evals/runner.py
```

Results are written to `evals/reports/results.json`. Expected: **10/10 tool_match, 10/10 status_match, 10/10 grounded**.

---

## Observability

Every request emits structured JSON logs to stdout:

- `request_trace` — path, method, trace_id, elapsed_ms
- `tool_call` — tool name, arguments, cache hit/miss
- `timing` — function-level latency (via `@timed` decorator)

Example:
```json
{"ts":"2026-06-22T09:31:20","kind":"tool_call","payload":{"tool":"get_customer_profile","cached":true,"customer_name":"Pinnacle Bancorp"}}
{"ts":"2026-06-22T09:31:20","kind":"request_trace","payload":{"path":"/query","method":"POST","trace_id":"...","elapsed_ms":178}}
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
