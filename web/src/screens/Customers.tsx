import { useEffect, useState } from 'react'
import { fetchCustomers } from '../api/customers'
import { healthLabel, healthMeta, healthScore } from '../utils'
import { useNav } from '../store/NavContext'
import type { Customer } from '../types'

export default function Customers() {
  const { navigate } = useNav()
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchCustomers()
      .then(setCustomers)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ padding: 40, color: '#9A9AA6' }}>Loading customers…</div>
  if (error) return <div style={{ padding: 40, color: '#B4232A' }}>{error}</div>

  const atRisk = customers.filter(c => c.health_status === 'amber').length
  const critical = customers.filter(c => c.health_status === 'red').length
  const totalOpen = customers.reduce((a, c) => a + (c.open_issues ?? 0), 0)

  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <div style={{ maxWidth: 1440, margin: '0 auto', padding: '26px 28px' }}>

        {/* KPI row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 28 }}>
          {[
            { label: 'Total accounts', value: String(customers.length), sub: 'under management', color: '#23232B' },
            { label: 'At risk',        value: String(atRisk),           sub: 'amber health',    color: '#C2410C' },
            { label: 'Critical',       value: String(critical),         sub: 'red health',      color: '#B4232A' },
            { label: 'Open issues',    value: String(totalOpen),        sub: 'across all accounts', color: '#23232B' },
          ].map(k => (
            <div key={k.label} style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 13, padding: '20px 22px' }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#9A9AA6', textTransform: 'uppercase', letterSpacing: '.07em' }}>{k.label}</div>
              <div style={{ fontSize: 36, fontWeight: 800, margin: '8px 0 4px', letterSpacing: '-.02em', color: k.color, lineHeight: 1 }}>{k.value}</div>
              <div style={{ fontSize: 14, color: '#A6A6B2' }}>{k.sub}</div>
            </div>
          ))}
        </div>

        {/* Customer grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18 }}>
          {customers.map(c => {
            const hm = healthMeta(c.health_status)
            const hl = healthLabel(c.health_status)
            const score = healthScore(c.health_status)
            const scoreColor = score >= 80 ? '#1F7A4D' : score >= 60 ? '#C2410C' : '#B4232A'
            return (
              <div key={c.id} style={{ background: '#fff', border: '1px solid #E6E6EC', borderRadius: 16, padding: '22px 22px', display: 'flex', flexDirection: 'column', gap: 0 }}>

                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <button onClick={() => navigate('issues', undefined, c.name)} style={{ all: 'unset', cursor: 'pointer', fontSize: 22, fontWeight: 800, letterSpacing: '-.01em', color: '#23232B', textDecoration: 'underline', textDecorationStyle: 'dotted', textUnderlineOffset: '3px' }}>{c.name}</button>
                      <span style={{ fontSize: 12, fontWeight: 700, color: '#6B6B78', background: '#F1F1F4', border: '1px solid #E6E6EC', padding: '2px 8px', borderRadius: 5 }}>{c.segment}</span>
                    </div>
                  </div>
                  <button onClick={() => navigate('issues', undefined, c.name)} style={{ all: 'unset', cursor: 'pointer', fontSize: 13.5, fontWeight: 700, color: hm.fg, background: hm.bg, padding: '5px 12px', borderRadius: 20, flexShrink: 0, marginTop: 2 }}>{hl}</button>
                </div>

                {/* Health score bar */}
                <div style={{ marginBottom: 18 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#9A9AA6', marginBottom: 7 }}>
                    <span style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em', fontSize: 13 }}>Health score</span>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: scoreColor, fontSize: 15 }}>{score}/100</span>
                  </div>
                  <div style={{ height: 7, background: '#EDEDF1', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${score}%`, background: scoreColor, borderRadius: 4 }} />
                  </div>
                </div>

                {/* Footer row */}
                <div style={{ borderTop: '1px solid #EDEDF1', paddingTop: 14, display: 'flex', alignItems: 'center' }}>
                  <span style={{ fontSize: 15.5, color: '#8C8C99' }}>Owner <span style={{ color: '#3A3A44', fontWeight: 600 }}>{c.account_owner}</span></span>
                  <button onClick={() => navigate('issues', undefined, c.name)} style={{ all: 'unset', cursor: 'pointer', marginLeft: 'auto', fontSize: 13.5, fontWeight: 700, color: (c.open_issues ?? 0) > 0 ? '#B4232A' : '#1F7A4D', background: (c.open_issues ?? 0) > 0 ? '#FBEAEA' : '#E7F4EC', border: `1px solid ${(c.open_issues ?? 0) > 0 ? '#FBCECE' : '#BBE5D0'}`, padding: '4px 11px', borderRadius: 20 }}>{c.open_issues ?? 0} open</button>
                </div>

              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
