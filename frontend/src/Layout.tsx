import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from './auth-context'
import { BuildingIcon, HomeIcon, MenuIcon, ShieldIcon, WalletIcon, WrenchIcon } from './icons'
import type { Role } from './types'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  end?: boolean
}

const NAV: Record<Role, NavItem[]> = {
  landlord: [
    { to: '/landlord', label: 'Dashboard', icon: <HomeIcon />, end: true },
    { to: '/landlord/properties', label: 'Properties', icon: <BuildingIcon /> },
    { to: '/landlord/maintenance', label: 'Maintenance', icon: <WrenchIcon /> },
  ],
  tenant: [
    { to: '/tenant', label: 'Rent', icon: <WalletIcon />, end: true },
    { to: '/tenant/maintenance', label: 'Maintenance', icon: <WrenchIcon /> },
  ],
  admin: [{ to: '/admin', label: 'Audit log', icon: <ShieldIcon /> }],
}

export default function Layout() {
  const { user, logout } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  function onLogout() {
    logout()
    queryClient.clear()
    navigate('/login', { replace: true })
  }

  const items = user ? NAV[user.role] : []
  const initials = user
    ? user.full_name
        .split(' ')
        .filter(Boolean)
        .map((part) => part[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : ''

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="app">
        <aside id="sidebar" className={`sidebar${open ? ' open' : ''}`}>
          <div className="sidebar-logo">
            <Link to="/" className="brand" onClick={() => setOpen(false)}>
              My Properties 4U
            </Link>
          </div>
          <nav className="sidebar-nav" aria-label="Main">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setOpen(false)}>
                {item.icon}
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </aside>
        {open && <div className="scrim" onClick={() => setOpen(false)} aria-hidden="true" />}

        <div className="main-panel">
          <header className="topbar">
            <button
              type="button"
              className="menu-toggle"
              aria-label="Open menu"
              aria-expanded={open}
              aria-controls="sidebar"
              onClick={() => setOpen((o) => !o)}
            >
              <MenuIcon />
            </button>
            {user && (
              <div className="user-box">
                <span className="avatar" aria-hidden="true">
                  {initials}
                </span>
                <span className="user-name">
                  <span className="muted">Hi,</span> <strong>{user.full_name}</strong>{' '}
                  <span className="badge badge-role">{user.role}</span>
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
        </div>
      </div>
    </>
  )
}
