import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from './auth-context'

export default function Layout() {
  const { user, logout } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  function onLogout() {
    logout()
    queryClient.clear()
    navigate('/login', { replace: true })
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="app-header">
        <Link to="/" className="brand">
          My Properties 4U
        </Link>
        {user?.role === 'tenant' && (
          <nav className="main-nav" aria-label="Main">
            <NavLink to="/tenant" end>
              Rent
            </NavLink>
            <NavLink to="/tenant/maintenance">Maintenance</NavLink>
          </nav>
        )}
        {user?.role === 'landlord' && (
          <nav className="main-nav" aria-label="Main">
            <NavLink to="/landlord" end>
              Dashboard
            </NavLink>
            <NavLink to="/landlord/maintenance">Maintenance</NavLink>
          </nav>
        )}
        {user && (
          <div className="user-box">
            <span>
              {user.full_name} <span className="badge">{user.role}</span>
            </span>
            <button type="button" className="btn btn-secondary" onClick={onLogout}>
              Log out
            </button>
          </div>
        )}
      </header>
      <main id="main" className="container">
        <Outlet />
      </main>
    </>
  )
}
