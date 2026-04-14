import React from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../app/Theme'

export const NavBar: React.FC = () => {
  const { username, logout } = useAuth()
  const { theme, toggle } = useTheme()

  return (
    <header className="masthead">
      <div className="mastheadTop">
        <div className="brand">
          <div className="brandTitle">CryptoSight</div>
          <div className="brandTag">MarketEdition</div>
        </div>
        <nav className="nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `navLink ${isActive ? 'navLinkActive' : ''}`}
          >
            Overview
          </NavLink>
          <NavLink
            to="/coin"
            className={({ isActive }) => `navLink ${isActive ? 'navLinkActive' : ''}`}
          >
            CoinDesk
          </NavLink>
          <NavLink
            to="/pulse"
            className={({ isActive }) => `navLink ${isActive ? 'navLinkActive' : ''}`}
          >
            MarketPulse
          </NavLink>
          <button className="navBtn" type="button" onClick={toggle}>
            Theme: {theme}
          </button>
          <span className="pill">Signed in: {username ?? '—'}</span>
          <button className="navBtn" type="button" onClick={logout}>
            Logout
          </button>
        </nav>
      </div>
    </header>
  )
}

