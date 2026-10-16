import type { Dashboard, IncomeSeries, Lease, Page, RentCharge, User } from './types'

const TOKEN_KEY = 'pm_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body: unknown = await res.json()
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) {
        return detail
          .map((d) =>
            typeof d === 'object' && d !== null && 'msg' in d
              ? String((d as { msg: unknown }).msg)
              : 'Invalid input',
          )
          .join(', ')
      }
    }
  } catch {
    // the response had no JSON body
  }
  return res.statusText || `Request failed (${res.status})`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`/api${path}`, { ...init, headers })

  if (!res.ok) {
    if (res.status === 401 && token) {
      // expired or invalid token: clear it and go back to the login page
      setToken(null)
      window.location.assign('/login')
    }
    throw new ApiError(res.status, await errorMessage(res))
  }
  return (await res.json()) as T
}

export const api = {
  async login(email: string, password: string) {
    setToken(null) // never send a stale token with a login attempt
    const body = new URLSearchParams({ username: email, password })
    return request<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body,
    })
  },
  me: () => request<User>('/auth/me'),
  dashboard: () => request<Dashboard>('/dashboard/summary'),
  income: (year: number) => request<IncomeSeries>(`/dashboard/income?year=${year}`),
  leases: () => request<Page<Lease>>('/leases'),
  charges: (leaseId: number) => request<Page<RentCharge>>(`/leases/${leaseId}/charges`),
  pay: (chargeId: number, amount: string, key: string) =>
    request<{ id: number }>('/payments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key },
      body: JSON.stringify({ rent_charge_id: chargeId, amount, method: 'card' }),
    }),
}
