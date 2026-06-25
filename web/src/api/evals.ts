import { apiFetch, getToken } from './client'
import type { EvalResult, EvalSummary } from '../types'

export async function fetchEvals(): Promise<{ summary: EvalSummary; results: EvalResult[] }> {
  return apiFetch('/evals')
}

export async function runEvalsStream(
  onResult: (row: EvalResult, idx: number, total: number) => void,
  onSummary: (summary: EvalSummary) => void,
): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch('/evals/run', { method: 'POST', headers })
  if (!res.ok || !res.body) throw new Error('Eval run failed')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const ev = JSON.parse(line.slice(6))
        if (ev.type === 'result') onResult(ev.row as EvalResult, ev.idx, ev.total)
        else if (ev.type === 'summary') onSummary(ev.summary as EvalSummary)
      } catch { /* malformed chunk, skip */ }
    }
  }
}
