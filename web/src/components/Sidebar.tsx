import type { View } from '../types'
import { useAuth } from '../store/AuthContext'
import { avatarMeta } from '../utils'

const NAV: Array<{ key: View; label: string; icon: () => JSX.Element }> = [
  { key: 'assistant', label: 'Assistant', icon: () => (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><circle cx="8.5" cy="8.5" r="6.2" stroke="currentColor" strokeWidth="1.5"/><circle cx="8.5" cy="8.5" r="2.1" fill="currentColor"/></svg>
  )},
  { key: 'customers', label: 'Customers', icon: () => (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><circle cx="6" cy="6" r="3.1" stroke="currentColor" strokeWidth="1.5"/><circle cx="11.6" cy="9.6" r="2.4" stroke="currentColor" strokeWidth="1.5"/></svg>
  )},
  { key: 'issues', label: 'Issues', icon: () => (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><rect x="2.5" y="2.5" width="12" height="12" rx="2.5" stroke="currentColor" strokeWidth="1.5"/><line x1="5.4" y1="6.4" x2="11.6" y2="6.4" stroke="currentColor" strokeWidth="1.5"/><line x1="5.4" y1="10" x2="9.4" y2="10" stroke="currentColor" strokeWidth="1.5"/></svg>
  )},
  { key: 'observability', label: 'Observability', icon: () => (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><rect x="2.4" y="8.5" width="3" height="6" rx="1" fill="currentColor"/><rect x="7" y="5" width="3" height="9.5" rx="1" fill="currentColor"/><rect x="11.6" y="2.4" width="3" height="12.1" rx="1" fill="currentColor"/></svg>
  )},
  { key: 'evals', label: 'Evaluations', icon: () => (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><rect x="2.6" y="2.6" width="11.8" height="11.8" rx="2.5" stroke="currentColor" strokeWidth="1.5"/><path d="M5.6 8.7l1.9 1.9 3.6-3.9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>
  )},
  { key: 'architecture', label: 'Architecture', icon: () => (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><rect x="2.4" y="2.4" width="5" height="5" rx="1.2" stroke="currentColor" strokeWidth="1.5"/><rect x="9.6" y="2.4" width="5" height="5" rx="1.2" stroke="currentColor" strokeWidth="1.5"/><rect x="2.4" y="9.6" width="5" height="5" rx="1.2" stroke="currentColor" strokeWidth="1.5"/><rect x="9.6" y="9.6" width="5" height="5" rx="1.2" stroke="currentColor" strokeWidth="1.5"/></svg>
  )},
]

const ACCESS_SUMMARY: Record<string, string> = {
  sales_user:   'Read-only · customers & issues',
  support_user: 'Read + recommend next actions',
  admin:        'Full access · incl. next actions',
}

interface Props { view: View; setView: (v: View) => void }

export default function Sidebar({ view, setView }: Props) {
  const { user } = useAuth()

  return (
    <aside style={{ width: 248, flexShrink: 0, background: '#1C1C23', display: 'flex', flexDirection: 'column', padding: '20px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px 20px' }}>
        <div style={{ display: 'flex', gap: 2.5 }}>
          <span style={{ width: 9, height: 9, background: '#FFE600', display: 'block' }} />
          <span style={{ width: 9, height: 9, background: '#FFE600', opacity: .55, display: 'block' }} />
          <span style={{ width: 9, height: 9, background: '#FFE600', opacity: .28, display: 'block' }} />
        </div>
        <span style={{ fontWeight: 800, fontSize: 15, color: '#fff', letterSpacing: '-.01em' }}>Atlas</span>
        <span style={{ fontSize: 10, fontWeight: 700, color: '#7A7A88', background: '#2A2A33', padding: '2px 6px', borderRadius: 5, marginLeft: 'auto', fontFamily: "'JetBrains Mono', monospace" }}>v1.0</span>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {NAV.map(({ key, label, icon: Icon }) => {
          const active = view === key
          return (
            <button key={key} onClick={() => setView(key)} style={{ all: 'unset', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, padding: '9px 11px', borderRadius: 9, background: active ? '#2A2A33' : 'transparent', position: 'relative' }}>
              <span style={{ position: 'absolute', left: -14, top: '50%', transform: 'translateY(-50%)', width: 3, height: 18, borderRadius: '0 3px 3px 0', background: active ? '#FFE600' : 'transparent' }} />
              <span style={{ width: 18, height: 18, flexShrink: 0, color: active ? '#fff' : '#9A9AA6', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon />
              </span>
              <span style={{ fontSize: 14, fontWeight: 600, color: active ? '#fff' : '#9A9AA6' }}>{label}</span>
            </button>
          )
        })}
      </nav>

      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>

        {/* Signed-in identity card */}
        {user && (() => {
          const av = avatarMeta(user.role)
          return (
            <div style={{ background: '#23232B', borderRadius: 10, padding: '12px 13px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 9 }}>
                <span style={{ width: 32, height: 32, borderRadius: '50%', background: av.bg, color: av.fg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 12, flexShrink: 0 }}>
                  {user.initials}
                </span>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ display: 'block', fontSize: 13, fontWeight: 700, color: '#E8E8F0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.displayName}</span>
                  <span style={{ display: 'inline-flex', marginTop: 3, fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 600, color: av.fg, background: av.bg, padding: '1px 6px', borderRadius: 4 }}>{user.role}</span>
                </span>
              </div>
              <div style={{ fontSize: 11.5, color: '#9A9AA6', lineHeight: 1.45, marginBottom: 8 }}>
                {ACCESS_SUMMARY[user.role] ?? 'Standard access'}
              </div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: '#555566', lineHeight: 1.4 }}>
                Access enforced server-side<br />via Keycloak · RBAC
              </div>
            </div>
          )
        })()}

        {/* Environment indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 11px', background: '#23232B', borderRadius: 9, fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#8A8A99' }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#36B37E', flexShrink: 0 }} />
          local · docker compose
        </div>
      </div>
    </aside>
  )
}
