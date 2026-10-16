import { Fragment, useState } from 'react'
import type { FormEvent } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../api'

const PAGE_SIZE = 20

function Values({ label, value }: { label: string; value: Record<string, unknown> | null }) {
  return (
    <div>
      <h4>{label}</h4>
      <pre className="json">{value ? JSON.stringify(value, null, 2) : '-'}</pre>
    </div>
  )
}

export default function AdminAudit() {
  const [entityInput, setEntityInput] = useState('')
  const [actorInput, setActorInput] = useState('')
  const [filters, setFilters] = useState({ entity: '', actorId: '' })
  const [offset, setOffset] = useState(0)
  const [expanded, setExpanded] = useState<number | null>(null)

  const audit = useQuery({
    queryKey: ['audit', filters, offset],
    queryFn: () => api.audit({ ...filters, limit: PAGE_SIZE, offset }),
    placeholderData: keepPreviousData,
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setFilters({ entity: entityInput, actorId: actorInput })
    setOffset(0)
    setExpanded(null)
  }

  function onClear() {
    setEntityInput('')
    setActorInput('')
    setFilters({ entity: '', actorId: '' })
    setOffset(0)
    setExpanded(null)
  }

  const total = audit.data?.total ?? 0
  const first = total === 0 ? 0 : offset + 1
  const last = Math.min(offset + PAGE_SIZE, total)

  return (
    <>
      <h1>Audit log</h1>

      <form className="card audit-filters" onSubmit={onSubmit}>
        <label>
          Entity
          <input
            value={entityInput}
            onChange={(e) => setEntityInput(e.target.value)}
            placeholder="e.g. payment"
          />
        </label>
        <label>
          Actor ID
          <input
            type="number"
            min="1"
            value={actorInput}
            onChange={(e) => setActorInput(e.target.value)}
          />
        </label>
        <button type="submit" className="btn">
          Apply filters
        </button>
        <button type="button" className="btn btn-secondary" onClick={onClear}>
          Clear
        </button>
      </form>

      {audit.isPending && <p role="status">Loading audit log...</p>}
      {audit.isError && (
        <p role="alert" className="error">
          Could not load the audit log: {audit.error.message}
        </p>
      )}
      {audit.data && audit.data.items.length === 0 && (
        <p className="muted">No audit entries match these filters.</p>
      )}
      {audit.data && audit.data.items.length > 0 && (
        <>
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Audit log entries, newest first</caption>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Actor</th>
                  <th scope="col">Entity</th>
                  <th scope="col">ID</th>
                  <th scope="col">Action</th>
                  <th scope="col">Details</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.items.map((a) => (
                  <Fragment key={a.id}>
                    <tr>
                      <td>{new Date(a.created_at).toLocaleString('en-GB')}</td>
                      <td>{a.actor_id ?? 'system'}</td>
                      <td>{a.entity}</td>
                      <td>{a.entity_id}</td>
                      <td>{a.action}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          aria-expanded={expanded === a.id}
                          onClick={() => setExpanded(expanded === a.id ? null : a.id)}
                        >
                          {expanded === a.id ? 'Hide' : 'Show'}
                        </button>
                      </td>
                    </tr>
                    {expanded === a.id && (
                      <tr>
                        <td colSpan={6}>
                          <div className="values-grid">
                            <Values label="Old values" value={a.old_values} />
                            <Values label="New values" value={a.new_values} />
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>

          <nav className="pager" aria-label="Audit log pages">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </button>
            <span role="status">
              {first}-{last} of {total}
            </span>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </nav>
        </>
      )}
    </>
  )
}
