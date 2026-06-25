import { useState } from 'react'
import { useAuth } from '../store/AuthContext'
import { login } from '../api/auth'
import { avatarMeta } from '../utils'
import type { Role } from '../types'

const DEMO_USERS = [
  { username: 'alice.sales',  displayName: 'Alice Sales',  first: 'Alice', initials: 'AS', role: 'sales_user'  as Role },
  { username: 'bob.support',  displayName: 'Bob Support',  first: 'Bob',   initials: 'BS', role: 'support_user' as Role },
  { username: 'carol.admin',  displayName: 'Carol Admin',  first: 'Carol', initials: 'CA', role: 'admin'        as Role },
]

function decodeJwt(token: string): Record<string, unknown> | null {
  try {
    return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
  } catch { return null }
}

export default function Login() {
  const { signIn } = useAuth()
  const [username, setUsername]       = useState('')
  const [password, setPassword]       = useState('')
  const [loading, setLoading]         = useState(false)
  const [loadingUser, setLoadingUser] = useState<string | null>(null)
  const [error, setError]             = useState('')
  const [resetSent, setResetSent]     = useState(false)

  async function submitCredentials(uname: string, pass: string) {
    setError('')
    setResetSent(false)
    try {
      const tok = await login(uname, pass)

      const known = DEMO_USERS.find(u => u.username === uname)
      if (known) {
        signIn({ ...known, token: tok.access_token })
        return
      }

      // Non-demo user — derive display metadata from JWT claims
      const claims = decodeJwt(tok.access_token)
      const preferredUsername = (claims?.preferred_username as string) || uname
      const roles = ((claims?.realm_access as Record<string, string[]>)?.roles) ?? []
      const role = (['admin', 'support_user', 'sales_user'].find(r => roles.includes(r)) ?? 'sales_user') as Role
      const inits = preferredUsername.split('.').map((p: string) => p[0]?.toUpperCase() ?? '').join('').slice(0, 2) || '?'

      signIn({
        username: preferredUsername,
        displayName: preferredUsername,
        first: preferredUsername.split('.')[0] || preferredUsername,
        initials: inits,
        role,
        token: tok.access_token,
      })
    } catch {
      setError('Incorrect username or password. Please try again.')
      setPassword('')
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    await submitCredentials(username, password)
    setLoading(false)
  }

  async function handleDemo(u: typeof DEMO_USERS[0]) {
    setUsername(u.username)
    setPassword('Password123!')
    setLoadingUser(u.username)
    await submitCredentials(u.username, 'Password123!')
    setLoadingUser(null)
  }

  const busy = loading || !!loadingUser

  return (
    <div style={{ height: '100vh', display: 'flex', background: '#1C1C23', overflow: 'hidden' }}>

      {/* Left panel — branding */}
      <div style={{ flex: '0 0 46%', display: 'flex', flexDirection: 'column', padding: '48px 64px', position: 'relative', overflow: 'hidden', borderRight: '1px solid #2A2A33' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 11, position: 'relative', zIndex: 2 }}>
          <div style={{ display: 'flex', gap: 3 }}>
            <span style={{ width: 11, height: 11, background: '#FFE600', display: 'block' }} />
            <span style={{ width: 11, height: 11, background: '#FFE600', opacity: .55, display: 'block' }} />
            <span style={{ width: 11, height: 11, background: '#FFE600', opacity: .28, display: 'block' }} />
          </div>
          <span style={{ fontWeight: 800, letterSpacing: '.16em', fontSize: 13, color: '#fff' }}>ACME OPERATIONS</span>
        </div>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center', position: 'relative', zIndex: 2 }}>
          <div style={{ maxWidth: 460 }}>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '.16em', color: '#FFE600', textTransform: 'uppercase', marginBottom: 18 }}>Atlas</div>
            <h1 style={{ fontSize: 44, lineHeight: 1.07, fontWeight: 800, color: '#fff', margin: '0 0 20px', letterSpacing: '-.025em' }}>The agentic operations assistant.</h1>
            <p style={{ fontSize: 16, lineHeight: 1.65, color: '#A6A6B2', margin: '0 0 36px' }}>Ask in plain language. Atlas reasons over your customer and issue data, calls the right tools, and returns auditable, grounded answers — with every step on the record.</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {['Dynamic tool-use over Postgres, MCP & Skills', 'Role-based access enforced on every action', 'Full traces, latency & evals for observability'].map(t => (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 14.5, color: '#C8C8D4' }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#FFE600', flexShrink: 0 }} />{t}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ position: 'relative', zIndex: 2, display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#7A7A88', fontFamily: "'JetBrains Mono', monospace" }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#36B37E', flexShrink: 0 }} />
          Secured by Keycloak · OpenID Connect · realm <span style={{ color: '#A6A6B2', marginLeft: 4 }}>acme</span>
        </div>

        <div style={{ position: 'absolute', right: -100, bottom: -100, width: 340, height: 340, border: '1px solid #2C2C36', borderRadius: '50%', zIndex: 1 }} />
        <div style={{ position: 'absolute', right: -44, bottom: -44, width: 220, height: 220, border: '1px solid #2C2C36', borderRadius: '50%', zIndex: 1 }} />
      </div>

      {/* Right panel — form */}
      <div style={{ flex: '1 1 54%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#F4F4F7', overflowY: 'auto', paddingBottom: '6vh' }}>
        <div style={{ width: '100%', maxWidth: 520, padding: '0 52px' }}>

          <h2 style={{ fontSize: 30, fontWeight: 800, margin: '0 0 6px', letterSpacing: '-.02em' }}>Sign in to Atlas</h2>
          <p style={{ fontSize: 15, color: '#6B6B78', margin: '0 0 28px', lineHeight: 1.55 }}>Enter your credentials to continue.</p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 700, color: '#4A4A55', marginBottom: 7, letterSpacing: '.02em' }}>USERNAME OR EMAIL</label>
              <input
                type="text"
                value={username}
                onChange={e => { setUsername(e.target.value); setError('') }}
                placeholder="e.g. alice.sales"
                autoFocus
                autoCapitalize="none"
                autoCorrect="off"
                disabled={busy}
                style={{ width: '100%', boxSizing: 'border-box', padding: '13px 15px', fontSize: 15, border: `1.5px solid ${error ? '#B4232A' : '#D8D8E2'}`, borderRadius: 12, outline: 'none', fontFamily: "'Manrope', sans-serif", background: busy ? '#F8F8FA' : '#fff' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12.5, fontWeight: 700, color: '#4A4A55', marginBottom: 7, letterSpacing: '.02em' }}>PASSWORD</label>
              <input
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError('') }}
                placeholder="Enter your password"
                disabled={busy}
                style={{ width: '100%', boxSizing: 'border-box', padding: '13px 15px', fontSize: 15, border: `1.5px solid ${error ? '#B4232A' : '#D8D8E2'}`, borderRadius: 12, outline: 'none', fontFamily: "'Manrope', sans-serif", background: busy ? '#F8F8FA' : '#fff' }}
              />
              {error && <div style={{ marginTop: 8, fontSize: 13, color: '#B4232A' }}>{error}</div>}

              <div style={{ marginTop: 10, display: 'flex', justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => setResetSent(true)} disabled={busy} style={{ all: 'unset', cursor: busy ? 'default' : 'pointer', fontSize: 12.5, color: '#6B6B78', fontWeight: 600 }}>
                  Forgot password?
                </button>
              </div>

              {resetSent && (
                <div style={{ marginTop: 8, padding: '11px 14px', background: '#EDF6F1', border: '1px solid #C0E0D0', borderRadius: 10, fontSize: 13, color: '#1F7A4D', lineHeight: 1.5 }}>
                  If an account exists for <strong>{username || 'that user'}@acme-ops.internal</strong>, a password reset link has been sent to the registered email.
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={busy || !username || !password}
              style={{ all: 'unset', cursor: busy || !username || !password ? 'default' : 'pointer', textAlign: 'center', background: busy || !username || !password ? '#D0D0DA' : '#23232B', color: '#fff', padding: '14px', borderRadius: 12, fontWeight: 700, fontSize: 15, opacity: loading ? .7 : 1, transition: 'background .15s' }}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {/* Demo accounts — clearly secondary */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '30px 0 14px' }}>
            <div style={{ flex: 1, height: 1, background: '#E0E0E8' }} />
            <span style={{ fontSize: 12, color: '#9A9AA6', fontWeight: 600, whiteSpace: 'nowrap' }}>or use a demo account</span>
            <div style={{ flex: 1, height: 1, background: '#E0E0E8' }} />
          </div>

          <p style={{ fontSize: 12.5, color: '#9A9AA6', margin: '0 0 12px', lineHeight: 1.55 }}>
            Walkthrough shortcuts — same Keycloak flow. See README for credentials.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {DEMO_USERS.map(u => {
              const av = avatarMeta(u.role)
              const isLoading = loadingUser === u.username
              return (
                <button
                  key={u.username}
                  onClick={() => !busy && handleDemo(u)}
                  disabled={busy}
                  style={{ all: 'unset', cursor: busy ? 'default' : 'pointer', display: 'flex', alignItems: 'center', gap: 13, background: '#fff', border: '1px solid #E2E2E9', borderRadius: 12, padding: '11px 16px', opacity: loadingUser && !isLoading ? 0.4 : 1, transition: 'opacity .15s', boxShadow: '0 1px 3px rgba(0,0,0,.04)' }}
                >
                  <span style={{ width: 36, height: 36, borderRadius: '50%', background: av.bg, color: av.fg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13, flexShrink: 0 }}>
                    {isLoading
                      ? <span style={{ width: 13, height: 13, border: `2px solid ${av.fg}40`, borderTopColor: av.fg, borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />
                      : u.initials}
                  </span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ display: 'block', fontWeight: 700, fontSize: 14, color: '#23232B' }}>{u.displayName}</span>
                    <span style={{ display: 'block', fontSize: 11.5, color: '#9A9AA6', fontFamily: "'JetBrains Mono', monospace", marginTop: 1 }}>{u.username}</span>
                  </span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, fontWeight: 600, color: av.fg, background: av.bg, padding: '2px 8px', borderRadius: 5, flexShrink: 0 }}>{u.role}</span>
                  {!isLoading && <span style={{ color: '#C2C2CC', fontSize: 18, flexShrink: 0, marginLeft: 2 }}>›</span>}
                </button>
              )
            })}
          </div>

        </div>
      </div>
    </div>
  )
}
