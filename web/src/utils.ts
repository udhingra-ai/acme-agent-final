import { C, mono } from './tokens'
import type { HealthStatus, RiskLevel, Role, Severity } from './types'

export function statusMeta(s: string): { fg: string; bg: string } {
  const v = (s || '').toLowerCase().replace(/\s+/g, '')
  if (v === 'open') return C.statusOpen
  if (v.includes('progress')) return C.statusInProg
  if (v.includes('waiting')) return C.statusWaiting
  if (v === 'resolved') return C.statusResolved
  return C.statusDefault
}

export function severityToPriority(sev: Severity): string {
  const map: Record<Severity, string> = { critical: 'P1', high: 'P2', medium: 'P3', low: 'P4' }
  return map[sev] ?? 'P4'
}

export function prioMeta(sev: Severity): { fg: string; bg: string } {
  if (sev === 'critical') return C.prioP1
  if (sev === 'high') return C.prioP2
  if (sev === 'medium') return C.prioP3
  return C.prioP4
}

export function healthLabel(h: HealthStatus): string {
  if (h === 'green') return 'Healthy'
  if (h === 'amber') return 'At Risk'
  return 'Critical'
}

export function healthMeta(h: HealthStatus): { fg: string; bg: string } {
  if (h === 'green') return C.riskLow
  if (h === 'amber') return C.riskHigh
  return C.riskCritical
}

export function healthScore(h: HealthStatus): number {
  if (h === 'green') return 88
  if (h === 'amber') return 62
  return 38
}

export function riskMeta(r: RiskLevel): { fg: string; bg: string } {
  if (r === 'Low') return C.riskLow
  if (r === 'Medium') return C.riskMedium
  if (r === 'High') return C.riskHigh
  return C.riskCritical
}

export function avatarMeta(role: Role): { bg: string; fg: string } {
  if (role === 'sales_user') return C.rolesSales
  if (role === 'support_user') return C.rolesSupport
  return C.rolesAdmin
}

export function roleLabel(role: Role): string {
  if (role === 'sales_user') return 'Sales'
  if (role === 'support_user') return 'Support'
  return 'Admin'
}

export function issId(n: number): string {
  return 'ISS-' + String(n).padStart(4, '0')
}

export function fmtMs(ms: number): string {
  return (ms / 1000).toFixed(2) + 's'
}

export function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return iso.slice(0, 10)
  }
}

export function initials(name: string): string {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

export const monoStyle: React.CSSProperties = { fontFamily: mono }
