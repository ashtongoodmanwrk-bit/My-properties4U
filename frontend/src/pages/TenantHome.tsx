import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { formatDate, money } from '../format'
import PayButton from '../PayButton'

export default function TenantHome() {
  const leases = useQuery({ queryKey: ['leases'], queryFn: () => api.leases() })
  const lease = leases.data?.items[0]
  const charges = useQuery({
    queryKey: ['charges', lease?.id],
    queryFn: () => api.charges(lease?.id ?? 0),
    enabled: lease !== undefined,
  })

  if (leases.isPending) return <p role="status">Loading your lease...</p>
  if (leases.isError) {
    return (
      <p role="alert" className="error">
        Could not load your lease: {leases.error.message}
      </p>
    )
  }
  if (!lease) return <p>You do not have a lease yet.</p>

  return (
    <>
      <h1>My lease</h1>
      <div className="card">
        <p>
          <strong>{money(lease.rent_amount)}</strong> per month, due on day {lease.due_day}
        </p>
        <p className="muted">
          {formatDate(lease.start_date)} to {formatDate(lease.end_date)}
        </p>
      </div>

      <h2>Rent schedule</h2>
      <p className="muted">Payments are simulated. No real money or card details are used.</p>
      {charges.isPending && <p role="status">Loading rent schedule...</p>}
      {charges.isError && (
        <p role="alert" className="error">
          Could not load the rent schedule: {charges.error.message}
        </p>
      )}
      {charges.data && (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Monthly rent charges and their status</caption>
            <thead>
              <tr>
                <th scope="col">Due date</th>
                <th scope="col">Amount</th>
                <th scope="col">Status</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {charges.data.items.map((c) => (
                <tr key={c.id}>
                  <td>{formatDate(c.due_date)}</td>
                  <td>{money(c.amount)}</td>
                  <td>
                    <span className={`badge status-${c.status}`}>{c.status}</span>
                  </td>
                  <td>
                    {c.status === 'paid' ? (
                      <span className="muted">Paid</span>
                    ) : (
                      <PayButton charge={c} />
                    )}
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
