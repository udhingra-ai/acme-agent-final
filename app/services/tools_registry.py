from services.tools import (
    tool_get_customer_profile,
    tool_get_open_issues,
    tool_get_issue_history,
    tool_recommend_next_action,
    tool_list_all_open_issues,
    tool_semantic_search_issues,
    tool_update_issue_status,
    tool_search_customers,
)

# Single source-of-truth tool map used by the orchestrators.
# To add a new tool: (1) implement in tools.py, (2) add here,
# (3) register in _WRITE_TOOL_REGISTRY in graph_orchestrator.py if it mutates data.
TOOL_MAP = {
    'list_all_open_issues':    tool_list_all_open_issues,
    'get_customer_profile':    tool_get_customer_profile,
    'get_open_issues':         tool_get_open_issues,
    'get_issue_history':       tool_get_issue_history,
    'recommend_next_action':   tool_recommend_next_action,
    'semantic_search_issues':  tool_semantic_search_issues,
    'update_issue_status':     tool_update_issue_status,
    'search_customers':        tool_search_customers,
}
