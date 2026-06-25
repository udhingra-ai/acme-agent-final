import { useEffect, useState } from 'react'
import { fetchEvals, runEvalsStream } from '../api/evals'
import { fmtMs } from '../utils'
import type { EvalResult, EvalSummary } from '../types'

function Badge({ v }: { v: boolean | 'na' }) {
  if (v === 'na') return <span style={{ width: 22, height: 22, borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 800, color: '#B0B0BA', background: '#F1F1F4' }}>–</span>
  return <span style={{ width: 22, height: 22, borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 800, color: v ? '#1F7A4D' : '#B4232A', background: v ? '#E7F4EC' : '#FBEAEA' }}>{v ? '✓' : '✗'}</span>
}

function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0
  return (
    <div style={{ height: 4, background: '#EDEDF1', borderRadius: 2, overflow: 'hidden', marginTop: 10 }}>
      <div style={{ height: '100%', width: `${pct}%`, background: '#FFE600', borderRadius: 2, transition: 'width .4s ease' }} />
    </div>
  )
}

export default function Evaluations() {
  const [summary, setSummary] = useState<EvalSummary | null>(null)
  const [results, setResults] = useState<EvalResult[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [error, setError] = useState('')
  const [lastRunAt, setLastRunAt] = useState<string | null>(null)

  useEffect(() => {
    fetchEvals()
      .then(d => {
        setSummary(d.summary?.total_tests != null ? d.summary : null)
        setResults(d.results ?? [])
      })
      .catch(() => {}) // no cached results yet — that's fine
      .finally(() => setLoading(false))
  }, [])

  async function startRun() {
    setRunning(true)
    setError('')
    setResults([])
    setSummary(null)
    setProgress({ current: 0, total: 0 })

    try {
      await runEvalsStream(
        (row, idx, total) => {
          setProgress({ current: idx + 1, total })
          setResults(prev => [...prev, row])
        },
        (s) => {
          setSummary(s)
          setLastRunAt(new Date().toLocaleTimeString())
        },
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <div style={{ padding: 40, color: '#9A9AA6' }}>Loading…</div>

  const passed = results.filter(r => r.tool_match && r.status_match && r.grounded).length

  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '26px 28px' }}>

        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
          <button
            onClick={startRun}
            disabled={running}
            style={{ all: 'unset', cursor: running ? 'default' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: 9, background: running ? '#D0D0DA' : '#23232B', color: '#fff', padding: '11px 20px', borderRadius: 10, fontWeight: 700, fontSize: 14, opacity: running ? .8 : 1 }}
          >
            {running ? (
              <>
                <span style={{ width: 13, height: 13, border: '2px solid #4A4A56', borderTopColor: '#FFE600', borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />
                Running {progress.current}/{progress.total}…
              </>
            ) : (
              <>
                <span style={{ fontSize: 16, lineHeight: 1 }}>▶</span>
                Run evaluations
              </>
            )}
          </button>
          {lastRunAt && !running && (
            <span style={{ fontSize: 12.5, color: '#9A9AA6', fontFamily: "'JetBrains Mono', monospace" }}>
              Last run: {lastRunAt}
            </span>
          )}
          {error && <span style={{ fontSize: 13, color: '#B4232A' }}>{error}</span>}
          {running && <div style={{ flex: 1 }}><ProgressBar current={progress.current} total={progress.total} /></div>}
        </div>

        {/* KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1fr 1fr', gap: 13, marginBottom: 20 }}>
          <div style={{ background: '#23232B', borderRadius: 13, padding: '16px 18px', color: '#fff' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.06em' }}>Cases passed</div>
            <div style={{ fontSize: 32, fontWeight: 800, marginTop: 6, letterSpacing: '-.01em' }}>
              {results.length === 0 && !running ? (
                <span style={{ fontSize: 16, color: '#7A7A88' }}>Run to see results</span>
              ) : (
                <>{passed}<span style={{ color: '#7A7A88' }}>/{results.length}</span>
                {' '}<span style={{ fontSize: 17, color: '#FFE600', fontWeight: 700 }}>{results.length ? Math.round(passed / results.length * 100) + '%' : '—'}</span></>
              )}
            </div>
          </div>
          {[
            { label: 'Tool selection', value: summary ? `${summary.tool_match_count}/${summary.total_tests}` : '—' },
            { label: 'Grounded',       value: summary ? `${summary.grounded_count}/${summary.total_tests}` : '—' },
            { label: 'RBAC',           value: summary ? `${summary.status_match_count}/${summary.total_tests}` : '—' },
            { label: 'Avg latency',    value: summary ? fmtMs(summary.avg_latency_ms) : '—' },
          ].map(k => (
            <div key={k.label} style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 13, padding: '16px 17px' }}>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.05em' }}>{k.label}</div>
              <div style={{ fontSize: 26, fontWeight: 800, marginTop: 6, fontFamily: "'JetBrains Mono', monospace" }}>{k.value}</div>
            </div>
          ))}
        </div>

        {/* Results table */}
        {(results.length > 0 || running) && (
          <div style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 14, overflow: 'hidden' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '34px 1fr 44px 44px 44px 72px 76px', gap: 8, padding: '12px 16px', background: '#F8F8FB', borderBottom: '1px solid #EDEDF1', fontSize: 12, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.05em' }}>
              <span>#</span><span>Test question</span>
              <span style={{ textAlign: 'center' }}>Tool</span>
              <span style={{ textAlign: 'center' }}>Grnd</span>
              <span style={{ textAlign: 'center' }}>Stat</span>
              <span style={{ textAlign: 'right' }}>Latency</span>
              <span style={{ textAlign: 'right' }}>Result</span>
            </div>
            {results.map((e, idx) => {
              const pass = e.tool_match && e.status_match && e.grounded
              return (
                <div key={e.id} style={{ display: 'grid', gridTemplateColumns: '34px 1fr 44px 44px 44px 72px 76px', gap: 8, padding: '14px 16px', borderTop: '1px solid #F1F1F4', alignItems: 'start', animation: 'fadeUp .25s ease both' }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13.5, fontWeight: 600, color: '#9A9AA6' }}>{idx + 1}</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#23232B', lineHeight: 1.4 }}>{e.query}</div>
                    <div style={{ fontSize: 12, color: '#9A9AA6', fontFamily: "'JetBrains Mono', monospace", marginTop: 3 }}>{e.expected_tools.join(' → ') || 'no tools expected'}</div>
                    {e.notes && <div style={{ fontSize: 13, color: '#8C8C99', marginTop: 5, lineHeight: 1.45 }}>{e.notes}</div>}
                  </div>
                  <span style={{ display: 'flex', justifyContent: 'center' }}><Badge v={e.tool_match} /></span>
                  <span style={{ display: 'flex', justifyContent: 'center' }}><Badge v={e.grounded} /></span>
                  <span style={{ display: 'flex', justifyContent: 'center' }}><Badge v={e.status_match} /></span>
                  <span style={{ textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5, color: '#6B6B78' }}>{fmtMs(e.latency_ms)}</span>
                  <span style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: pass ? '#1F7A4D' : '#B4232A', background: pass ? '#E7F4EC' : '#FBEAEA', padding: '3px 9px', borderRadius: 20, fontFamily: "'JetBrains Mono', monospace" }}>{pass ? 'PASS' : 'FAIL'}</span>
                  </span>
                </div>
              )
            })}
            {running && progress.current < progress.total && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', borderTop: '1px solid #F1F1F4', color: '#9A9AA6', fontSize: 13 }}>
                <span style={{ width: 11, height: 11, border: '2px solid #E6E6EC', borderTopColor: '#23232B', borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />
                Running test {progress.current + 1}…
              </div>
            )}
          </div>
        )}

        {!running && results.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#9A9AA6', fontSize: 15 }}>
            Click <strong style={{ color: '#23232B' }}>Run evaluations</strong> to execute the test suite live against the agent.
          </div>
        )}

        {summary && (
          <div style={{ marginTop: 14, display: 'flex', gap: 9, alignItems: 'flex-start', background: summary.verdict === 'PASS' ? '#EDF6F1' : '#FBEAEA', border: `1px solid ${summary.verdict === 'PASS' ? '#C0E0D0' : '#FBCECE'}`, borderRadius: 11, padding: '13px 15px' }}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, fontWeight: 700, color: summary.verdict === 'PASS' ? '#1F7A4D' : '#B4232A', flexShrink: 0, marginTop: 1 }}>verdict</span>
            <span style={{ fontSize: 14.5, color: '#3A3A44', lineHeight: 1.5 }}>
              <strong>{summary.verdict}</strong> — {summary.tool_match_count}/{summary.total_tests} tool_match · {summary.grounded_count}/{summary.total_tests} grounded · {summary.status_match_count}/{summary.total_tests} status_match · avg {fmtMs(summary.avg_latency_ms)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
