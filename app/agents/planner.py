import json
import re
from typing import Any, Dict, List

from core.config import OPENAI_API_KEY, OPENAI_MODEL

TOOL_DESCRIPTIONS = {
    'list_all_open_issues':   'List issues across ALL customers. Args: severity (optional: critical/high/medium/low), statuses (optional list: open/in_progress/resolved/waiting — defaults to [open, in_progress]). USE THIS whenever no specific customer is named.',
    'get_customer_profile':   'Get the profile for ONE named customer. Args: customer_name (string).',
    'get_open_issues':        'Get all open issues for ONE named customer. Args: customer_name (string).',
    'get_issue_history':      'Get update history for a specific issue. Args: issue_id (int). Requires get_open_issues first.',
    'recommend_next_action':  'Create a next action for a specific issue. Args: issue_id (int). Requires get_open_issues first.',
    'semantic_search_issues': 'Find issues by concept/phrase using semantic vector similarity (RAG). Args: query (string). Use for conceptual queries like "issues similar to rate limiting problems" or "find API timeout issues" when no specific customer is named.',
}

SYSTEM_PROMPT = """Core planning engine for an enterprise operations assistant (Atlas).
Given a user query and available tools, return ONLY valid JSON with keys: customer_name (string), reasoning (string), steps (array).
Each step: {"tool": "<name>", "args": {...}} or {"tool": "<name>", "args_from": "<source>"}.

AVAILABLE TOOLS:
- list_all_open_issues(severity?, statuses?): portfolio-wide issue list
- get_customer_profile(customer_name): single-client profile
- get_open_issues(customer_name): single-client open issues
- get_issue_history: history for one issue (needs issue_id)
- recommend_next_action: create next action (needs issue_id, admin/support only)
- semantic_search_issues(query): find issues by concept/phrase using vector similarity — use for conceptual queries like "find issues related to X", "issues mentioning Y", "similar to Z"

DECISION RULES — follow strictly:

RULE 1 — Semantic/conceptual query (no customer name, searching by concept) → use semantic_search_issues
  If the user asks to "find", "search", or asks about issues "related to", "similar to", or "mentioning" a concept
  without naming a specific customer, use semantic_search_issues.
  Set customer_name = "".
  Examples: "find issues related to rate limiting", "search for timeout issues", "issues mentioning SWIFT",
            "find issues similar to authentication problems".

RULE 2 — No named client, portfolio view → use list_all_open_issues
  If the user asks for a cross-customer list, filtering by status/severity, or portfolio-wide view.
  Set customer_name = "".
  Examples: "all issues", "critical issues", "what's in progress", "which clients are at risk".

RULE 3 — Status filtering
  Map user language to statuses array:
  "in progress" / "being worked on" → ["in_progress"]
  "closed" / "resolved" / "done" → ["resolved"]
  "waiting" / "on hold" → ["waiting"]
  "open" → ["open"]
  "all" / "any" / not specified → omit statuses (defaults to open + in_progress)

RULE 4 — Named client → use per-client tools in this order
  If user names a specific client (e.g. "Pinnacle Bancorp", "Nexus Payments"):
  Step 1: ALWAYS call get_customer_profile first.
  Step 2: Add get_open_issues if the query is about issues, status, summary, or open work.
  Step 3: Add get_issue_history if the query includes "status", "summary", "summarise", "summarize", "latest", "update", "history" — these words mean the user wants to know what has happened recently.
  Step 4: Add recommend_next_action ONLY if the user explicitly asks to suggest/create/recommend an action.

RULE 5 — Never invent tool names. Never call get_customer_profile with an empty name.

EXAMPLES:
Q: "find issues related to rate limiting or API throttling"
→ {customer_name:"", steps:[{tool:"semantic_search_issues", args:{query:"rate limiting API throttling"}}]}

Q: "list all critical issues across all clients"
→ {customer_name:"", steps:[{tool:"list_all_open_issues", args:{severity:"critical"}}]}

Q: "summarise the latest status for Nexus Payments Ltd"
→ {customer_name:"Nexus Payments Ltd", steps:[{tool:"get_customer_profile",args:{customer_name:"Nexus Payments Ltd"}},{tool:"get_open_issues",args:{customer_name:"Nexus Payments Ltd"}},{tool:"get_issue_history",args_from:"first_issue_id"}]}

Q: "what is the latest status for Pinnacle Bancorp"
→ {customer_name:"Pinnacle Bancorp", steps:[{tool:"get_customer_profile",args:{customer_name:"Pinnacle Bancorp"}},{tool:"get_open_issues",args:{customer_name:"Pinnacle Bancorp"}},{tool:"get_issue_history",args_from:"first_issue_id"}]}

Q: "which clients have high severity open issues"
→ {customer_name:"", steps:[{tool:"list_all_open_issues", args:{severity:"high", statuses:["open"]}}]}
"""

