import type { Property, Unit, AuditEntry,
  Dashboard,
  IncomeSeries,
  Lease,
  MaintenanceRequest,
  Page,
  RentCharge,
  User,
} from './types'

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
  properties: () => request<Page<Property>>('/properties'),
  createProperty: (data: { name: string; address_line: string; city: string; postcode: string }) =>
    request<Property>('/properties', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  units: (propertyId: number) => request<Page<Unit>>(`/properties/${propertyId}/units`),
  createUnit: (
    propertyId: number,
    data: { unit_number: string; bedrooms: number; monthly_rent: string },
  ) =>
    request<Unit>(`/properties/${propertyId}/units`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  createLease: (data: {
    unit_id: number
    tenant_email: string
    start_date: string
    end_date: string
    rent_amount?: string
    due_day: number
  }) =>
    request<Lease>('/leases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  audit: (params: { entity: string; actorId: string; limit: number; offset: number }) => {
    const q = new URLSearchParams({
      limit: String(params.limit),
      offset: String(params.offset),
    })
    if (params.entity.trim()) q.set('entity', params.entity.trim())
    if (params.actorId.trim()) q.set('actor_id', params.actorId.trim())
    return request<Page<AuditEntry>>(`/audit?${q.toString()}`)
  },
  maintenance: () => request<Page<MaintenanceRequest>>('/maintenance'),
  reportIssue: (data: { title: string; description: string; category: string; priority: string }) =>
    request<MaintenanceRequest>('/maintenance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
  updateRequest: (id: number, data: { status: string; assigned_to?: string }) =>
    request<MaintenanceRequest>(`/maintenance/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
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

export async function downloadStatement(month: string): Promise<void> {
  const token = getToken()
  const res = await fetch(`/api/statements?month=${encodeURIComponent(month)}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  const url = URL.createObjectURL(await res.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = `statement-${month}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
