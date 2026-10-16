import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { MaintenanceRequest } from '../types'

const COLUMNS = [
  { status: 'submitted', label: 'Submitted' },
  { status: 'assigned', label: 'Assigned' },
  { status: 'in_progress', label: 'In progress' },
  { status: 'resolved', label: 'Resolved' },
]

function RequestCard({ request }: { request: MaintenanceRequest }) {
  const queryClient = useQueryClient()
  const [contractor, setContractor] = useState('')

  const update = useMutation({
    mutationFn: (data: { status: string; assigned_to?: string }) =>
      api.updateRequest(request.id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['maintenance'] })
    },
  })

  return (
    <li className="card">
      <h3>{request.title}</h3>
      <p className="muted">
        Unit #{request.unit_id} - {request.category} - {request.priority} priority
      </p>
      <p>{request.description}</p>
      {request.assigned_to && <p>Contractor: {request.assigned_to}</p>}

      {request.status === 'submitted' && (
        <>
          <label className="sr-only" htmlFor={`contractor-${request.id}`}>
            Contractor name for {request.title}
          </label>
          <input
            id={`contractor-${request.id}`}
            placeholder="Contractor name"
            value={contractor}
            onChange={(e) => setContractor(e.target.value)}
            disabled={update.isPending}
          />{' '}
          <button
            type="button"
            className="btn"
            disabled={update.isPending || contractor.trim() === ''}
            onClick={() => update.mutate({ status: 'assigned', assigned_to: contractor.trim() })}
          >
            Assign
          </button>
        </>
      )}
      {request.status === 'assigned' && (
        <button
          type="button"
          className="btn"
          disabled={update.isPending}
          onClick={() => update.mutate({ status: 'in_progress' })}
        >
          Start work
        </button>
      )}
      {request.status === 'in_progress' && (
        <button
          type="button"
          className="btn"
          disabled={update.isPending}
          onClick={() => update.mutate({ status: 'resolved' })}
        >
          Mark resolved
        </button>
      )}
      {update.isError && (
        <p role="alert" className="error">
          {update.error.message}
        </p>
      )}
    </li>
  )
}

export default function LandlordMaintenance() {
  const requests = useQuery({ queryKey: ['maintenance'], queryFn: () => api.maintenance() })

  if (requests.isPending) return <p role="status">Loading requests...</p>
  if (requests.isError) {
    return (
      <p role="alert" className="error">
        Could not load requests: {requests.error.message}
      </p>
    )
  }

  const items = requests.data.items

  return (
    <>
      <h1>Maintenance board</h1>
      {items.length === 0 && <p className="muted">No maintenance requests yet.</p>}
      <div className="board">
        {COLUMNS.map((col) => {
          const inColumn = items.filter((r) => r.status === col.status)
          return (
            <section key={col.status} aria-labelledby={`col-${col.status}`}>
              <h2 id={`col-${col.status}`}>
                {col.label} ({inColumn.length})
              </h2>
              <ul className="plain-list">
                {inColumn.map((r) => (
                  <RequestCard key={r.id} request={r} />
                ))}
              </ul>
            </section>
          )
        })}
      </div>
    </>
  )
}
