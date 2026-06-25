import React, { createContext, useContext, useState } from 'react'
import type { TraceRecord } from '../types'

interface TraceCtx {
  traces: TraceRecord[]
  addTrace: (t: TraceRecord) => void
}

const Ctx = createContext<TraceCtx>({ traces: [], addTrace: () => {} })

export function TraceProvider({ children }: { children: React.ReactNode }) {
  const [traces, setTraces] = useState<TraceRecord[]>([])
  function addTrace(t: TraceRecord) {
    setTraces(prev => [t, ...prev])
  }
  return <Ctx.Provider value={{ traces, addTrace }}>{children}</Ctx.Provider>
}

export function useTraces() { return useContext(Ctx) }
