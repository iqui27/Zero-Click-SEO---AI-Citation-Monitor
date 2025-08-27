import React, { useEffect, useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Link, Outlet, Navigate, useNavigate } from 'react-router-dom'
import Runs from './pages/Runs'
import RunDetail from './pages/RunDetail'
import TemplatesPage from './pages/Templates'
import ProjectsPage from './pages/Projects'
import SubprojectsPage from './pages/Subprojects'
import SubprojectDetail from './pages/SubprojectDetail'
import WorkspacePage from './pages/Workspace'
import SettingsPage from './pages/Settings'
import './index.css'
import { Button } from './components/ui/button'

function LiveBadge() {
  const [mode, setMode] = useState<string>('')
  useEffect(() => {
    const read = () => setMode(localStorage.getItem('live_mode') || '')
    read()
    const onStorage = (e: StorageEvent) => { if (e.key === 'live_mode') read() }
    window.addEventListener('storage', onStorage)
    const h = setInterval(read, 1000)
    return () => { window.removeEventListener('storage', onStorage); clearInterval(h) }
  }, [])
  if (!mode) return null
  const m = mode.toLowerCase()
  const isSSE = m.includes('sse') || m === 'sse'
  const isPolling = m.includes('polling')
  const label = isSSE ? 'Conectado (SSE)' : isPolling ? 'Conectado (Polling)' : mode
  const dotCls = isSSE ? 'bg-green-500' : isPolling ? 'bg-amber-500' : 'bg-neutral-400'
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-1 border rounded-md">
      <span className={`h-1.5 w-1.5 rounded-full ${dotCls} animate-pulse`} />
      {label}
    </span>
  )
}

function Layout() {
  const [dark, setDark] = useState<boolean>(() => (localStorage.getItem('theme') || 'light') === 'dark')
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const searchRef = useRef<HTMLInputElement | null>(null)
  const [chord, setChord] = useState<string | null>(null)
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const isTyping = !!target && (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        (target as HTMLElement).isContentEditable
      )
      if (!isTyping && e.key === '/') {
        e.preventDefault()
        searchRef.current?.focus()
        return
      }
      if (!isTyping && e.key === 'r') {
        e.preventDefault()
        navigate('/runs?new=1')
        return
      }
      if (!isTyping && e.key.toLowerCase() === 'g') {
        setChord('g')
        setTimeout(() => setChord(null), 600)
        return
      }
      if (chord === 'g' && e.key.toLowerCase() === 'd') {
        e.preventDefault()
        setChord(null)
        navigate('/')
        return
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [navigate, chord])
  return (
    <div className="min-h-screen grid grid-rows-[auto_1fr]">
      <nav className="flex items-center gap-4 px-3 sm:px-4 md:px-6 py-3 border-b border-neutral-200 dark:border-neutral-800">
        <Link to="/" className="flex items-center text-neutral-900 dark:text-neutral-100" aria-label="Home">
          <svg
            viewBox="0 0 640 160"
            xmlns="http://www.w3.org/2000/svg"
            role="img"
            aria-label="GEO – AI Citation Monitor & Zero-Click SEO"
            className="h-12 sm:h-14 w-auto"
          >
            <g transform="translate(20,20)" fill="none" stroke="currentColor" strokeWidth={6} strokeLinecap="round" strokeLinejoin="round">
              <defs>
                <mask id="cut-bolt" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
                  <rect x="0" y="0" width="120" height="120" fill="white" />
                  <path d="M66 16 40 74h24l-10 44 38-70H68z" fill="black" stroke="black" strokeWidth={10} />
                </mask>
              </defs>

              <circle cx="60" cy="60" r="54" />
              <path d="M16 72c16-14 32-14 48 0s32 14 48 0" mask="url(#cut-bolt)" />
              <path d="M66 16 40 74h24l-10 44 38-70H68z" fill="currentColor" stroke="none" />
            </g>

            <g transform="translate(160,52)" fill="currentColor">
              <text
                x="0"
                y="40"
                fontFamily="Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif"
                fontSize={56}
                fontWeight={800}
                letterSpacing={0.2}
              >
                GEO
              </text>
              <text
                x="4"
                y="80"
                fontFamily="Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif"
                fontSize={22}
                fontWeight={500}
                opacity={0.6}
              >
                AI Citation Monitor &amp; Zero-Click SEO
              </text>
            </g>
          </svg>
        </Link>
        <Link to="/runs" className="text-sm opacity-80 hover:opacity-100">Runs</Link>
        <Link to="/workspace" className="text-sm opacity-80 hover:opacity-100">Projetos & Temas</Link>
        <Link to="/prompts" className="text-sm opacity-80 hover:opacity-100">Prompts</Link>
        <Link to="/settings" className="text-sm opacity-80 hover:opacity-100">⚙️ Settings</Link>
        <div className="ml-auto flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-2">
            <input
              ref={searchRef}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/runs?q=${encodeURIComponent(search)}`) }}
              placeholder="Buscar (/)"
              aria-label="Buscar"
              className="text-sm px-3 py-1.5 border rounded-md bg-transparent border-neutral-300 dark:border-neutral-700"
            />
            <Button variant="secondary" size="sm" onClick={() => navigate(`/runs?q=${encodeURIComponent(search)}`)}>Buscar</Button>
          </div>
          <Button size="sm" onClick={() => navigate('/runs?new=1')}>Nova Run</Button>
          <LiveBadge />
          <button onClick={() => setDark((v) => !v)} className="text-sm px-3 py-1 border rounded-md border-neutral-300 dark:border-neutral-700">
            {dark ? 'Light' : 'Dark'}
          </button>
        </div>
      </nav>
      <main className="py-4">
        <div className="space-y-4 px-3 sm:px-4 md:px-6 max-w-[1200px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function RootRedirect() {
  return <Navigate to="/runs" replace />
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <RootRedirect /> },
      { path: 'runs', element: <Runs /> },
      { path: 'runs/:id', element: <RunDetail /> },
      { path: 'workspace', element: <WorkspacePage /> },
      { path: 'projects', element: <ProjectsPage /> },
      { path: 'subprojects', element: <SubprojectsPage /> },
      { path: 'subprojects/:id', element: <SubprojectDetail /> },
      { path: 'prompts', element: <TemplatesPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
