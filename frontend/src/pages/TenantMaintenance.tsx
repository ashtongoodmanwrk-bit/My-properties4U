import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'

const CATEGORIES = ['plumbing', 'electrical', 'heating', 'appliance', 'structural', 'other']
const PRIORITIES = ['low', 'medium', 'high', 'urgent']

export default function TenantMaintenance() {
  const queryClient = useQueryClient()
  const requests = useQuery({ queryKey: ['maintenance'], queryFn: () => api.maintenance() })
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('plumbing')
  const [priority, setPriority] = useState('medium')

  const report = useMutation({
    mutationFn: () => api.reportIssue({ title, description, category, priority }),
    onSuccess: () => {
      setTitle('')
      setDescription('')
      setCategory('plumbing')
      setPriority('medium')
      void queryClient.invalidateQueries({ queryKey: ['maintenance'] })
    },
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    report.mutate()
  }

  return (
    <>
      <h1>Maintenance</h1>

      <h2>Report an issue</h2>
      <form className="card form-grid" onSubmit={onSubmit}>
        <label>
          Title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
            required
          />
        </label>
        <label>
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            maxLength={5000}
            required
          />
        </label>
        <label>
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="btn" disabled={report.isPending}>
          {report.isPending ? 'Sending...' : 'Submit request'}
        </button>
        {report.isError && (
          <p role="alert" className="error">
            {report.error.message}
          </p>
        )}
        {report.isSuccess && <p role="status">Request sent to your landlord.</p>}
      </form>

      <h2>My requests</h2>
      {requests.isPending && <p role="status">Loading requests...</p>}
      {requests.isError && (
        <p role="alert" className="error">
          Could not load requests: {requests.error.message}
        </p>
      )}
      {requests.data && requests.data.items.length === 0 && (
        <p className="muted">You have not reported any issues.</p>
      )}
      {requests.data && requests.data.items.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Your maintenance requests and their status</caption>
            <thead>
              <tr>
                <th scope="col">Reported</th>
                <th scope="col">Issue</th>
                <th scope="col">Priority</th>
                <th scope="col">Status</th>
                <th scope="col">Assigned to</th>
              </tr>
            </thead>
            <tbody>
              {requests.data.items.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.created_at).toLocaleDateString('en-GB')}</td>
                  <td>{r.title}</td>
                  <td>{r.priority}</td>
                  <td>
                    <span className={`badge status-${r.status}`}>{r.status.replace('_', ' ')}</span>
                  </td>
                  <td>{r.assigned_to ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
