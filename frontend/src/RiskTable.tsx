import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import { formatDate, money } from './format'

export default function RiskTable() {
  const risk = useQuery({ queryKey: ['risk'], queryFn: () => api.risk() })

  return (
    <section aria-labelledby="risk-heading" className="card" style={{ marginTop: '1.5rem' }}>
      <div className="card-header">
        <h2 id="risk-heading" className="card-title">
          Upcoming rent: late-payment risk
        </h2>
      </div>
      {risk.isPending && <p role="status">Loading risk scores...</p>}
      {risk.isError && (
        <p role="alert" className="error">
          Could not load risk scores: {risk.error.message}
        </p>
      )}
      {risk.data && (
        <>
          <p className="muted">{risk.data.note}</p>
          {risk.data.items.length === 0 && <p className="muted">No upcoming charges.</p>}
          {risk.data.items.length > 0 && (
            <div className="table-wrap">
              <table>
                <caption className="sr-only">
                  Upcoming rent charges with an estimated chance of late payment
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Due</th>
                    <th scope="col">Property</th>
                    <th scope="col">Tenant</th>
                    <th scope="col">Amount</th>
                    <th scope="col">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {risk.data.items.map((r) => (
                    <tr key={r.charge_id}>
                      <td>{formatDate(r.due_date)}</td>
                      <td>
                        {r.property_name}, {r.unit_number}
                      </td>
                      <td>{r.tenant_email}</td>
                      <td>{money(r.amount)}</td>
                      <td>
                        <span className={`badge risk-${r.band}`}>
                          {r.probability === null
                            ? 'Not enough history'
                            : `${r.band} (${Math.round(r.probability * 100)}%)`}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}
