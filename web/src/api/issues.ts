import { apiFetch } from './client'
import type { Issue, IssueDetail } from '../types'

export async function fetchIssues(): Promise<Issue[]> {
  return apiFetch('/issues')
}

export async function fetchIssueDetail(id: number): Promise<IssueDetail> {
  return apiFetch(`/issues/${id}/history`)
}
