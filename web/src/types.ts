export type Role = 'sales_user' | 'support_user' | 'admin'
export type View = 'assistant' | 'customers' | 'issues' | 'observability' | 'evals' | 'architecture'
export type HealthStatus = 'green' | 'amber' | 'red'
export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'

export interface AuthUser {
  username: string
  displayName: string
  first: string
  initials: string
  role: Role
  token: string
}

export interface Customer {
  id: number
  name: string
  segment: string
  account_owner: string
  health_status: HealthStatus
  open_issues: number
}

export interface Issue {
  id: number
  title: string
  severity: Severity
  status: string
  created_at: string
  customer_name: string
  customer_id: number
}

export interface IssueUpdate {
  issue_id: number
  update_text: string
  updated_by: string
  created_at: string
}

export interface NextAction {
  id: number
  issue_id: number
  action_text: string
  owner: string
  due_date: string
  status: string
  created_at: string
}

export interface IssueDetail {
  history: IssueUpdate[]
  next_actions: NextAction[]
}

export interface SkillOutput {
  customer_name: string
  executive_summary: string
  customer_health: string
  risk_level: RiskLevel
  risk_rationale: string
  urgency: string
  recommended_next_action: string
  owner_suggestion: string
  missing_information: string[]
  evidence_used: {
    customer_id: number | null
    issue_ids: number[]
    history_events: number
    sources: string[]
  }
}

export interface QueryStep {
  tool?: string
  skill?: string
  args?: Record<string, unknown>
  output: unknown
}

export interface QueryPlan {
  customer_name: string
  reasoning: string
  steps: Array<{ tool: string; args?: Record<string, unknown> }>
  planner_mode: string
  roles_seen: string[]
}

export interface QueryResponse {
  user: { username: string; roles: string[]; auth_mode: string }
  answer: string
  plan: QueryPlan
  steps: QueryStep[]
  session_context: { history: unknown[] }
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text?: string
  response?: QueryResponse
  loading?: boolean
  traceOpen?: boolean
}

export interface TraceRecord {
  id: string
  ts: string
  user: string
  role: string
  query: string
  tools: Array<{ name: string; ms: number }>
  ms: number
  status: 'ok' | 'warn' | 'error'
  grounded: boolean
  rbac: 'allowed' | 'denied'
  statusCode: number
}

export interface EvalResult {
  id: string
  query: string
  role: string
  expected_tools: string[]
  expect_status: number
  notes: string
  latency_ms: number
  status_code: number
  actual_tools: string[]
  tool_match: boolean
  status_match: boolean
  grounded: boolean
}

export interface EvalSummary {
  total_tests: number
  tool_match_count: number
  status_match_count: number
  grounded_count: number
  total_latency_ms: number
  avg_latency_ms: number
  verdict: string
}
