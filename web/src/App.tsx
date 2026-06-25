import { useState } from 'react'
import { AuthProvider, useAuth } from './store/AuthContext'
import { TraceProvider } from './store/TraceContext'
import Login from './screens/Login'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Assistant from './screens/Assistant'
import Customers from './screens/Customers'
import Issues from './screens/Issues'
import Observability from './screens/Observability'
import Evaluations from './screens/Evaluations'
import Architecture from './screens/Architecture'
import type { View } from './types'

function Shell() {
  const { user } = useAuth()
  const [view, setView] = useState<View>('assistant')

  if (!user) return <Login />

  const titles: Record<View, [string, string]> = {
    assistant:    ['Assistant',    'Ask Atlas about customers, issues and next actions'],
    customers:    ['Customers',    'Accounts, health and ownership'],
    issues:       ['Issues',       'Support queue, history and actions'],
    observability:['Observability','Traces, latency and tool-call logs'],
    evals:        ['Evaluations',  'Agent quality across a test set'],
    architecture: ['Architecture', 'System components and request flow'],
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#F4F4F7' }}>
      <Sidebar view={view} setView={setView} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TopBar title={titles[view][0]} sub={titles[view][1]} />
        <main style={{ flex: 1, overflow: 'auto' }}>
          {view === 'assistant'     && <Assistant key={user.username} />}
          {view === 'customers'     && <Customers />}
          {view === 'issues'        && <Issues />}
          {view === 'observability' && <Observability />}
          {view === 'evals'         && <Evaluations />}
          {view === 'architecture'  && <Architecture />}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <TraceProvider>
        <Shell />
      </TraceProvider>
    </AuthProvider>
  )
}
