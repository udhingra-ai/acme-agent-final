import { createContext, useContext, useState } from 'react'
import type { View } from '../types'

interface NavCtx {
  view: View
  setView: (v: View) => void
  issueTarget: number | null
  customerTarget: string | null
  navigate: (view: View, issueId?: number, customerName?: string) => void
  clearIssueTarget: () => void
  clearCustomerTarget: () => void
}

const NavContext = createContext<NavCtx | null>(null)

export function NavProvider({ children }: { children: React.ReactNode }) {
  const [view, setViewState] = useState<View>('assistant')
  const [issueTarget, setIssueTarget] = useState<number | null>(null)
  const [customerTarget, setCustomerTarget] = useState<string | null>(null)

  function setView(v: View) {
    setIssueTarget(null)
    setCustomerTarget(null)
    setViewState(v)
  }

  function navigate(v: View, issueId?: number, customerName?: string) {
    setIssueTarget(issueId ?? null)
    setCustomerTarget(customerName ?? null)
    setViewState(v)
  }

  function clearIssueTarget() { setIssueTarget(null) }
  function clearCustomerTarget() { setCustomerTarget(null) }

  return (
    <NavContext.Provider value={{ view, setView, issueTarget, customerTarget, navigate, clearIssueTarget, clearCustomerTarget }}>
      {children}
    </NavContext.Provider>
  )
}

export function useNav() {
  const ctx = useContext(NavContext)
  if (!ctx) throw new Error('useNav must be inside NavProvider')
  return ctx
}
