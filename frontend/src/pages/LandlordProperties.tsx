import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { formatDate, money } from '../format'
import type { Property, Unit } from '../types'

function LeaseForm({ unit, onDone }: { unit: Unit; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [tenantEmail, setTenantEmail] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [rent, setRent] = useState('')
  const [dueDay, setDueDay] = useState('1')

  const create = useMutation({
    mutationFn: () =>
      api.createLease({
        unit_id: unit.id,
        tenant_email: tenantEmail.trim(),
        start_date: startDate,
        end_date: endDate,
        rent_amount: rent.trim() === '' ? undefined : rent.trim(),
        due_day: Number(dueDay),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['leases'] })
      onDone()
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    create.mutate()
  }

  return (
    <form className="form-grid" onSubmit={onSubmit}>
      <label>
        Tenant email
        <input
          type="email"
          value={tenantEmail}
          onChange={(e) => setTenantEmail(e.target.value)}
          required
        />
      </label>
      <label>
        Start date
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          required
        />
      </label>
      <label>
        End date
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
      </label>
      <label>
        Monthly rent (blank = unit rent {money(unit.monthly_rent)})
        <input
          type="number"
          min="0.01"
          step="0.01"
          value={rent}
          onChange={(e) => setRent(e.target.value)}
        />
      </label>
      <label>
        Due day of month (1-28)
        <input
          type="number"
          min="1"
          max="28"
          value={dueDay}
          onChange={(e) => setDueDay(e.target.value)}
          required
        />
      </label>
      <button type="submit" className="btn" disabled={create.isPending}>
        {create.isPending ? 'Creating...' : 'Create lease'}
      </button>{' '}
      <button type="button" className="btn btn-secondary" onClick={onDone}>
        Cancel
      </button>
      {create.isError && (
        <p role="alert" className="error">
          {create.error.message}
        </p>
      )}
    </form>
  )
}

function UnitRow({ unit }: { unit: Unit }) {
  const [showLease, setShowLease] = useState(false)
  return (
    <li>
      {unit.unit_number} - {unit.bedrooms} bed - {money(unit.monthly_rent)} per month{' '}
      {!showLease && (
        <button type="button" className="btn btn-secondary" onClick={() => setShowLease(true)}>
          New lease
        </button>
      )}
      {showLease && <LeaseForm unit={unit} onDone={() => setShowLease(false)} />}
    </li>
  )
}

function AddUnitForm({ propertyId }: { propertyId: number }) {
  const queryClient = useQueryClient()
  const [unitNumber, setUnitNumber] = useState('')
  const [bedrooms, setBedrooms] = useState('1')
  const [rent, setRent] = useState('')

  const create = useMutation({
    mutationFn: () =>
      api.createUnit(propertyId, {
        unit_number: unitNumber.trim(),
        bedrooms: Number(bedrooms),
        monthly_rent: rent.trim(),
      }),
    onSuccess: () => {
      setUnitNumber('')
      setBedrooms('1')
      setRent('')
      void queryClient.invalidateQueries({ queryKey: ['units', propertyId] })
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    create.mutate()
  }

  return (
    <form className="form-grid" onSubmit={onSubmit}>
      <h4>Add a unit</h4>
      <label>
        Unit number
        <input value={unitNumber} onChange={(e) => setUnitNumber(e.target.value)} required />
      </label>
      <label>
        Bedrooms
        <input
          type="number"
          min="0"
          max="20"
          value={bedrooms}
          onChange={(e) => setBedrooms(e.target.value)}
          required
        />
      </label>
      <label>
        Monthly rent
        <input
          type="number"
          min="0"
          step="0.01"
          value={rent}
          onChange={(e) => setRent(e.target.value)}
          required
        />
      </label>
      <button type="submit" className="btn" disabled={create.isPending}>
        {create.isPending ? 'Adding...' : 'Add unit'}
      </button>
      {create.isError && (
        <p role="alert" className="error">
          {create.error.message}
        </p>
      )}
    </form>
  )
}

function PropertyCard({ property }: { property: Property }) {
  const units = useQuery({
    queryKey: ['units', property.id],
    queryFn: () => api.units(property.id),
  })
  return (
    <li className="card">
      <h3>{property.name}</h3>
      <p className="muted">
        {property.address_line}, {property.city} {property.postcode}
      </p>
      {units.isPending && <p role="status">Loading units...</p>}
      {units.isError && (
        <p role="alert" className="error">
          Could not load units: {units.error.message}
        </p>
      )}
      {units.data && units.data.items.length === 0 && <p className="muted">No units yet.</p>}
      {units.data && units.data.items.length > 0 && (
        <ul className="plain-list">
          {units.data.items.map((u) => (
            <UnitRow key={u.id} unit={u} />
          ))}
        </ul>
      )}
      <AddUnitForm propertyId={property.id} />
    </li>
  )
}

function AddPropertyForm() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [city, setCity] = useState('')
  const [postcode, setPostcode] = useState('')

  const create = useMutation({
    mutationFn: () =>
      api.createProperty({
        name: name.trim(),
        address_line: address.trim(),
        city: city.trim(),
        postcode: postcode.trim(),
      }),
    onSuccess: () => {
      setName('')
      setAddress('')
      setCity('')
      setPostcode('')
      void queryClient.invalidateQueries({ queryKey: ['properties'] })
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    create.mutate()
  }

  return (
    <form className="card form-grid" onSubmit={onSubmit}>
      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <label>
        Address
        <input value={address} onChange={(e) => setAddress(e.target.value)} required />
      </label>
      <label>
        City
        <input value={city} onChange={(e) => setCity(e.target.value)} required />
      </label>
      <label>
        Postcode
        <input value={postcode} onChange={(e) => setPostcode(e.target.value)} required />
      </label>
      <button type="submit" className="btn" disabled={create.isPending}>
        {create.isPending ? 'Adding...' : 'Add property'}
      </button>
      {create.isError && (
        <p role="alert" className="error">
          {create.error.message}
        </p>
      )}
    </form>
  )
}

export default function LandlordProperties() {
  const properties = useQuery({ queryKey: ['properties'], queryFn: () => api.properties() })
  const leases = useQuery({ queryKey: ['leases'], queryFn: () => api.leases() })

  return (
    <>
      <h1>Properties</h1>

      <h2>Add a property</h2>
      <AddPropertyForm />

      <h2>My properties</h2>
      {properties.isPending && <p role="status">Loading properties...</p>}
      {properties.isError && (
        <p role="alert" className="error">
          Could not load properties: {properties.error.message}
        </p>
      )}
      {properties.data && properties.data.items.length === 0 && (
        <p className="muted">You have no properties yet.</p>
      )}
      {properties.data && properties.data.items.length > 0 && (
        <ul className="plain-list">
          {properties.data.items.map((p) => (
            <PropertyCard key={p.id} property={p} />
          ))}
        </ul>
      )}

      <h2>Leases</h2>
      {leases.isPending && <p role="status">Loading leases...</p>}
      {leases.isError && (
        <p role="alert" className="error">
          Could not load leases: {leases.error.message}
        </p>
      )}
      {leases.data && leases.data.items.length === 0 && <p className="muted">No leases yet.</p>}
      {leases.data && leases.data.items.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Your leases</caption>
            <thead>
              <tr>
                <th scope="col">Lease</th>
                <th scope="col">Unit</th>
                <th scope="col">Tenant</th>
                <th scope="col">Start</th>
                <th scope="col">End</th>
                <th scope="col">Rent</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {leases.data.items.map((l) => (
                <tr key={l.id}>
                  <td>#{l.id}</td>
                  <td>#{l.unit_id}</td>
                  <td>#{l.tenant_id}</td>
                  <td>{formatDate(l.start_date)}</td>
                  <td>{formatDate(l.end_date)}</td>
                  <td>{money(l.rent_amount)}</td>
                  <td>
                    <span className={`badge status-${l.status}`}>{l.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
