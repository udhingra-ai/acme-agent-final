import { apiFetch } from './client'
import type { Customer } from '../types'

export async function fetchCustomers(): Promise<Customer[]> {
  return apiFetch('/customers')
}
