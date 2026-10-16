import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth-context'

const DEMOS = [
  { label: 'Landlord', email: 'landlord1@example.com' },
  { label: 'Tenant', email: 'tenant1@example.com' },
  { label: 'Admin', email: 'admin@example.com' },
]
const DEMO_PASSWORD = 'Demo1234!'

export default function Login() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <form onSubmit={onSubmit} className="card login-card">
        <h1>My Properties 4U</h1>
        <p className="muted">Sign in to manage properties, rent and maintenance.</p>

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}

        <button type="submit" className="btn" disabled={submitting}>
          {submitting ? 'Signing in...' : 'Sign in'}
        </button>

        <div className="demo">
          <p className="muted">Demo accounts (simulated data, no real money):</p>
          <div className="demo-buttons">
            {DEMOS.map((d) => (
              <button
                key={d.email}
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setEmail(d.email)
                  setPassword(DEMO_PASSWORD)
                }}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>
      </form>
    </main>
  )
}
