import { useEffect, useState } from 'react'
import { fetchIssues, fetchIssueDetail } from '../api/issues'
import { statusMeta, severityToPriority, prioMeta, issId, fmtDate } from '../utils'
import { useAuth } from '../store/AuthContext'
import type { Issue, IssueDetail } from '../types'

const FILTERS = ['All', 'Open', 'In Progress', 'Resolved']

export default function Issues() {
  const { user } = useAuth()
  const [issues, setIssues] = useState<Issue[]>([])
  const [selId, setSelId] = useState<number | null>(null)
  const [detail, setDetail] = useState<IssueDetail | null>(null)
  const [filter, setFilter] = useState('All')
  const [loading, setLoading] = useState(true)
  const [updateDraft, setUpdateDraft] = useState('')
  const [actionDraft, setActionDraft] = useState('')
  const [toast, setToast] = useState('')

  const canUpdate = user?.role === 'support_user' || user?.role === 'admin'
  const canCreate = user?.role === 'admin'

  function flash(msg: string) {
    setToast(msg)
    setTimeout(() => setToast(''), 2800)
  }

  useEffect(() => {
    fetchIssues()
      .then(data => {
        setIssues(data)
        if (data.length) setSelId(data[0].id)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selId) return
    setDetail(null)
    fetchIssueDetail(selId).then(setDetail)
  }, [selId])

  const filtered = filter === 'All' ? issues : issues.filter(i => i.status.toLowerCase() === filter.toLowerCase())
  const selIssue = issues.find(i => i.id === selId) ?? null

  if (loading) return <div style={{ padding: 40, color: '#9A9AA6' }}>Loading issues…</div>

  return (
    <div style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', height: '100%' }}>
        {/* List panel */}
        <div style={{ width: 430, flexShrink: 0, borderRight: '1px solid #E6E6EC', background: '#fff', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '13px 16px', borderBottom: '1px solid #EDEDF1', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {FILTERS.map(f => {
              const active = filter === f
              return (
                <button key={f} onClick={() => setFilter(f)} style={{ all: 'unset', cursor: 'pointer', fontSize: 14, fontWeight: 600, color: active ? '#fff' : '#5A5A66', background: active ? '#23232B' : '#fff', border: `1px solid ${active ? '#23232B' : '#E6E6EC'}`, padding: '7px 15px', borderRadius: 18 }}>
                  {f}
                </button>
              )
            })}
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {filtered.map(i => {
              const sm = statusMeta(i.status)
              const pm = prioMeta(i.severity)
              const sel = i.id === selId
              return (
                <button key={i.id} onClick={() => setSelId(i.id)} style={{ all: 'unset', cursor: 'pointer', display: 'block', width: '100%', boxSizing: 'border-box', padding: '15px 16px 15px 17px', borderBottom: '1px solid #F1F1F4', background: sel ? '#F4F4F7' : '#fff', position: 'relative' }}>
                  <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: sel ? '#FFE600' : 'transparent' }} />
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13.5, fontWeight: 600, color: '#8C8C99' }}>{issId(i.id)}</span>
                    <span style={{ fontSize: 12.5, fontWeight: 700, color: pm.fg, background: pm.bg, padding: '2px 8px', borderRadius: 4, fontFamily: "'JetBrains Mono', monospace" }}>{severityToPriority(i.severity)}</span>
                    <span style={{ marginLeft: 'auto', fontSize: 13, fontWeight: 700, color: sm.fg, background: sm.bg, padding: '3px 10px', borderRadius: 20 }}>{i.status}</span>
                  </div>
                  <div style={{ fontSize: 17, fontWeight: 600, marginTop: 7, color: '#23232B', textAlign: 'left', lineHeight: 1.35 }}>{i.title}</div>
                  <div style={{ fontSize: 15, color: '#9A9AA6', marginTop: 4, textAlign: 'left' }}>{i.customer_name}</div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Detail panel */}
        <div style={{ flex: 1, overflowY: 'auto', background: '#F4F4F7' }}>
          {selIssue ? (
            <div style={{ maxWidth: 780, margin: '0 auto', padding: '26px 30px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 10 }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 14.5, fontWeight: 600, color: '#6B6B78' }}>{issId(selIssue.id)}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: prioMeta(selIssue.severity).fg, background: prioMeta(selIssue.severity).bg, padding: '2px 8px', borderRadius: 5, fontFamily: "'JetBrains Mono', monospace" }}>{severityToPriority(selIssue.severity)}</span>
                <span style={{ fontSize: 14, color: '#8C8C99' }}>{selIssue.severity}</span>
                <span style={{ marginLeft: 'auto', fontSize: 14, fontWeight: 700, color: statusMeta(selIssue.status).fg, background: statusMeta(selIssue.status).bg, padding: '4px 13px', borderRadius: 20 }}>{selIssue.status}</span>
              </div>
              <h2 style={{ fontSize: 32, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-.01em', lineHeight: 1.22 }}>{selIssue.title}</h2>
              <div style={{ fontSize: 17, fontWeight: 700, color: '#2A5BC0' }}>{selIssue.customer_name}</div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: '#E6E6EC', border: '1px solid #E6E6EC', borderRadius: 12, overflow: 'hidden', marginTop: 18 }}>
                {[
                  { label: 'Opened',   value: fmtDate(selIssue.created_at) },
                  { label: 'Customer', value: selIssue.customer_name },
                  { label: 'Severity', value: selIssue.severity },
                  { label: 'Status',   value: selIssue.status },
                ].map(f => (
                  <div key={f.label} style={{ background: '#fff', padding: '14px 16px' }}>
                    <div style={{ fontSize: 12.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.05em' }}>{f.label}</div>
                    <div style={{ fontSize: 16, fontWeight: 600, marginTop: 5 }}>{f.value}</div>
                  </div>
                ))}
              </div>

              {/* Actions panel */}
              <div style={{ marginTop: 18, background: '#fff', border: '1px solid #E6E6EC', borderRadius: 13, padding: '16px 17px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 14 }}>
                  <span style={{ fontSize: 16, fontWeight: 800 }}>Actions</span>
                  <span style={{ fontSize: 13.5, color: '#9A9AA6' }}>Enforced by your role</span>
                </div>

                <div style={{ fontSize: 13.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 9 }}>
                  Status{!canUpdate && <span style={{ color: '#C2410C', textTransform: 'none', letterSpacing: 0, fontWeight: 600 }}> · read-only role</span>}
                </div>
                <div style={{ display: 'flex', gap: 7, marginBottom: 20 }}>
                  {['Open', 'In Progress', 'Waiting', 'Resolved'].map(s => {
                    const isActive = selIssue.status.toLowerCase() === s.toLowerCase() || (s === 'In Progress' && selIssue.status === 'in_progress')
                    return (
                      <button key={s} disabled={!canUpdate} style={{ all: 'unset', cursor: canUpdate ? 'pointer' : 'default', fontSize: 15, fontWeight: 600, padding: '8px 17px', borderRadius: 7, border: `1px solid ${isActive ? '#23232B' : '#E6E6EC'}`, background: isActive ? '#23232B' : '#fff', color: isActive ? '#fff' : '#6B6B78', opacity: canUpdate ? 1 : 0.55 }}>{s}</button>
                    )
                  })}
                </div>

                <div style={{ fontSize: 13.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 9 }}>
                  Post an update {!canUpdate && <span style={{ color: '#C2410C', textTransform: 'none', letterSpacing: 0, fontWeight: 600 }}> · read-only role</span>}
                </div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
                  <input
                    value={updateDraft}
                    onChange={e => setUpdateDraft(e.target.value)}
                    placeholder="Add a note or status update…"
                    disabled={!canUpdate}
                    style={{ flex: 1, border: '1.5px solid #E0E0E6', borderRadius: 9, padding: '12px 15px', fontFamily: "'Manrope', sans-serif", fontSize: 16, outline: 'none', minWidth: 0, opacity: canUpdate ? 1 : .5 }}
                  />
                  <button
                    onClick={() => { if (!canUpdate) { flash('Read-only role — you can\'t post updates.'); return } if (!updateDraft.trim()) return; flash('Update posted to ' + issId(selIssue.id)); setUpdateDraft('') }}
                    style={{ all: 'unset', cursor: 'pointer', fontSize: 15.5, fontWeight: 700, color: '#fff', background: canUpdate && updateDraft.trim() ? '#23232B' : '#C7C7CF', padding: '12px 20px', borderRadius: 9 }}
                  >Post</button>
                </div>

                <div style={{ fontSize: 13.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 9 }}>Create next action</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    value={actionDraft}
                    onChange={e => setActionDraft(e.target.value)}
                    placeholder="Recommend a next action…"
                    disabled={!canCreate}
                    style={{ flex: 1, border: '1.5px solid #E0E0E6', borderRadius: 9, padding: '12px 15px', fontFamily: "'Manrope', sans-serif", fontSize: 16, outline: 'none', minWidth: 0, opacity: canCreate ? 1 : .5 }}
                  />
                  <button
                    onClick={() => { if (!canCreate) { flash('Creating next actions requires the admin role.'); return } if (!actionDraft.trim()) return; flash('Next action created on ' + issId(selIssue.id)); setActionDraft('') }}
                    style={{ all: 'unset', cursor: 'pointer', fontSize: 15.5, fontWeight: 700, color: '#fff', background: canCreate && actionDraft.trim() ? '#23232B' : '#C7C7CF', padding: '12px 20px', borderRadius: 9 }}
                  >Create</button>
                </div>
                {!canCreate && <div style={{ fontSize: 14.5, color: '#C2410C', marginTop: 8, fontWeight: 600 }}>Creating next actions requires the admin role.</div>}
              </div>

              {/* Next actions */}
              {detail && detail.next_actions.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 9 }}>Next actions</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                    {detail.next_actions.map(a => (
                      <div key={a.id} style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 11, padding: '12px 14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5, fontWeight: 600, color: '#6B6B78' }}>NA-{String(a.id).padStart(3, '0')}</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: '#1F7A4D', background: '#E7F4EC', padding: '2px 8px', borderRadius: 20 }}>{a.status}</span>
                          <span style={{ marginLeft: 'auto', fontSize: 13, color: '#9A9AA6' }}>Due {a.due_date}</span>
                        </div>
                        <div style={{ fontSize: 15, marginTop: 7, color: '#3A3A44', lineHeight: 1.5 }}>{a.action_text}</div>
                        <div style={{ fontSize: 12.5, color: '#9A9AA6', marginTop: 5 }}>Owner · {a.owner}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* History */}
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 13.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 12 }}>History</div>
                {!detail && <div style={{ fontSize: 15, color: '#9A9AA6' }}>Loading…</div>}
                {detail && detail.history.length === 0 && <div style={{ fontSize: 15, color: '#9A9AA6' }}>No updates logged for this issue.</div>}
                {detail && detail.history.length > 0 && (
                  <div style={{ borderLeft: '2px solid #E0E0E6', marginLeft: 5 }}>
                    {detail.history.map((u, i) => (
                      <div key={i} style={{ position: 'relative', padding: '0 0 18px 20px' }}>
                        <span style={{ position: 'absolute', left: -6, top: 3, width: 9, height: 9, borderRadius: '50%', background: '#2A5BC0', border: '2px solid #F4F4F7', display: 'block' }} />
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 15.5, fontWeight: 700, color: '#23232B' }}>{u.updated_by}</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: '#2A5BC0', background: '#E7EEFB', padding: '1px 7px', borderRadius: 4, fontFamily: "'JetBrains Mono', monospace" }}>note</span>
                          <span style={{ marginLeft: 'auto', fontSize: 13.5, color: '#9A9AA6', fontFamily: "'JetBrains Mono', monospace" }}>{fmtDate(u.created_at)}</span>
                        </div>
                        <div style={{ fontSize: 15.5, color: '#4A4A55', lineHeight: 1.55, marginTop: 5 }}>{u.update_text}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ padding: 40, color: '#9A9AA6' }}>Select an issue</div>
          )}
        </div>
      </div>

      {toast && (
        <div style={{ position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', background: '#23232B', color: '#fff', padding: '12px 20px', borderRadius: 11, fontSize: 15, fontWeight: 600, boxShadow: '0 16px 40px -12px rgba(0,0,0,.4)', zIndex: 80, animation: 'fadeUp .25s ease both' }}>{toast}</div>
      )}
    </div>
  )
}
