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
import { BuildingIcon, ClockIcon, WalletIcon, WrenchIcon } from '../icons'

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
      <p className="page-category">Occupancy, rent and maintenance across your properties.</p>

      <section aria-labelledby="kpi-heading">
        <h2 id="kpi-heading">This month ({d.month})</h2>
        <div className="cards">
          <article className="card stat">
            <div className="stat-icon stat-blue">
              <BuildingIcon />
            </div>
            <div>
              <h3>Occupancy</h3>
              <p className="big">{d.occupancy_rate}%</p>
              <p className="muted">
                {d.occupied_units} of {d.total_units} units let
              </p>
            </div>
          </article>
          <article className="card stat">
            <div className="stat-icon stat-green">
              <WalletIcon />
            </div>
            <div>
              <h3>Income collected</h3>
              <p className="big">{money(d.collected_income)}</p>
              <p className="muted">
                of {money(d.expected_income)} expected ({d.collection_rate}%)
              </p>
            </div>
          </article>
          <article className="card stat">
            <div className="stat-icon stat-red">
              <ClockIcon />
            </div>
            <div>
              <h3>Overdue</h3>
              <p className="big">{money(d.overdue_amount)}</p>
              <p className="muted">{d.overdue_charges} unpaid charges past due</p>
            </div>
          </article>
          <article className="card stat">
            <div className="stat-icon stat-orange">
              <WrenchIcon />
            </div>
            <div>
              <h3>Open requests</h3>
              <p className="big">{d.open_requests_total}</p>
              <p className="muted">{breakdown}</p>
            </div>
          </article>
        </div>
      </section>

      <section aria-labelledby="chart-heading" className="card chart" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <h2 id="chart-heading" className="card-title">
            Income in {year}: expected vs collected
          </h2>
        </div>
        {income.isPending && <p role="status">Loading chart...</p>}
        {income.isError && (
          <p role="alert" className="error">
            Could not load the income chart: {income.error.message}
          </p>
        )}
        {income.data && (
          <div
            role="img"
            aria-label={`Bar chart of expected and collected rent for each month of ${year}`}
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ebedf2" vertical={false} />
                <XAxis dataKey="label" />
                <YAxis tickFormatter={(v: number) => moneyWhole(v)} width={80} />
                <Tooltip formatter={(value) => money(Number(value))} />
                <Legend />
                <Bar dataKey="Expected" fill="#fdaf4b" radius={[3, 3, 0, 0]} />
                <Bar dataKey="Collected" fill="#177dff" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </>
  )
}
