from __future__ import annotations

import httpx
from core.config import MCP_SERVER_URL, MCP_SECRET
from repositories.customer_repo import (
    get_customer_by_name, resolve_customer_name, get_allowed_customer_names,
)
from repositories.issue_repo import (
    get_open_issues_for_customer, get_issue_history, create_next_action, get_issue_by_id,
)
from services.memory_service import get_cached_customer_profile, cache_customer_profile
from observability.logging_utils import log_event, timed


def _apply_rls_to_issues(issues: list, user_ctx: dict | None) -> list:
    """Filter issue list by allowed customers when user_ctx requires RLS."""
    if not user_ctx:
        return issues
    allowed = get_allowed_customer_names(user_ctx)
    if allowed is None:
        return issues  # unrestricted role
    return [i for i in issues if i.get('customer_name') in allowed]


def _mcp_get(path: str):
    """
    Call the MCP server. Returns the parsed JSON dict/list on success,
    or None if MCP is unavailable (timeout, connection error, non-200 status).
    Never raises — callers always fall back to direct DB on None.
    Sends X-MCP-Secret if configured so MCP can reject unauthenticated callers.
    """
    try:
        headers = {}
        if MCP_SECRET:
            headers['X-MCP-Secret'] = MCP_SECRET
        with httpx.Client(timeout=3.0) as client:
            r = client.get(f'{MCP_SERVER_URL}{path}', headers=headers)
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


@timed
def tool_get_customer_profile(customer_name: str):
    # Resolve fuzzy/partial name to canonical DB name before any lookup
    canonical = resolve_customer_name(customer_name)
    if canonical != customer_name:
        log_event('tool_call', {'tool': 'get_customer_profile', 'name_resolved': True,
                                'input': customer_name, 'resolved': canonical})

    # Redis cache — fastest path, no network hop
    cached = get_cached_customer_profile(canonical)
    if cached:
        log_event('tool_call', {'tool': 'get_customer_profile', 'via': 'cache', 'cached': True, 'customer_name': canonical})
        return cached

    # Route through MCP execution endpoint
    mcp_result = _mcp_get(f'/customer/{canonical}')
    if mcp_result is not None:
        data = mcp_result if mcp_result else None
        via = 'mcp'
    else:
        data = get_customer_by_name(canonical)
        via = 'direct_db_fallback'

    if data:
        cache_customer_profile(canonical, data)

    log_event('tool_call', {'tool': 'get_customer_profile', 'via': via, 'cached': False, 'customer_name': canonical})
    return data or None


@timed
def tool_get_open_issues(customer_name: str, user_ctx: dict = None):
    # Resolve fuzzy/partial name to canonical DB name
    canonical = resolve_customer_name(customer_name)
    if canonical != customer_name:
        log_event('tool_call', {'tool': 'get_open_issues', 'name_resolved': True,
                                'input': customer_name, 'resolved': canonical})

    mcp_result = _mcp_get(f'/issues/{canonical}')
    if mcp_result is not None:
        issues = mcp_result.get('issues', [])
        issues = _apply_rls_to_issues(issues, user_ctx)  # MCP has no RLS — filter app-side
        via = 'mcp'
    else:
        issues = get_open_issues_for_customer(canonical, user_ctx=user_ctx)
        via = 'direct_db_fallback'

    log_event('tool_call', {'tool': 'get_open_issues', 'via': via, 'customer_name': canonical})
    return issues


@timed
def tool_get_issue_history(issue_id: int):
    mcp_result = _mcp_get(f'/history/{issue_id}')
    if mcp_result is not None:
        history = mcp_result.get('history', [])
        via = 'mcp'
    else:
        history = get_issue_history(issue_id)
        via = 'direct_db_fallback'
    log_event('tool_call', {'tool': 'get_issue_history', 'via': via, 'issue_id': issue_id})
    return history


@timed
def tool_list_all_open_issues(severity: str = None, statuses: list = None,
                               user_ctx: dict = None):
    from repositories.issue_repo import get_all_issues_filtered
    effective_statuses = statuses if statuses else ['open', 'in_progress']

    qs_parts = ['statuses=' + ','.join(effective_statuses)]
    if severity:
        qs_parts.append(f'severity={severity}')
    mcp_result = _mcp_get(f'/issues?{"&".join(qs_parts)}')

    if mcp_result is not None:
        issues = mcp_result.get('issues', [])
        issues = _apply_rls_to_issues(issues, user_ctx)  # MCP has no RLS — filter app-side
        via = 'mcp'
    else:
        issues = get_all_issues_filtered(statuses=effective_statuses, severity=severity,
                                         user_ctx=user_ctx)
        via = 'direct_db_fallback'

    log_event('tool_call', {'tool': 'list_all_open_issues', 'via': via, 'severity': severity, 'statuses': effective_statuses})
    return issues


@timed
def tool_semantic_search_issues(query: str, user_ctx: dict = None):
    """Find issues semantically similar to a concept/phrase (RAG path)."""
    from services.embedding_service import get_embedding
    from repositories.issue_repo import semantic_search_issues
    embedding = get_embedding(query)
    if not embedding:
        return {'results': [], 'note': 'Semantic search requires OPENAI_API_KEY'}
    results = semantic_search_issues(embedding, user_ctx=user_ctx)
    log_event('tool_call', {'tool': 'semantic_search_issues', 'query': query, 'results_count': len(results)})
    return results


def _build_action_text(issue: dict) -> str:
    """Generate a contextual next-action recommendation from issue attributes."""
    severity = (issue.get('severity') or 'high').lower()
    title = issue.get('title') or 'the reported issue'
    customer = issue.get('customer_name') or 'the customer'

    urgency_map = {
        'critical': 'immediately',
        'high': 'within 24 hours',
        'medium': 'within 48 hours',
        'low': 'by end of next business day',
    }
    urgency = urgency_map.get(severity, 'by end of next business day')

    return (
        f'Escalate "{title}" for {customer} to the relevant team {urgency}. '
        f'Confirm scope of impact, coordinate a fix, and send the customer a status update once resolution is underway.'
    )


@timed
def tool_recommend_next_action(issue_id: int, username: str):
    issue = get_issue_by_id(issue_id)
    action_text = _build_action_text(issue) if issue else (
        'Review the open issue, coordinate with the relevant team, '
        'and provide the customer with a status update by end of next business day.'
    )
    log_event('tool_call', {'tool': 'recommend_next_action', 'via': 'direct_db',
                            'issue_id': issue_id, 'owner': username})
    return create_next_action(issue_id, action_text, username)
