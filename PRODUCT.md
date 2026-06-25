# Product

## Register

product

## Users

Sales and support staff — account managers and customer support reps who open Atlas during client calls, triage sessions, or escalation reviews. They need fast, grounded answers about customer health and open issues without digging through multiple systems. Secondary audience: ops/eng leads who review observability traces and eval results.

## Product Purpose

Atlas is an agentic customer operations assistant. It accepts natural-language queries, reasons over Postgres data via MCP-connected tools, enforces RBAC on every action, and returns auditable answers grounded in real data. The interface makes the agent's reasoning transparent (expandable traces, grounded citations, escalation skill cards) so users trust the output. Success: a support rep gets a grounded answer about a customer escalation in under 10 seconds, with evidence they can act on.

## Brand Personality

Intelligent · Clear · Calm. The tool should feel like a senior colleague who always has the right answer ready — confident without being loud, structured without being cold. Every screen should reduce cognitive load, not add to it.

## Anti-references

- **Generic SaaS dashboard**: No navy sidebars, blue primary buttons, or chart-heavy layout that looks like Salesforce or HubSpot.
- **Chatbot consumer app**: No bubble chat UI, rounded-everything aesthetic, pastel palette, or anything that reads as a support widget or consumer AI product.

## Design Principles

1. **Trust through transparency** — The agent's reasoning (tool calls, citations, skill outputs) is always one click away, never hidden. Grounded answers show their sources.
2. **Density earns its place** — Show information at the density the task requires. Data tables are dense by design; empty states teach, not apologize.
3. **Role-awareness is visible** — RBAC constraints are communicated clearly in the UI, not surfaced as surprise errors. Users always know what they can and cannot do.
4. **The tool disappears into the task** — No decorative motion, no gratuitous color, no invented affordances. The interface recedes so the answer is the focus.
5. **Calm authority** — Charcoal + yellow accent conveys capability without aggression. Reserve emphasis for what matters: risk levels, RBAC denials, escalation flags.

## Accessibility & Inclusion

WCAG 2.1 AA. Priority areas: color contrast on muted text (especially #9A9AA6 on #F4F4F7), keyboard navigation through the chat composer and sidebar, screen-reader labels on icon-only buttons, and reduced-motion alternatives for any transitions added.
