import { useRef, useState } from 'react'
import { useAuth } from '../store/AuthContext'
import { useTraces } from '../store/TraceContext'
import { useNav } from '../store/NavContext'
import { sendQueryStream } from '../api/chat'
import { statusMeta, severityToPriority, prioMeta, riskMeta, issId, fmtMs, roleLabel } from '../utils'
import type { AgentStage, ChatMessage, QueryResponse, QueryStep, SkillOutput } from '../types'

function uid() { return Math.random().toString(36).slice(2) }

function applyInline(s: string): string {
  return s
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code style="background:#F1F1F4;padding:1px 5px;border-radius:4px;font-size:0.88em;font-family:JetBrains Mono,monospace">$1</code>')
}

function mdToHtml(text: string): string {
  const lines = text.split('\n')
  const out: string[] = []
  for (const line of lines) {
    const t = line.trim()
    if (!t) { out.push('<div style="height:8px"/>'); continue }
    if (/^#{1,3} /.test(t)) {
      const body = t.replace(/^#+\s*/, '')
      out.push(`<div style="font-size:13.5px;font-weight:800;color:#1C1C23;margin:12px 0 3px">${applyInline(body)}</div>`)
    } else if (t.startsWith('- ') || t.startsWith('* ')) {
      out.push(`<div style="display:flex;gap:8px;padding-left:6px;margin:2px 0"><span style="color:#9A9AA6;flex-shrink:0;line-height:1.65">•</span><span style="line-height:1.65">${applyInline(t.slice(2))}</span></div>`)
    } else if (/^\d+\.\s/.test(t)) {
      const [num, ...rest] = t.split(/\.\s(.+)/)
      out.push(`<div style="display:flex;gap:8px;padding-left:6px;margin:2px 0"><span style="color:#9A9AA6;flex-shrink:0;line-height:1.65;font-size:12px;font-family:JetBrains Mono,monospace">${num}.</span><span style="line-height:1.65">${applyInline(rest.join('. '))}</span></div>`)
    } else {
      out.push(`<div style="line-height:1.65;margin:2px 0">${applyInline(t)}</div>`)
    }
  }
  return out.join('')
}

const SUGGESTIONS = [
  { label: 'List all critical issues across all clients',                            tag: 'portfolio',   tagFg: '#B4232A', tagBg: '#FBEAEA', q: 'List all critical issues across all clients.' },
  { label: 'Profile and open issues for Pinnacle Bancorp',                           tag: 'multi-tool',  tagFg: '#2A5BC0', tagBg: '#E7EEFB', q: 'Give me the profile and all open issues for Pinnacle Bancorp.' },
  { label: 'Summarise latest status for Nexus Payments Ltd',                         tag: 'lookup',      tagFg: '#1F7A4D', tagBg: '#E7F4EC', q: 'Summarise the latest status for Nexus Payments Ltd.' },
  { label: 'Escalation summary for Apex Clearing Services and suggest next action',  tag: 'skill',       tagFg: '#9A6B00', tagBg: '#FBF1DF', q: 'Give me an escalation summary for Apex Clearing Services and suggest the next action.' },
]

function stepServer(tool: string): string {
  if (tool === 'get_customer_profile' || tool === 'get_open_issues' || tool === 'get_issue_history' || tool === 'list_all_open_issues') return 'mcp·postgres'
  if (tool === 'risk_action_agent') return 'risk·action'
  return 'acme-tools'
}

function StepRow({ step, idx }: { step: QueryStep; idx: number }) {
  const tool = step.tool ?? step.skill ?? 'unknown'
  const output = step.output
  let rows: Array<{ cells: string[] }> = []
  let colHeads: string[] = []

  if (tool === 'get_customer_profile' && output && typeof output === 'object' && !Array.isArray(output)) {
    colHeads = ['field', 'value']
    const o = output as Record<string, unknown>
    rows = Object.entries(o).map(([k, v]) => ({ cells: [k, String(v ?? '')] }))
  } else if (tool === 'get_open_issues' && Array.isArray(output)) {
    colHeads = ['id', 'title', 'severity', 'status']
    rows = (output as Array<Record<string, unknown>>).map(i => ({ cells: [issId(Number(i.id)), String(i.title ?? ''), String(i.severity ?? ''), String(i.status ?? '')] }))
  } else if (tool === 'get_issue_history' && Array.isArray(output)) {
    colHeads = ['updated_by', 'note']
    rows = (output as Array<Record<string, unknown>>).map(u => ({ cells: [String(u.updated_by ?? ''), String(u.update_text ?? '')] }))
  } else if (tool === 'recommend_next_action' && output && typeof output === 'object' && !Array.isArray(output)) {
    const o = output as Record<string, unknown>
    colHeads = ['field', 'value']
    rows = [
      { cells: ['action', String(o.action_text ?? '')] },
      { cells: ['owner', String(o.owner ?? '')] },
      { cells: ['due', String(o.due_date ?? '')] },
      { cells: ['status', String(o.status ?? '')] },
    ]
  } else if (step.skill === 'risk_action_agent' && output && typeof output === 'object') {
    const o = output as Record<string, unknown>
    colHeads = ['field', 'value']
    rows = [
      { cells: ['risk_level', String(o.risk_level ?? '')] },
      { cells: ['urgency', String(o.urgency ?? '')] },
      { cells: ['primary_issue', String((o.selected_primary_issue as Record<string, unknown> | null)?.title ?? '—')] },
    ]
  }

  return (
    <div style={{ borderTop: '1px solid #25252E', padding: '11px 0 3px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#5BD89A', flexShrink: 0 }} />
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5, fontWeight: 600, color: '#EDEDF2' }}>{tool}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 600, color: '#7A7A88', background: '#23232D', padding: '2px 7px', borderRadius: 5 }}>{step.skill ? stepServer(step.skill) : stepServer(tool)}</span>
        <span style={{ marginLeft: 'auto', fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, color: '#8A8A99' }}>step {idx + 1}</span>
      </div>
      {step.args && (
        <div style={{ margin: '7px 0 0 18px', fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#7E7E8C' }}>
          {JSON.stringify(step.args)}
        </div>
      )}
      {rows.length > 0 && (
        <div style={{ margin: '7px 0 0 18px', border: '1px solid #2A2A33', borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ display: 'flex', background: '#15151B' }}>
            {colHeads.map(h => <div key={h} style={{ flex: 1, padding: '5px 10px', fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5, fontWeight: 700, color: '#7A7A88', textTransform: 'uppercase', letterSpacing: '.05em' }}>{h}</div>)}
          </div>
          {rows.map((r, i) => (
            <div key={i} style={{ display: 'flex', borderTop: '1px solid #23232B' }}>
              {r.cells.map((c, j) => <div key={j} style={{ flex: 1, padding: '6px 10px', fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#C7C7D2', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c}</div>)}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const STAGE_LABELS: Record<NonNullable<AgentStage>, string> = {
  planning: 'Agent 1 — Planning…',
  tools: 'ReAct loop — reasoning & tools…',
  risk_action: 'Agent 2 — Risk assessment…',
  response: 'Agent 3 — Writing response…',
}

function DisambiguationCard({ dis, onSelect }: {
  dis: { matches: string[]; original_query: string }
  onSelect: (name: string) => void
}) {
  return (
    <div style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 15, padding: '18px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, fontWeight: 700, color: '#9A6B00', background: '#FBF1DF', padding: '3px 8px', borderRadius: 5, letterSpacing: '.05em' }}>NAME RESOLUTION</span>
        <span style={{ fontSize: 13.5, fontWeight: 600, color: '#3A3A44' }}>
          {dis.matches.length === 1
            ? `Did you mean ${dis.matches[0]}?`
            : 'Multiple customers match — please confirm which one you meant:'}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {dis.matches.map(name => (
          <button key={name} onClick={() => onSelect(name)} style={{ all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, padding: '12px 15px', background: '#F8F8FB', border: '1px solid #E6E6EC', borderRadius: 11, transition: 'border-color .15s' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#23232B')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#E6E6EC')}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#2A5BC0', flexShrink: 0 }} />
            <span style={{ fontSize: 14.5, fontWeight: 700, color: '#23232B' }}>{name}</span>
            <span style={{ marginLeft: 'auto', fontSize: 11, color: '#9A9AA6', fontFamily: "'JetBrains Mono', monospace" }}>{dis.matches.length === 1 ? 'yes, fetch →' : 'confirm →'}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function AgentTrace({ msg }: { msg: ChatMessage }) {
  const [open, setOpen] = useState(false)
  const steps = msg.loading ? (msg.partialSteps ?? []) : (msg.response?.steps ?? [])
  const plan  = msg.loading ? msg.partialPlan : msg.response?.plan
  const thoughts = msg.reactThoughts ?? []
  const totalMs = steps.reduce((a, s) => {
    const o = s.output
    if (typeof o === 'object' && o !== null && 'id' in o) return a + 100
    return a + 80
  }, 0)

  return (
    <div style={{ marginTop: 9 }}>
      {!msg.loading && (
        <button onClick={() => setOpen(o => !o)} style={{ all: 'unset', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 14, fontWeight: 600, color: '#6B6B78', fontFamily: "'JetBrains Mono', monospace" }}>
          <span style={{ fontSize: 9 }}>{open ? '▼' : '▶'}</span>
          Agent trace · {steps.filter(s => s.tool).length} tool calls · {thoughts.length > 0 ? `${thoughts.length} thoughts · ` : ''}{fmtMs(totalMs)}
        </button>
      )}
      {(open || msg.loading) && (
        <div style={{ marginTop: 10, background: '#1C1C23', borderRadius: 13, padding: '15px 17px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 11 }}>
            {msg.loading && <span style={{ width: 13, height: 13, border: '2px solid #3A3A45', borderTopColor: '#FFE600', borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />}
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 700, color: '#A6A6B2', letterSpacing: '.05em', textTransform: 'uppercase' }}>
              {msg.loading ? (STAGE_LABELS[msg.currentStage ?? 'planning'] ?? 'Reasoning & tool calls') : 'Agent trace'}
            </span>
          </div>

          {/* ReAct thoughts — shown during streaming and in completed trace */}
          {thoughts.length > 0 && (
            <div style={{ marginBottom: 10, borderBottom: '1px solid #25252E', paddingBottom: 10 }}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5, fontWeight: 700, color: '#FFE600', letterSpacing: '.07em', textTransform: 'uppercase', marginBottom: 7 }}>ReAct loop</div>
              {thoughts.map((t, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 5, fontSize: 11.5, lineHeight: 1.5 }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 700, color: '#7A7A88', flexShrink: 0, marginTop: 1 }}>T{i + 1}</span>
                  <span style={{ color: '#C4C4D0', flex: 1 }}>{t.thought}</span>
                  {t.next_tool && t.next_tool !== 'done' && (
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 600, color: '#5BD89A', flexShrink: 0 }}>→ {t.next_tool}</span>
                  )}
                  {t.next_tool === 'done' && (
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 600, color: '#FFE600', flexShrink: 0 }}>done</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {plan && (
            <div style={{ display: 'flex', gap: 8, fontSize: 12.5, lineHeight: 1.55, color: '#9A9AA6', paddingBottom: 4 }}>
              <span style={{ color: '#FFE600', fontWeight: 700, flexShrink: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>plan</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>{plan.planner_mode}</span>
            </div>
          )}
          {steps.map((s, i) => <StepRow key={i} step={s} idx={i} />)}
          {!msg.loading && (
            <div style={{ borderTop: '1px solid #25252E', marginTop: 9, paddingTop: 9, fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, color: '#7A7A88' }}>
              {steps.filter(s => s.tool).length} tool calls · {thoughts.length} react steps · {plan?.planner_mode ?? ''} · rbac: {msg.response?.user.roles.join(',')}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function healthMeta(h: string) {
  if (h === 'red')   return { fg: '#B4232A', bg: '#FBEAEA' }
  if (h === 'amber') return { fg: '#9A6B00', bg: '#FBF1DF' }
  if (h === 'green') return { fg: '#1F7A4D', bg: '#E7F4EC' }
  return { fg: '#6B6B78', bg: '#F1F1F4' }
}

function extractRec(answer: string): string {
  const paras = answer.split(/\n{2,}/).map(p => p.trim()).filter(Boolean)
  for (let i = paras.length - 1; i >= 0; i--) {
    const p = paras[i]
    if (!p.startsWith('-') && !p.startsWith('*') && !p.startsWith('#') && !/^\d+\./.test(p)) return p
  }
  return ''
}

function PortfolioView({ issues, answer }: { issues: Array<Record<string, unknown>>; answer: string }) {
  const { navigate } = useNav()
  const byCustomer: Record<string, Array<Record<string, unknown>>> = {}
  for (const iss of issues) {
    const cn = String(iss.customer_name ?? 'Unknown')
    ;(byCustomer[cn] ??= []).push(iss)
  }
  const rec = extractRec(answer)
  return (
    <>
      <div style={{ fontSize: 11.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 14 }}>
        {issues.length} issue{issues.length !== 1 ? 's' : ''} · {Object.keys(byCustomer).length} client{Object.keys(byCustomer).length !== 1 ? 's' : ''}
      </div>
      {Object.entries(byCustomer).map(([cname, cissues]) => {
        const health = String(cissues[0]?.health_status ?? 'unknown')
        const hc = healthMeta(health)
        return (
          <div key={cname} style={{ marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
              <span style={{ fontSize: 14.5, fontWeight: 800, color: '#1C1C23' }}>{cname}</span>
              <span style={{ fontSize: 10.5, fontWeight: 700, color: hc.fg, background: hc.bg, padding: '2px 8px', borderRadius: 5, fontFamily: "'JetBrains Mono', monospace" }}>{health}</span>
            </div>
            <div style={{ border: '1px solid #EDEDF1', borderRadius: 11, overflow: 'hidden' }}>
              {cissues.map((it, i) => {
                const sev = String(it.severity ?? 'low') as import('../types').Severity
                const sm = statusMeta(String(it.status ?? ''))
                const pm = prioMeta(sev)
                return (
                  <div key={i} onClick={() => navigate('issues', Number(it.id))} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '10px 13px', borderTop: i > 0 ? '1px solid #EDEDF1' : 'none', background: '#fff', cursor: 'pointer' }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11.5, fontWeight: 600, color: '#2A5BC0', flexShrink: 0, width: 62 }}>{issId(Number(it.id))}</span>
                    <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: '#23232B', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(it.title ?? '')}</span>
                    <span style={{ fontSize: 10.5, fontWeight: 700, color: pm.fg, background: pm.bg, padding: '2px 7px', borderRadius: 5, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>{severityToPriority(sev)}</span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: sm.fg, background: sm.bg, padding: '3px 9px', borderRadius: 20, flexShrink: 0 }}>{String(it.status ?? '').replace(/_/g, ' ')}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
      {rec && (
        <div style={{ marginTop: 4, padding: '11px 14px', background: '#F8F8FB', border: '1px solid #EDEDF1', borderRadius: 10, fontSize: 13.5, color: '#4A4A55', lineHeight: 1.6 }}
          dangerouslySetInnerHTML={{ __html: applyInline(rec) }}
        />
      )}
    </>
  )
}

function AnswerCard({ msg }: { msg: ChatMessage }) {
  const { navigate } = useNav()
  const r = msg.response
  if (!r) return null
  // risk_action_agent replaced customer_escalation_summary in the 3-agent refactor
  const skillStep = r.steps.find(s => s.skill === 'risk_action_agent')
  const skill = skillStep?.output as SkillOutput | undefined
  const issuesStep = r.steps.find(s => s.tool === 'get_open_issues')
  const issues = (issuesStep?.output ?? []) as Array<Record<string, unknown>>
  const histStep = r.steps.find(s => s.tool === 'get_issue_history')
  const history = (histStep?.output ?? []) as Array<Record<string, unknown>>
  const nextStep = r.steps.find(s => s.tool === 'recommend_next_action')
  const nextAction = nextStep?.output as Record<string, unknown> | undefined
  const allIssuesStep = r.steps.find(s => s.tool === 'list_all_open_issues')
  const allIssues = (allIssuesStep?.output ?? []) as Array<Record<string, unknown>>

  const profileStep = r.steps.find(s => s.tool === 'get_customer_profile')
  const profile = profileStep?.output as Record<string, unknown> | undefined

  // Derive customer identity from whichever source is available
  const customerName = String(
    profile?.name ??
    (issues.length > 0 ? issues[0].customer_name : undefined) ??
    r.plan?.customer_name ?? ''
  )
  const customerSegment = String(profile?.segment ?? '')
  const customerHealth  = String(profile?.health_status ?? '')

  // Structured data present → use component view; absent → fall back to markdown
  const hasStructuredData = Boolean(profile) || issues.length > 0 || allIssues.length > 0

  const citations: Array<{ label: string; dot: string }> = []
  if (customerName) citations.push({ label: customerName, dot: '#2A5BC0' })
  if (issues.length) citations.push(...issues.map((i) => ({ label: issId(Number(i.id)), dot: '#23232B' })))

  return (
    <div style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 15, padding: '18px 20px' }}>
      {allIssues.length > 0 && <PortfolioView issues={allIssues} answer={r.answer} />}

      {/* Single-customer structured view — never mix with markdown */}
      {allIssues.length === 0 && hasStructuredData && customerName && (
        <p style={{ margin: '0 0 2px', fontSize: 14.5, lineHeight: 1.6, color: '#2E2E38', fontWeight: 500 }}>
          <button onClick={() => navigate('issues', issues[0] ? Number(issues[0].id) : undefined)} style={{ all: 'unset', cursor: 'pointer', fontWeight: 700, color: '#2A5BC0', textDecoration: 'underline', textDecorationStyle: 'dotted', textUnderlineOffset: '3px' }}>{customerName}</button>
          {customerSegment && <span style={{ color: '#6B6B78' }}> ({customerSegment})</span>}
          {customerHealth && <span> — health: <strong>{customerHealth}</strong></span>}
        </p>
      )}

      {/* Markdown fallback — only when no structured tool data is available (cache hits, general answers) */}
      {allIssues.length === 0 && !hasStructuredData && (
        <div style={{ fontSize: 14.5, color: '#2E2E38' }}
          dangerouslySetInnerHTML={{ __html: mdToHtml(r.answer) }}
        />
      )}

      {allIssues.length === 0 && issues.length > 0 && (
        <div style={{ marginTop: 14, border: '1px solid #EDEDF1', borderRadius: 11, overflow: 'hidden' }}>
          {issues.map((it, i) => {
            const sev = String(it.severity ?? 'low') as import('../types').Severity
            const sm = statusMeta(String(it.status ?? ''))
            const pm = prioMeta(sev)
            return (
              <div key={i} onClick={() => navigate('issues', Number(it.id))} style={{ display: 'flex', alignItems: 'center', gap: 11, width: '100%', padding: '11px 13px', borderTop: i > 0 ? '1px solid #EDEDF1' : 'none', background: '#fff', cursor: 'pointer' }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11.5, fontWeight: 600, color: '#2A5BC0', flexShrink: 0, width: 72 }}>{issId(Number(it.id))}</span>
                <span style={{ flex: 1, fontSize: 13.5, fontWeight: 600, color: '#23232B', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(it.title ?? '')}</span>
                <span style={{ fontSize: 10.5, fontWeight: 700, color: pm.fg, background: pm.bg, padding: '2px 7px', borderRadius: 5, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>{severityToPriority(sev)}</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: sm.fg, background: sm.bg, padding: '3px 9px', borderRadius: 20, flexShrink: 0 }}>{String(it.status ?? '')}</span>
              </div>
            )
          })}
        </div>
      )}

      {allIssues.length === 0 && history.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 5 }}>Latest status</div>
          <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, color: '#4A4A55' }}>
            {String(history[history.length - 1]?.update_text ?? '')}
            <span style={{ color: '#9A9AA6', marginLeft: 6 }}>— {String(history[history.length - 1]?.updated_by ?? '')}</span>
          </p>
        </div>
      )}

      {allIssues.length === 0 && skill && (
        <div style={{ marginTop: 16, border: '1px solid #E6E6EC', borderRadius: 13, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 15px', background: '#1C1C23' }}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 700, color: '#FFE600', letterSpacing: '.06em' }}>RISK · ACTION</span>
            <span style={{ fontSize: 13.5, fontWeight: 700, color: '#fff' }}>Customer Escalation Summary</span>
            <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 800, color: '#fff', background: riskMeta(skill.risk_level).fg, padding: '4px 11px', borderRadius: 20, letterSpacing: '.04em' }}>{skill.risk_level.toUpperCase()}</span>
          </div>
          <div style={{ padding: '16px 17px' }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#23232B' }}>{skill.customer_name}</div>
            <p style={{ margin: '11px 0 0', fontSize: 13.5, lineHeight: 1.62, color: '#3A3A44' }}>{skill.executive_summary}</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginTop: 15 }}>
              <div>
                <div style={{ fontSize: 10.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 8 }}>Risk rationale</div>
                <p style={{ margin: 0, fontSize: 12.5, color: '#4A4A55' }}>{skill.rationale}</p>
              </div>
              <div>
                <div style={{ fontSize: 10.5, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 8 }}>Missing information</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {skill.missing_information.map((m, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, fontSize: 12.5, lineHeight: 1.45, color: '#4A4A55' }}>
                      <span style={{ color: '#9A9AA6', fontWeight: 800, flexShrink: 0 }}>?</span><span>{m}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div style={{ marginTop: 15, background: '#FBF8E5', border: '1px solid #F0E7A8', borderRadius: 10, padding: '12px 14px' }}>
              <div style={{ fontSize: 10.5, fontWeight: 700, color: '#8A7A1A', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 4 }}>Recommended next action</div>
              <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: '#3A3A44', fontWeight: 600 }}>{skill.recommended_next_action}</p>
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 18, fontSize: 12, color: '#8C8C99' }}>
              <span><b style={{ color: '#4A4A55', fontWeight: 700 }}>Urgency</b> · {skill.urgency}</span>
              <span><b style={{ color: '#4A4A55', fontWeight: 700 }}>Owner</b> · {skill.owner_suggestion}</span>
            </div>
          </div>
        </div>
      )}

      {allIssues.length === 0 && nextAction && (
        <div style={{ marginTop: 14, border: '1px solid #E6E6EC', borderRadius: 12, padding: '14px 15px', background: '#FAFAFC' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 7 }}>Recommended next action</div>
          <p style={{ margin: '0 0 10px', fontSize: 13.5, lineHeight: 1.55, color: '#3A3A44', fontWeight: 600 }}>{String(nextAction.action_text ?? '')}</p>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: 12, color: '#8C8C99' }}>
            <span><b style={{ color: '#4A4A55', fontWeight: 700 }}>Owner</b> · {String(nextAction.owner ?? '')}</span>
            <span><b style={{ color: '#4A4A55', fontWeight: 700 }}>Due</b> · {String(nextAction.due_date ?? '')}</span>
            <span><b style={{ color: '#4A4A55', fontWeight: 700 }}>Status</b> · {String(nextAction.status ?? '')}</span>
          </div>
        </div>
      )}

      {citations.length > 0 && (
        <div style={{ marginTop: 14, paddingTop: 13, borderTop: '1px solid #EDEDF1', display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.07em' }}>Grounded in</span>
          {citations.map((c, i) => {
            const issMatch = c.label.match(/^ISS-(\d+)$/)
            const issNum = issMatch ? parseInt(issMatch[1]) : null
            return (
              <span key={i} onClick={() => issNum !== null ? navigate('issues', issNum) : navigate('issues')} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, color: '#3A3A44', background: '#F1F1F4', border: '1px solid #E6E6EC', padding: '4px 9px', borderRadius: 7, cursor: 'pointer' }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.dot, flexShrink: 0 }} />{c.label}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function Assistant() {
  const { user } = useAuth()
  const { addTrace } = useTraces()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [sessionId] = useState(() => 'atlas-' + uid())
  const chatRef = useRef<HTMLDivElement>(null)

  function scrollBottom() {
    requestAnimationFrame(() => {
      if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
    })
  }

  function update(id: string, patch: Partial<ChatMessage>) {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, ...patch } : m))
  }

  async function send(text?: string, confirmedCustomer = '') {
    const q = (text ?? draft).trim()
    if (!q) return
    setDraft('')
    const userMsg: ChatMessage = { id: uid(), role: 'user', text: q }
    const assistId = uid()
    const assistMsg: ChatMessage = {
      id: assistId, role: 'assistant', loading: true,
      currentStage: 'planning', partialSteps: [], reactThoughts: [],
    }
    setMessages(prev => [...prev, userMsg, assistMsg])
    scrollBottom()

    const t0 = Date.now()
    let accAnswer = ''
    let finalUser: QueryResponse['user'] | null = null
    let finalPlan: import('../types').QueryPlan | null = null
    let finalSteps: QueryStep[] = []
    let finalTraceId = ''
    let accThoughts: import('../types').ReactThought[] = []

    try {
      await sendQueryStream(q, sessionId, (ev) => {
        if (ev.type === 'react_thought') {
          accThoughts = [...accThoughts, { thought: ev.thought, next_tool: ev.next_tool, iteration: ev.iteration }]
          update(assistId, { reactThoughts: accThoughts, currentStage: 'tools' })
          scrollBottom()

        } else if (ev.type === 'disambiguation') {
          update(assistId, {
            loading: false,
            disambiguation: { matches: ev.matches, original_query: ev.original_query },
          })
          scrollBottom()
          return

        } else if (ev.type === 'planning') {
          finalPlan = ev.plan
          update(assistId, { partialPlan: ev.plan, currentStage: 'tools' })
          scrollBottom()

        } else if (ev.type === 'tool_result') {
          finalSteps = [...finalSteps, ev.step]
          update(assistId, { partialSteps: finalSteps, currentStage: 'tools' })
          scrollBottom()

        } else if (ev.type === 'risk_action') {
          finalSteps = [...finalSteps, ev.step]
          update(assistId, { partialSteps: finalSteps, currentStage: 'response' })
          scrollBottom()

        } else if (ev.type === 'token') {
          accAnswer += ev.delta
          update(assistId, { streamingAnswer: accAnswer, currentStage: 'response' })
          scrollBottom()

        } else if (ev.type === 'answer') {
          accAnswer = ev.text
          update(assistId, { streamingAnswer: accAnswer, currentStage: 'response' })
          scrollBottom()

        } else if (ev.type === 'error') {
          const errMsg = ev.detail || 'Request failed'
          update(assistId, { loading: false, streamingAnswer: undefined, text: errMsg })
          addTrace({ id: 'tr-' + uid(), ts: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }), user: user?.displayName ?? '', role: user?.role ?? '', query: q, tools: [], ms: Date.now() - t0, status: ev.status === 403 ? 'warn' : 'error', grounded: false, rbac: ev.status === 403 ? 'denied' : 'allowed', statusCode: ev.status })

        } else if (ev.type === 'done') {
          finalUser = ev.user as QueryResponse['user']
          finalTraceId = ev.trace_id
        }
      }, undefined, confirmedCustomer)

      // Assemble final QueryResponse from accumulated stream data
      if (finalUser && finalPlan) {
        const response: QueryResponse = {
          user: finalUser,
          answer: accAnswer,
          plan: finalPlan,
          steps: finalSteps,
          session_context: { history: [] },
          trace_id: finalTraceId,
        }
        const ms = Date.now() - t0
        update(assistId, {
          loading: false, response,
          streamingAnswer: undefined, partialSteps: undefined,
          partialPlan: undefined, currentStage: null,
          reactThoughts: accThoughts,
        })
        addTrace({
          id: 'tr-' + uid(),
          ts: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          user: user?.displayName ?? '',
          role: user?.role ?? '',
          query: q,
          tools: finalSteps.filter(s => s.tool).map(s => ({ name: s.tool!, ms: 100 })),
          ms,
          status: 'ok',
          grounded: finalSteps.some(s => s.tool || s.skill === 'risk_action_agent'),
          rbac: 'allowed',
          statusCode: 200,
        })
      }

    } catch (err: unknown) {
      const ms = Date.now() - t0
      const status = (err as { status?: number }).status ?? 500
      const errMsg = err instanceof Error ? err.message : 'Request failed'
      update(assistId, { loading: false, streamingAnswer: undefined, partialSteps: undefined, partialPlan: undefined, currentStage: null, text: errMsg })
      addTrace({ id: 'tr-' + uid(), ts: new Date().toLocaleTimeString('en-GB'), user: user?.displayName ?? '', role: user?.role ?? '', query: q, tools: [], ms, status: status === 403 ? 'warn' : 'error', grounded: false, rbac: status === 403 ? 'denied' : 'allowed', statusCode: status })
    }
  }

  const rl = user ? roleLabel(user.role) : ''

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#F4F4F7' }}>
      <div ref={chatRef} style={{ flex: 1, overflowY: 'auto', padding: '28px 0', display: 'flex', flexDirection: 'column' }}>
        <div style={{ maxWidth: 840, width: '100%', margin: '0 auto', padding: '0 28px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          {messages.length === 0 && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0' }}>
              <div style={{ textAlign: 'center', marginBottom: 32 }}>
                <div style={{ width: 56, height: 56, borderRadius: 16, background: '#23232B', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
                  <span style={{ display: 'flex', gap: 3 }}>
                    <span style={{ width: 9, height: 9, background: '#FFE600' }} />
                    <span style={{ width: 9, height: 9, background: '#FFE600', opacity: .5 }} />
                  </span>
                </div>
                <h2 style={{ fontSize: 33, fontWeight: 800, margin: '0 0 10px', letterSpacing: '-.01em' }}>Hi {user?.first} — what do you need?</h2>
                <p style={{ fontSize: 18, color: '#6B6B78', margin: '0 auto', maxWidth: 480, lineHeight: 1.6 }}>Ask about a customer, their open issues, or request an escalation summary. You're signed in as <b style={{ color: '#23232B' }}>{rl}</b>.</p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 13, width: '100%' }}>
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} onClick={() => send(s.q)} style={{ all: 'unset', cursor: 'pointer', display: 'block', background: '#fff', border: '1px solid #E6E6EC', borderRadius: 14, padding: '17px 18px', boxSizing: 'border-box', transition: 'border-color .15s' }}>
                    <span style={{ display: 'inline-block', fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 600, color: s.tagFg, background: s.tagBg, padding: '2px 8px', borderRadius: 5, marginBottom: 11 }}>{s.tag}</span>
                    <span style={{ display: 'block', fontSize: 18, fontWeight: 600, lineHeight: 1.45, color: '#23232B' }}>{s.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map(m => (
            <div key={m.id} style={{ marginBottom: 22, animation: 'fadeUp .3s ease both' }}>
              {m.role === 'user' ? (
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <div style={{ maxWidth: '75%', background: '#23232B', color: '#fff', padding: '13px 17px', borderRadius: '15px 15px 4px 15px', fontSize: 16.5, lineHeight: 1.5, fontWeight: 500 }}>{m.text}</div>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 13 }}>
                  <div style={{ width: 34, height: 34, borderRadius: 9, background: '#23232B', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 2 }}>
                    <span style={{ display: 'flex', gap: 2.5 }}>
                      <span style={{ width: 6, height: 6, background: '#FFE600' }} />
                      <span style={{ width: 6, height: 6, background: '#FFE600', opacity: .5 }} />
                    </span>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Disambiguation — agent found multiple customer matches */}
                    {m.disambiguation && (
                      <DisambiguationCard
                        dis={m.disambiguation}
                        onSelect={(name) => {
                          setMessages(prev => prev.filter(x => x.id !== m.id && x.text !== m.disambiguation?.original_query))
                          send(m.disambiguation!.original_query, name)
                        }}
                      />
                    )}
                    {/* Streaming answer — shown while loading, token by token */}
                    {m.loading && m.streamingAnswer && (
                      <div style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 15, padding: '18px 20px', marginBottom: 8 }}>
                        <div style={{ fontSize: 14.5, color: '#2E2E38', lineHeight: 1.65 }}
                          dangerouslySetInnerHTML={{ __html: mdToHtml(m.streamingAnswer) }}
                        />
                        <span style={{ display: 'inline-block', width: 2, height: 16, background: '#23232B', marginLeft: 1, verticalAlign: 'text-bottom', animation: 'blink 1s step-end infinite' }} />
                      </div>
                    )}
                    {/* Spinner — only before streaming answer starts */}
                    {m.loading && !m.streamingAnswer && (
                      <div style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 15, padding: '18px 20px', display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                        <span style={{ width: 13, height: 13, border: '2px solid #E6E6EC', borderTopColor: '#23232B', borderRadius: '50%', animation: 'spin .7s linear infinite', display: 'inline-block' }} />
                        <span style={{ fontSize: 16, color: '#9A9AA6' }}>Thinking…</span>
                      </div>
                    )}
                    {!m.loading && m.response && <AnswerCard msg={m} />}
                    {!m.loading && !m.response && m.text && (
                      <div style={{ background: '#FBEAEA', border: '1px solid #FBCECE', borderRadius: 15, padding: '12px 16px', fontSize: 15.5, color: '#B4232A' }}>{m.text}</div>
                    )}
                    <AgentTrace msg={m} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Composer */}
      <div style={{ flexShrink: 0, borderTop: '1px solid #E6E6EC', background: '#fff', padding: '14px 0 16px' }}>
        <div style={{ maxWidth: 840, margin: '0 auto', padding: '0 28px' }}>
          {messages.length > 0 && (
            <div style={{ display: 'flex', gap: 7, marginBottom: 11, flexWrap: 'wrap' }}>
              {SUGGESTIONS.slice(0, 3).map((s, i) => (
                <button key={i} onClick={() => send(s.q)} style={{ all: 'unset', cursor: 'pointer', fontSize: 15, fontWeight: 600, color: '#4A4A55', background: '#F1F1F4', border: '1px solid #E6E6EC', padding: '8px 15px', borderRadius: 20 }}>
                  {s.label.split(',')[0].slice(0, 40)}
                </button>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 11, background: '#fff', border: `1.5px solid ${draft.trim() ? '#23232B' : '#DDD'}`, borderRadius: 14, padding: '7px 7px 7px 17px' }}>
            <input
              value={draft}
              onChange={e => setDraft(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              placeholder="Ask Atlas about a customer, an issue, or request an escalation summary…"
              style={{ flex: 1, border: 'none', outline: 'none', fontFamily: "'Manrope', sans-serif", fontSize: 17, color: '#23232B', background: 'transparent', minWidth: 0 }}
            />
            <button onClick={() => send()} style={{ all: 'unset', cursor: 'pointer', width: 38, height: 38, borderRadius: 10, background: draft.trim() ? '#23232B' : '#D7D7DF', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><path d="M3 8.5h10M9 4.5l4 4-4 4" stroke={draft.trim() ? '#FFE600' : '#fff'} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </button>
          </div>
          <div style={{ textAlign: 'center', marginTop: 9, fontSize: 13.5, color: '#A6A6B2' }}>
            Atlas calls tools and reads data. Actions respect your <b style={{ color: '#6B6B78', fontWeight: 700 }}>{rl}</b> permissions.
          </div>
        </div>
      </div>
    </div>
  )
}
