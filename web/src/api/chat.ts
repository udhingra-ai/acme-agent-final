import { apiFetch, getToken } from './client'
import type { QueryResponse, QueryStep, QueryPlan } from '../types'

export async function sendQuery(user_query: string, session_id = 'atlas-session'): Promise<QueryResponse> {
  return apiFetch('/query', {
    method: 'POST',
    body: JSON.stringify({ user_query, session_id }),
  })
}

export type StreamEvent =
  | { type: 'planning'; plan: QueryPlan; trace_id: string }
  | { type: 'tool_result'; step: QueryStep }
  | { type: 'risk_action'; step: QueryStep }
  | { type: 'token'; delta: string }
  | { type: 'answer'; text: string }
  | { type: 'error'; status: number; detail: string }
  | { type: 'done'; trace_id: string; user: { username: string; roles: string[]; auth_mode: string } }
  | { type: 'react_thought'; thought: string; next_tool: string; iteration: number }
  | { type: 'disambiguation'; matches: string[]; original_query: string }

export async function sendQueryStream(
  user_query: string,
  session_id: string,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
  confirmed_customer = '',
): Promise<void> {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch('/query/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({ user_query, session_id, confirmed_customer }),
    signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw Object.assign(new Error(err.detail || res.statusText), { status: res.status })
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const parts = buf.split('\n\n')
    buf = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trim()
      if (line.startsWith('data: ')) {
        try { onEvent(JSON.parse(line.slice(6))) } catch { /* malformed chunk */ }
      }
    }
  }
}
