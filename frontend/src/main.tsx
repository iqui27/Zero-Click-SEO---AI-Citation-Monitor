import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Link, Outlet, useLocation, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Runs from './pages/Runs'
import RunDetail from './pages/RunDetail'
import TemplatesPage from './pages/Templates'
import SubprojectsPage from './pages/Subprojects'
import SubprojectDetail from './pages/SubprojectDetail'
import MonitorsPage from './pages/Monitors'
import SettingsPage from './pages/Settings'
import ProjectsPage from './pages/Projects'
import SetupWizard from './pages/SetupWizard'
import InsightsPage from './pages/Insights'
import axios from 'axios'
import './index.css'

function LiveBadge() {
  const [mode, setMode] = useState<string>('')
  useEffect(() => {
    const h = setInterval(() => {
      setMode(localStorage.getItem('live_mode') || '')
    }, 1000)
    return () => clearInterval(h)
  }, [])
  if (!mode) return null
  return <span className="text-xs px-2 py-1 border rounded-md">{mode}</span>
}

function Layout() {
  const [dark, setDark] = useState(true)
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])
  return (
    <div className="min-h-screen grid grid-rows-[auto_1fr]">
      <nav className="flex items-center gap-4 px-4 py-3 border-b border-neutral-200 dark:border-neutral-800">
        <Link to="/" className="font-bold">Zero‑Click Monitor</Link>
        <Link to="/projects" className="text-sm opacity-80 hover:opacity-100">Projetos</Link>
        <Link to="/subprojects" className="text-sm opacity-80 hover:opacity-100">Subprojetos</Link>
        <Link to="/templates" className="text-sm opacity-80 hover:opacity-100">Templates</Link>
        <Link to="/runs" className="text-sm opacity-80 hover:opacity-100">Runs</Link>
        <Link to="/insights" className="text-sm opacity-80 hover:opacity-100">Insights</Link>
        <Link to="/settings" className="text-sm opacity-80 hover:opacity-100">Settings</Link>
        <div className="ml-auto flex items-center gap-2">
          <LiveBadge />
          <button onClick={() => setDark((v) => !v)} className="text-sm px-3 py-1 border rounded-md border-neutral-300 dark:border-neutral-700">
            {dark ? 'Light' : 'Dark'}
          </button>
        </div>
      </nav>
      <main className="p-4">
        <Outlet />
      </main>
    </div>
  )
}

function RootRedirect() {
  const [ready, setReady] = useState(false)
  const [needsSetup, setNeedsSetup] = useState(false)
  useEffect(() => {
    axios.get('/api/setup/status').then(r => {
      const sandbox = r.data?.sandbox
      const hasProject = !!localStorage.getItem('project_id')
      setNeedsSetup(!hasProject)
    }).finally(() => setReady(true))
  }, [])
  if (!ready) return null
  if (needsSetup) return <Navigate to="/setup" replace />
  return <Dashboard />
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <RootRedirect /> },
      { path: 'setup', element: <SetupWizard /> },
      { path: 'projects', element: <ProjectsPage /> },
      { path: 'runs', element: <Runs /> },
      { path: 'runs/:id', element: <RunDetail /> },
      { path: 'templates', element: <TemplatesPage /> },
      { path: 'subprojects', element: <SubprojectsPage /> },
      { path: 'subprojects/:id', element: <SubprojectDetail /> },
      { path: 'monitors', element: <MonitorsPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'insights', element: <InsightsPage /> },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
