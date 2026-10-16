import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api'
import { money, moneyWhole } from '../format'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export default function LandlordDashboard() {
  const year = new Date().getFullYear()
  const summary = useQuery({ queryKey: ['dashboard', 'summary'], queryFn: () => api.dashboard() })
  const income = useQuery({
    queryKey: ['dashboard', 'income', year],
    queryFn: () => api.income(year),
  })

  if (summary.isPending) return <p role="status">Loading dashboard...</p>
  if (summary.isError) {
    return (
      <p role="alert" className="error">
        Could not load the dashboard: {summary.error.message}
      </p>
    )
  }

  const d = summary.data
  const chartData =
    income.data?.months.map((m, i) => ({
      label: MONTHS[i],
      Expected: Number(m.expected),
      Collected: Number(m.collected),
    })) ?? []
  const breakdown = Object.entries(d.open_requests)
    .map(([status, n]) => `${n} ${status.replace('_', ' ')}`)
    .join(', ')

  return (
    <>
      <h1>Dashboard</h1>

      <section aria-labelledby="kpi-heading">
        <h2 id="kpi-heading">This month ({d.month})</h2>
        <div className="cards">
          <article className="card">
            <h3>Occupancy</h3>
            <p className="big">{d.occupancy_rate}%</p>
            <p className="muted">
              {d.occupied_units} of {d.total_units} units let
            </p>
          </article>
          <article className="card">
            <h3>Income collected</h3>
            <p className="big">{money(d.collected_income)}</p>
            <p className="muted">
              of {money(d.expected_income)} expected ({d.collection_rate}%)
            </p>
          </article>
          <article className="card">
            <h3>Overdue</h3>
            <p className="big">{money(d.overdue_amount)}</p>
            <p className="muted">{d.overdue_charges} unpaid charges past due</p>
          </article>
          <article className="card">
            <h3>Open requests</h3>
            <p className="big">{d.open_requests_total}</p>
            <p className="muted">{breakdown}</p>
          </article>
        </div>
      </section>

      <section aria-labelledby="chart-heading">
        <h2 id="chart-heading">Income in {year}: expected vs collected</h2>
        {income.isPending && <p role="status">Loading chart...</p>}
        {income.isError && (
          <p role="alert" className="error">
            Could not load the income chart: {income.error.message}
          </p>
        )}
        {income.data && (
          <div
            className="card chart"
            role="img"
            aria-label={`Bar chart of expected and collected rent for each month of ${year}`}
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis tickFormatter={(v: number) => moneyWhole(v)} width={80} />
                <Tooltip formatter={(value) => money(Number(value))} />
                <Legend />
                <Bar dataKey="Expected" fill="#94a3b8" />
                <Bar dataKey="Collected" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </>
  )
}
