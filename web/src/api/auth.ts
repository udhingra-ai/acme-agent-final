import { apiFetch } from './client'

export async function login(username: string, password: string): Promise<{ access_token: string; token_type: string }> {
  return apiFetch('/auth/token', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}
