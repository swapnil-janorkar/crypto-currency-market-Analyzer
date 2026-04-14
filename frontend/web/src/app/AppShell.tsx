import React from 'react'
import { Outlet } from 'react-router-dom'
import { NavBar } from '../components/NavBar'

export const AppShell: React.FC = () => {
  return (
    <div className="container">
      <NavBar />
      <main className="contentGrid">
        <Outlet />
      </main>
    </div>
  )
}

