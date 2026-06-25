from services.tools import tool_get_customer_profile, tool_get_open_issues, tool_get_issue_history, tool_recommend_next_action

TOOLS = {
    'get_customer_profile': tool_get_customer_profile,
    'get_open_issues': tool_get_open_issues,
    'get_issue_history': tool_get_issue_history,
    'recommend_next_action': tool_recommend_next_action,
}
