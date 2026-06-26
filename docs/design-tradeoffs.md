# Design Assumptions, Trade-offs & Future Enhancements

This document explains the deliberate decisions made in this pipeline, what was deferred and why, and what a production-grade evolution would look like. Written to support interview discussion of architectural choices.

---

## Current Assumptions (Demo Scope)

| Assumption | Why it holds for demo | What breaks at scale |
|---|---|---|
| Single Keycloak realm, 3 test users | Sufficient to demonstrate RBAC | Production needs user federation, SAML/OIDC integration, role sync |
| All 10 customers owned by `alice.sales` | Simplifies RLS demo | Real org has 100s of AMs; ownership matrix is complex |
| OpenAI as sole LLM provider | Fastest path to working agents | Vendor lock-in; no fallback if OpenAI degrades |
| Embeddings generated on-demand | Acceptable latency at 10 issues | At 1M issues, embedding backfill is a days-long job |
| Single Postgres instance | No HA, no read replicas | SPOF; write-heavy embed updates contend with reads |
| Redis single node | Acceptable for demo | SPOF for cache, rate limiter, session state, distributed lock |
| In-process CDC listener thread | Simplest real-time embed update | Doesn't survive pod restarts; misses events during downtime |
| Synchronous SQLAlchemy | Correct given sequential ReAct loop | Re-evaluate if parallel tool execution expands significantly |
| MCP server on separate port | Clean tool isolation | In production, MCP auth and network policy need hardening |
| No write-through cache invalidation | Cache TTL is 15 min | Stale answers if an issue is updated and queried within TTL |

---

## Why Synchronous SQLAlchemy (not async)

**Decision:** sync SQLAlchemy with connection pool (`pool_size=20`).

**Reasoning:** The ReAct loop is inherently sequential — the LLM decides the next tool based on the previous result. There is no fan-out of independent I/O within a single iteration. DB queries run in under 10ms; LLM calls dominate at 500ms–2s. Making DB async saves ~15ms of blocking time per request while adding a full-codebase rewrite cost.

**When to revisit:** If parallel tool execution expands to 4+ tools per iteration, or if the product adds a reporting path that fires many independent queries concurrently.

**Migration path:** Repository layer is already isolated behind function boundaries. Swapping `SessionLocal` for `AsyncSession` and marking each function `async def` is a contained refactor — roughly 3–5 days. LangGraph supports async node graphs.

---

## Why ThreadPoolExecutor for Parallel Tools (not asyncio.gather)

**Decision:** `concurrent.futures.ThreadPoolExecutor` for parallel tool execution.

**Reasoning:** Each tool call is a blocking sync DB call. asyncio.gather only parallelises coroutines — it would require every tool function to be async. ThreadPoolExecutor runs blocking calls in worker threads, giving true parallel I/O without rewriting the tool layer. Each thread pulls its own connection from the SQLAlchemy pool independently.

**Limitation:** Thread-per-tool adds overhead (~1ms) compared to true coroutine fan-out. Not meaningful at 2–4 tools per batch.

**Gain achieved:** Parallel `get_customer_profile + get_open_issues` eliminates one full LLM iteration (~400ms) per customer query. Measured: 2 LLM round-trips instead of 3.

---

## Why LangGraph ReAct (not a simpler loop)

**Decision:** LangGraph 5-node StateGraph with bounded ReAct loop.

**Reasoning:** LangGraph gives an explicit, inspectable state machine. Every node transition is logged, state is serialisable to Redis for trace recovery, and the graph is testable node-by-node. A hand-rolled while loop would give the same behaviour but with implicit state and no standard tracing hooks.

**Trade-off:** LangGraph adds a dependency (~30MB) and its streaming API has quirks (e.g., `stream_mode='updates'` returns full list state, not diffs). Worth it for the observability and the ability to add conditional branches without restructuring code.

---

## Why Two-Layer Cache (not just Redis)

**Decision:** L1 Redis exact (SHA-256, 15 min TTL) + L2 pgvector semantic (cosine > 0.92).

**Reasoning:** L1 catches exact repeated queries (common in ops teams checking the same dashboard repeatedly). L2 catches paraphrases — "status of Nexus?" and "how is Nexus doing?" return the same cached answer without an LLM call. Without L2, paraphrase variants each pay a full LLM round-trip.

**Limitation:** L2 adds one OpenAI embedding call (~80ms) on every cache miss. At very high QPS, this embed call becomes a bottleneck. Mitigation: batch embed calls or use a cheaper local embedding model for cache lookup.

**Gap:** No cache invalidation on write. If `update_issue_status` changes an issue's state, cached answers about that issue remain stale for up to 15 minutes. Fix: on any write tool execution, delete cache entries whose `customer_name` matches the updated record.

---

## Why pg_trgm for Customer Disambiguation (not a vector search)

**Decision:** Three-tier fuzzy match: exact ILIKE → word-level ILIKE → pg_trgm trigram similarity.

