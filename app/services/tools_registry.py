from services.tools import (
    tool_get_customer_profile,
    tool_get_open_issues,
    tool_get_issue_history,
    tool_recommend_next_action,
    tool_list_all_open_issues,
)

# Single source-of-truth tool map used by the orchestrator.
# Adding a new tool means adding it here; the orchestrator dispatch loop
# picks it up automatically.
TOOL_MAP = {
    'list_all_open_issues':  tool_list_all_open_issues,
    'get_customer_profile':  tool_get_customer_profile,
    'get_open_issues':       tool_get_open_issues,
    'get_issue_history':     tool_get_issue_history,
    'recommend_next_action': tool_recommend_next_action,
}
