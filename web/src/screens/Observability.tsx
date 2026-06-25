import { useTraces } from '../store/TraceContext'
import { fmtMs } from '../utils'
import { useState } from 'react'
import type { TraceRecord } from '../types'

function statusStyle(s: TraceRecord['status']) {
  if (s === 'ok') return { fg: '#1F7A4D', bg: '#E7F4EC', label: 'ok' }
  if (s === 'warn') return { fg: '#9A6B00', bg: '#FBF1DF', label: 'warn' }
  return { fg: '#B4232A', bg: '#FBEAEA', label: 'error' }
}

export default function Observability() {
  const { traces } = useTraces()
  const [selId, setSelId] = useState<string | null>(traces[0]?.id ?? null)

  const maxMs = Math.max(...traces.map(t => t.ms), 1)
  const totalCalls = traces.reduce((a, t) => a + t.tools.length, 0)
  const avgMs = traces.length ? Math.round(traces.reduce((a, t) => a + t.ms, 0) / traces.length) : 0
  const grounded = traces.length ? Math.round(traces.filter(t => t.grounded).length / traces.length * 100) : 0
  const flagged = traces.filter(t => t.status !== 'ok').length

  const selTrace = traces.find(t => t.id === selId) ?? null
  let acc = 0
  const spans = (selTrace?.tools ?? []).map(x => {
    const off = Math.round(acc / Math.max(selTrace!.ms, 1) * 100)
    const w = Math.max(Math.round(x.ms / Math.max(selTrace!.ms, 1) * 100), 4)
    acc += x.ms
    return { name: x.name, ms: x.ms + ' ms', off, w }
  })

  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <div style={{ maxWidth: 1440, margin: '0 auto', padding: '26px 28px' }}>
        {/* KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 13, marginBottom: 20 }}>
          {[
            { label: 'Requests',   value: String(traces.length), sub: 'this session' },
            { label: 'Avg latency', value: fmtMs(avgMs),          sub: 'end-to-end' },
            { label: 'Tool calls',  value: String(totalCalls),    sub: 'dispatched' },
            { label: 'Grounded',    value: grounded + '%',         sub: 'cite-backed' },
            { label: 'Flagged',     value: String(flagged),        sub: 'needs review' },
          ].map(k => (
            <div key={k.label} style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 13, padding: '15px 17px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.06em' }}>{k.label}</div>
              <div style={{ fontSize: 25, fontWeight: 800, marginTop: 6, letterSpacing: '-.01em' }}>{k.value}</div>
              <div style={{ fontSize: 11, color: '#A6A6B2', marginTop: 2 }}>{k.sub}</div>
            </div>
          ))}
        </div>

        {traces.length === 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 20px', gap: 16 }}>
            <div style={{ width: 52, height: 52, borderRadius: 14, background: '#fff', border: '1px solid #E6E6EC', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M3 12h4l3 8 4-16 3 8h4" stroke="#9A9AA6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#3A3A44', marginBottom: 6 }}>No traces yet</div>
              <div style={{ fontSize: 13, color: '#9A9AA6', maxWidth: 340, lineHeight: 1.55 }}>
                Send a query from the <span style={{ fontWeight: 700, color: '#23232B' }}>Assistant</span> tab and the agent's tool calls, latency, and RBAC decisions will appear here in real time.
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              {['Tool calls', 'Latency spans', 'RBAC decisions', 'Grounding'].map(label => (
                <span key={label} style={{ fontSize: 11, fontWeight: 600, color: '#9A9AA6', background: '#fff', border: '1px solid #E6E6EC', padding: '4px 10px', borderRadius: 20 }}>{label}</span>
              ))}
            </div>
          </div>
        )}

        {traces.length > 0 && (
          <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start' }}>
            {/* Trace list */}
            <div style={{ flex: 1, minWidth: 0, background: '#fff', border: '1px solid #E6E6EC', borderRadius: 14, overflow: 'hidden' }}>
              <div style={{ padding: '13px 16px', borderBottom: '1px solid #EDEDF1', fontSize: 13, fontWeight: 800 }}>Recent traces</div>
              {traces.map(t => {
                const sc = statusStyle(t.status)
                const sel = t.id === selId
                return (
                  <button key={t.id} onClick={() => setSelId(t.id)} style={{ all: 'unset', cursor: 'pointer', display: 'block', width: '100%', boxSizing: 'border-box', padding: '13px 16px', borderTop: '1px solid #F1F1F4', background: sel ? '#F8F8FB' : '#fff', position: 'relative' }}>
                    <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: sel ? '#FFE600' : 'transparent' }} />
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#9A9AA6' }}>{t.ts}</span>
                      <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: '#23232B', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'left' }}>{t.query}</span>
                      <span style={{ fontSize: 10, fontWeight: 700, color: sc.fg, background: sc.bg, padding: '2px 8px', borderRadius: 20, fontFamily: "'JetBrains Mono', monospace" }}>{sc.label}</span>
                      {t.rbac === 'denied' && <span style={{ fontSize: 10, fontWeight: 700, color: '#B4232A', background: '#FBEAEA', padding: '2px 8px', borderRadius: 20, fontFamily: "'JetBrains Mono', monospace" }}>rbac denied</span>}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, fontWeight: 600, color: '#6B6B78', background: '#F1F1F4', padding: '2px 7px', borderRadius: 5 }}>{t.role}</span>
                      <span style={{ flex: 1, fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#9A9AA6', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'left' }}>{t.tools.map(x => x.name).join(' → ') || 'no tools'}</span>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#6B6B78' }}>{fmtMs(t.ms)}</span>
                    </div>
                    <div style={{ height: 4, background: '#EDEDF1', borderRadius: 3, marginTop: 8, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.round(t.ms / maxMs * 100)}%`, background: '#23232B', borderRadius: 3 }} />
                    </div>
                  </button>
                )
              })}
            </div>

            {/* Trace detail */}
            {selTrace && (
              <div style={{ width: 392, flexShrink: 0, background: '#fff', border: '1px solid #E6E6EC', borderRadius: 14, padding: '17px 18px' }}>
                <div style={{ fontSize: 13, fontWeight: 800 }}>Trace detail</div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#9A9AA6', marginTop: 2, marginBottom: 14 }}>{selTrace.id}</div>
                <div style={{ fontSize: 13, color: '#3A3A44', lineHeight: 1.5, marginBottom: 14 }}>{selTrace.query}</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 11, marginBottom: 16 }}>
                  {[
                    { label: 'User · role', value: `${selTrace.user} · ${selTrace.role}` },
                    { label: 'Latency',     value: fmtMs(selTrace.ms) },
                    { label: 'Tool calls',  value: String(selTrace.tools.length) },
                    { label: 'Grounded',    value: selTrace.grounded ? 'yes' : 'flagged' },
                    { label: 'RBAC',        value: selTrace.rbac },
                    { label: 'Status',      value: selTrace.statusCode === 200 ? '200 OK' : String(selTrace.statusCode) },
                  ].map(f => (
                    <div key={f.label}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.05em' }}>{f.label}</div>
                      <div style={{ fontSize: 12.5, fontWeight: 600, marginTop: 3, fontFamily: "'JetBrains Mono', monospace" }}>{f.value}</div>
                    </div>
                  ))}
                </div>
                {spans.length > 0 && (
                  <>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 9 }}>Span timeline</div>
                    {spans.map((s, i) => (
                      <div key={i} style={{ marginBottom: 9 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: "'JetBrains Mono', monospace", fontSize: 11, marginBottom: 4 }}>
                          <span style={{ color: '#3A3A44' }}>{s.name}</span>
                          <span style={{ color: '#9A9AA6' }}>{s.ms}</span>
                        </div>
                        <div style={{ height: 6, background: '#F1F1F4', borderRadius: 3, position: 'relative' }}>
                          <div style={{ position: 'absolute', top: 0, height: 6, left: `${s.off}%`, width: `${s.w}%`, background: '#23232B', borderRadius: 3 }} />
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
