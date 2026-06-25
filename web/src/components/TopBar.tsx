import { useAuth } from '../store/AuthContext'
import { avatarMeta } from '../utils'

interface Props { title: string; sub: string }

export default function TopBar({ title, sub }: Props) {
  const { user, signOut } = useAuth()
  const uav = user ? avatarMeta(user.role) : { bg: '#EDEDF1', fg: '#5A5A66' }

  return (
    <header style={{ height: 62, flexShrink: 0, background: '#fff', borderBottom: '1px solid #E6E6EC', display: 'flex', alignItems: 'center', padding: '0 24px', gap: 18, zIndex: 20 }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: '-.01em' }}>{title}</div>
        <div style={{ fontSize: 12, color: '#8C8C99', marginTop: 1 }}>{sub}</div>
      </div>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#6B6B78', background: '#F1F1F4', border: '1px solid #E6E6EC', padding: '6px 10px', borderRadius: 8 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#36B37E' }} />
          gpt-4.1-mini · agent
        </div>

        {/* User display — read-only, no switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 9px 6px 6px', borderRadius: 10, border: '1px solid #E6E6EC' }}>
          <span style={{ width: 32, height: 32, borderRadius: 8, background: uav.bg, color: uav.fg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13 }}>
            {user?.initials ?? '?'}
          </span>
          <span style={{ textAlign: 'left' }}>
            <span style={{ display: 'block', fontSize: 13, fontWeight: 700, lineHeight: 1.1 }}>{user?.displayName ?? ''}</span>
            <span style={{ display: 'block', fontSize: 10.5, fontWeight: 600, color: uav.fg, fontFamily: "'JetBrains Mono', monospace", marginTop: 2 }}>{user?.role ?? ''}</span>
          </span>
        </div>

        <button
          onClick={signOut}
          style={{ all: 'unset', cursor: 'pointer', fontSize: 12.5, fontWeight: 600, color: '#8C8C99', padding: '6px 13px', borderRadius: 8, border: '1px solid #E6E6EC', background: '#fff' }}
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