_SEMANTIC_SEARCH_KEYWORDS = [
    'find issues related to', 'find issues mentioning', 'issues similar to',
    'issues related to', 'search for issues', 'find issues about',
    'issues mentioning', 'similar to', 'related to',
]

_CROSS_CUSTOMER_KEYWORDS = [
    'all clients', 'all customers', 'all accounts', 'across all', 'across clients',
    'every client', 'every customer', 'portfolio', 'full portfolio', 'overall',
    'in progress', 'in-progress', 'resolved', 'closed', 'waiting', 'on hold',
]

_STATUS_MAP = {
    'in progress': 'in_progress', 'in-progress': 'in_progress', 'being worked': 'in_progress',
    'resolved': 'resolved', 'closed': 'resolved', 'done': 'resolved', 'completed': 'resolved',
    'waiting': 'waiting', 'on hold': 'waiting',
    'open': 'open',
}


def _is_cross_customer(query: str) -> bool:
    lowered = query.lower()
    return any(kw in lowered for kw in _CROSS_CUSTOMER_KEYWORDS)


def _infer_severity(query: str):
    lowered = query.lower()
    for sev in ('critical', 'high', 'medium', 'low'):
        if sev in lowered:
            return sev
    return None


def _infer_statuses(query: str):
    lowered = query.lower()
    found = []
    for phrase, status in _STATUS_MAP.items():
        if phrase in lowered and status not in found:
            found.append(status)
    return found if found else None


def infer_customer_name(user_query: str) -> str:
    name_pattern = r'[A-Z][A-Za-z0-9&\'-]*(?:\s+[A-Z][A-Za-z0-9&\'-]*)*'
    patterns = [
        r'for\s+(' + name_pattern + r')',
        r'on\s+(' + name_pattern + r')',
        r'about\s+(' + name_pattern + r')',
        r'regarding\s+(' + name_pattern + r')',
        r'customer\s+(' + name_pattern + r')',
        r'client\s+(' + name_pattern + r')',
        r'of\s+(' + name_pattern + r')',
        r'at\s+(' + name_pattern + r')',
    ]
    stop_words = {'all', 'every', 'any', 'each', 'my', 'the', 'our', 'your', 'this', 'that', 'risk'}
    for pattern in patterns:
        m = re.search(pattern, user_query)
        if m:
            name = m.group(1).strip().rstrip('?.!,')
            if name.lower() not in stop_words:
                return name
    return ''


def _is_semantic_query(query: str) -> bool:
    lowered = query.lower()
    return any(kw in lowered for kw in _SEMANTIC_SEARCH_KEYWORDS)


