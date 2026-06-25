import httpx
from core.config import MCP_SERVER_URL
from repositories.customer_repo import get_customer_by_name, resolve_customer_name
from repositories.issue_repo import get_open_issues_for_customer, get_issue_history, create_next_action
from services.memory_service import get_cached_customer_profile, cache_customer_profile
from observability.logging_utils import log_event


def _mcp_get(path: str):
    """
    Call the MCP server. Returns the parsed JSON dict/list on success,
    or None if MCP is unavailable (timeout, connection error, non-200 status).
    Never raises — callers always fall back to direct DB on None.
    """
    try:
        with httpx.Client(timeout=3.0) as client:
            r = client.get(f'{MCP_SERVER_URL}{path}')
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


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


def tool_get_open_issues(customer_name: str):
    # Resolve fuzzy/partial name to canonical DB name
    canonical = resolve_customer_name(customer_name)
    if canonical != customer_name:
        log_event('tool_call', {'tool': 'get_open_issues', 'name_resolved': True,
                                'input': customer_name, 'resolved': canonical})

    mcp_result = _mcp_get(f'/issues/{canonical}')
    if mcp_result is not None:
        issues = mcp_result.get('issues', [])
        via = 'mcp'
    else:
        issues = get_open_issues_for_customer(canonical)
        via = 'direct_db_fallback'

    log_event('tool_call', {'tool': 'get_open_issues', 'via': via, 'customer_name': canonical})
    return issues


def tool_get_issue_history(issue_id: int):
    log_event('tool_call', {'tool': 'get_issue_history', 'via': 'direct_db', 'issue_id': issue_id})
    return get_issue_history(issue_id)


def tool_list_all_open_issues(severity: str = None, statuses: list = None):
    from repositories.issue_repo import get_all_issues_filtered
    effective_statuses = statuses if statuses else ['open', 'in_progress']
    log_event('tool_call', {'tool': 'list_all_open_issues', 'via': 'direct_db', 'severity': severity, 'statuses': effective_statuses})
    return get_all_issues_filtered(statuses=effective_statuses, severity=severity)


def tool_recommend_next_action(issue_id: int, username: str):
    action_text = 'Validate mapping rules, confirm impact, and send customer update by end of next business day.'
    log_event('tool_call', {'tool': 'recommend_next_action', 'via': 'direct_db', 'issue_id': issue_id, 'owner': username})
    return create_next_action(issue_id, action_text, username)
