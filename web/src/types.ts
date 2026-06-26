export type Role = 'sales_user' | 'support_user' | 'admin'
export type View = 'assistant' | 'customers' | 'issues' | 'observability' | 'evals' | 'architecture'

export interface Briefing {
  id: number
  customer_name: string
  account_owner: string
  health_status: string
  open_issues: number
  risk_level: string
  risk_summary: string
  recommended_action: string
  urgency: string
  source: 'health_sweep' | 'escalation_cdc' | 'churn_signal'
  trigger_issue_id?: number
  acknowledged: boolean
  created_at: string
}
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
  rationale: string
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
  selected_primary_issue?: Record<string, unknown>
}

export interface QueryStep {
  tool?: string
  skill?: string
  args?: Record<string, unknown>
  output: unknown
  rls_note?: string
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
  trace_id?: string
}

export type AgentStage = 'planning' | 'tools' | 'risk_action' | 'response' | null

export interface ReactThought {
  thought: string
  next_tool: string
  iteration: number
}

export interface Alert {
  type: 'critical' | 'warning'
  customer_name: string
  segment: string
  open_issues: number
  message: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text?: string
  response?: QueryResponse
  loading?: boolean
  traceOpen?: boolean
  // Streaming state (populated during loading, cleared on done)
  streamingAnswer?: string
  partialSteps?: QueryStep[]
  partialPlan?: QueryPlan
  currentStage?: AgentStage
  // ReAct loop thoughts shown during streaming
  reactThoughts?: ReactThought[]
  // Disambiguation
  disambiguation?: { matches: string[]; original_query: string }
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
