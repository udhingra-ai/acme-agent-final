import React, { createContext, useContext, useState } from 'react'
import type { AuthUser } from '../types'
import { setToken } from '../api/client'

interface AuthCtx {
  user: AuthUser | null
  signIn: (u: AuthUser) => void
  signOut: () => void
}

const Ctx = createContext<AuthCtx>({ user: null, signIn: () => {}, signOut: () => {} })

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)

  function signIn(u: AuthUser) {
    setToken(u.token)
    setUser(u)
  }

  function signOut() {
    setToken('')
    setUser(null)
  }

  return <Ctx.Provider value={{ user, signIn, signOut }}>{children}</Ctx.Provider>
}

export function useAuth() { return useContext(Ctx) }