**Reasoning:** Trigram similarity is deterministic and fast (<5ms with GIN index). It handles abbreviations ("nexi" → "Nexus Payments Ltd"), typos, and partial names without an LLM call or embedding. Vector search would add 80ms+ of embedding latency for a lookup that has a correct answer — the canonical customer name — not a semantic similarity problem.

**Limitation:** Trigram struggles with acronyms that share no character trigrams with the full name (e.g., "GS" → "Goldman Sachs"). Fix: add an aliases table with known abbreviations, searched first before trigram.

---

## Gaps and Future Enhancements

### 1. Async Database Engine
- **Gap:** Sync SQLAlchemy blocks a thread per in-flight query.
- **Benefit:** One event loop thread can service many concurrent requests; reduces thread overhead at 500+ concurrent users.
- **Risk:** Full rewrite of repository layer + LangGraph nodes + tests. ~3–5 days.
- **Trigger:** Profile under load; migrate when connection wait time appears in traces.

### 2. Cache Invalidation on Write
- **Gap:** Write tools (`update_issue_status`, `recommend_next_action`) don't invalidate cache.
- **Benefit:** Eliminates stale answers immediately after a status update.
- **Risk:** Low. Add a cache key pattern delete after each write tool audit event.
- **Effort:** ~2 hours.

### 3. Customer Aliases Table
- **Gap:** Trigram fails on acronyms ("GS", "JPM", "HSBC").
- **Benefit:** Correct disambiguation for all real-world client name variants.
- **Risk:** Low. New table, no schema changes.
- **Effort:** ~1 day including seed data.

### 4. Durable CDC (Kafka/Debezium) vs In-Process Listener
- **Gap:** Current CDC listener is a background thread. It misses events during pod restarts and doesn't survive horizontal scaling (multiple pods each try to listen).
- **Benefit:** Kafka/Debezium gives durable event log, at-least-once delivery, and consumer group semantics so only one pod processes each event.
- **Risk:** High operational complexity. Adds Kafka to the stack.
- **Trigger:** When embedding freshness SLA is tighter than "within one pod restart cycle".

### 5. Read Replica for Analytics Queries
- **Gap:** `list_all_open_issues` and autonomous health sweep run on the primary DB, competing with write traffic.
- **Benefit:** Analytics queries don't impact write latency.
- **Risk:** Read replica lag means slightly stale reads (acceptable for ops dashboards).
- **Effort:** Config change in `DATABASE_URL`; route read-only queries to replica URL.

### 6. LLM Provider Abstraction
- **Gap:** OpenAI is hardcoded throughout (`OPENAI_MODEL`, `openai.OpenAI()`).
- **Benefit:** Swap to Anthropic, Azure OpenAI, or a local model (Ollama) without touching agent logic.
- **Risk:** Low. Wrap in a `LLMClient` interface; each provider is an implementation.
- **Effort:** ~1 day.

### 7. Structured Logging + Distributed Tracing
- **Gap:** `log_event` writes JSON to stdout. No trace correlation across pods.
- **Benefit:** Full request trace from HTTP ingress → LangGraph nodes → tool calls → LLM → response, searchable in Datadog/Grafana.
- **Risk:** Low. Add OpenTelemetry spans; `trace_id` is already threaded through the pipeline.
- **Effort:** ~1 day.

### 8. HNSW Index Rebuild Concurrently
- **Gap:** CDC listener rebuilds the HNSW index synchronously after N new embeddings. Blocks the thread for minutes at large scale.
- **Benefit:** Zero-downtime index rebuild; semantic search stays available during rebuild.
- **Fix:** Use `CREATE INDEX CONCURRENTLY` and run in a background thread outside the CDC callback.
- **Risk:** Low. Targeted change in `cdc_listener.py`.

### 9. Parallel Tool Execution — Expanded
- **Current:** `get_customer_profile + get_open_issues` run in parallel via ThreadPoolExecutor.
- **Future:** Expand to `get_issue_history` for multiple issues simultaneously (one call per issue ID). LLM returns `[{tool: get_issue_history, args: {issue_id: 1}}, {tool: get_issue_history, args: {issue_id: 2}}]`.
- **Gain:** Reduces history fetch from N sequential calls to 1 parallel batch.
- **Risk:** Low. `_run_single_tool` already handles arbitrary args; LLM prompt needs one new example.

---

## What We Explicitly Did Not Do (and Why)

| Not done | Reason |
|---|---|
| Async SQLAlchemy | Bottleneck is LLM latency, not DB I/O; rewrite cost exceeds benefit at demo scale |
| Kafka/Debezium CDC | Operational complexity not justified for demo; in-process listener is demonstrably correct |
| Multi-region Postgres | HA is an ops concern, not an architecture concern at this stage |
| Fine-tuned LLM | Prompt engineering + few-shot examples achieves required accuracy; fine-tuning adds training infrastructure |
| GraphQL API | REST + SSE covers all client needs; GraphQL adds schema maintenance overhead with no client benefit here |
| Service mesh (Istio) | mTLS and traffic management are deployment concerns; application-level auth (JWT + RBAC) is sufficient |
