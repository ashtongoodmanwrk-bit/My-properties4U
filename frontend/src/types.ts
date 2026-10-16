export type Role = 'landlord' | 'tenant' | 'admin'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  created_at: string
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Dashboard {
  as_of: string
  month: string
  total_units: number
  occupied_units: number
  occupancy_rate: number
  expected_income: string
  collected_income: string
  collection_rate: number
  overdue_amount: string
  overdue_charges: number
  open_requests: Record<string, number>
  open_requests_total: number
}

export interface IncomePoint {
  month: string
  expected: string
  collected: string
}

export interface IncomeSeries {
  year: number
  months: IncomePoint[]
}

export interface Lease {
  id: number
  unit_id: number
  tenant_id: number
  start_date: string
  end_date: string
  rent_amount: string
  due_day: number
  status: string
  created_at: string
}

export interface RentCharge {
  id: number
  lease_id: number
  due_date: string
  amount: string
  status: string
}

export interface MaintenanceRequest {
  id: number
  unit_id: number
  reported_by: number
  title: string
  description: string
  category: string
  priority: string
  status: string
  assigned_to: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export interface AuditEntry {
  id: number
  actor_id: number | null
  entity: string
  entity_id: number
  action: string
  old_values: Record<string, unknown> | null
  new_values: Record<string, unknown> | null
  created_at: string
}

export interface Property {
  id: number
  owner_id: number
  name: string
  address_line: string
  city: string
  postcode: string
  created_at: string
}

export interface Unit {
  id: number
  property_id: number
  unit_number: string
  bedrooms: number
  monthly_rent: string
}