def build_rule_plan(user_query: str, user_roles: List[str]) -> Dict[str, Any]:
    lowered = user_query.lower()
    customer_name = infer_customer_name(user_query)

    # Semantic search takes priority when the query is a conceptual search without a named customer
    if _is_semantic_query(user_query) and not customer_name:
        return {
            'customer_name': '',
            'reasoning': 'Conceptual search query — routing to semantic vector search.',
            'steps': [{'tool': 'semantic_search_issues', 'args': {'query': user_query}}],
            'available_tools': TOOL_DESCRIPTIONS,
            'planner_mode': 'rule_fallback',
            'roles_seen': user_roles,
        }

    if _is_cross_customer(user_query) or not customer_name:
        severity = _infer_severity(user_query)
        statuses = _infer_statuses(user_query)
        args: dict = {}
        if severity:
            args['severity'] = severity
        if statuses:
            args['statuses'] = statuses
        return {
            'customer_name': '',
            'reasoning': 'Cross-customer or no-customer query — listing issues across all clients.',
            'steps': [{'tool': 'list_all_open_issues', 'args': args}],
            'available_tools': TOOL_DESCRIPTIONS,
            'planner_mode': 'rule_fallback',
            'roles_seen': user_roles,
        }

    steps = [{'tool': 'get_customer_profile', 'args': {'customer_name': customer_name}}]
    if any(t in lowered for t in ['issue', 'status', 'summary', 'summarise', 'summarize', 'next action', 'open', 'progress', 'history']):
        steps.append({'tool': 'get_open_issues', 'args': {'customer_name': customer_name}})
    if any(t in lowered for t in ['history', 'status', 'summary', 'summarise', 'summarize', 'latest', 'update']):
        steps.append({'tool': 'get_issue_history', 'args_from': 'first_issue_id'})
    if any(t in lowered for t in ['next action', 'suggest', 'recommend', 'create action']):
        steps.append({'tool': 'recommend_next_action', 'args_from': 'first_issue_id_and_user'})

    return {
        'customer_name': customer_name,
        'reasoning': 'Deterministic local fallback planner.',
        'steps': steps,
        'available_tools': TOOL_DESCRIPTIONS,
        'planner_mode': 'rule_fallback',
        'roles_seen': user_roles,
    }


def _safe_json_loads(text: str):
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```\w*\n?', '', text)
        text = text.rstrip('`').strip()
    return json.loads(text)


def build_llm_plan(user_query: str, user_roles: List[str]) -> Dict[str, Any]:
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'replace_me':
        raise RuntimeError('OPENAI_API_KEY not configured')
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, max_retries=3)
    # Don't pass user_roles to the LLM — RBAC is enforced by the orchestrator,
    # not the planner. Passing roles here causes the LLM to silently filter tools
    # that it shouldn't be making access decisions about.
    prompt = {
        'query': user_query,
        'inferred_customer_name': infer_customer_name(user_query),
        'is_cross_customer': _is_cross_customer(user_query),
    }
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt)}
        ]
    )
    data = _safe_json_loads(resp.choices[0].message.content)
    data['available_tools'] = TOOL_DESCRIPTIONS
    data['planner_mode'] = 'llm'
    data['roles_seen'] = user_roles
    if 'customer_name' not in data:
        data['customer_name'] = infer_customer_name(user_query)

    # Override LLM plan if the query is clearly cross-customer, or if the LLM
    # hallucinated a customer name that doesn't actually appear in the query.
    llm_customer = data.get('customer_name', '')
    query_lower = user_query.lower()
    hallucinated = llm_customer and llm_customer.lower() not in query_lower
    if _is_cross_customer(user_query) or (hallucinated and not infer_customer_name(user_query)):
        severity = _infer_severity(user_query)
        statuses = _infer_statuses(user_query)
        args: dict = {}
        if severity:
            args['severity'] = severity
        if statuses:
            args['statuses'] = statuses
        data['steps'] = [{'tool': 'list_all_open_issues', 'args': args}]
        data['customer_name'] = ''

    return data


def build_plan(user_query: str, user_roles: List[str]) -> Dict[str, Any]:
    try:
        return build_llm_plan(user_query, user_roles)
    except Exception:
        return build_rule_plan(user_query, user_roles)


def serialize_plan(plan: Dict[str, Any]) -> str:
    return json.dumps(plan, indent=2)
