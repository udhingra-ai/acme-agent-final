import { apiFetch } from './client'
import type { QueryResponse } from '../types'

export async function sendQuery(user_query: string, session_id = 'atlas-session'): Promise<QueryResponse> {
  return apiFetch('/query', {
    method: 'POST',
    body: JSON.stringify({ user_query, session_id }),
  })
}
