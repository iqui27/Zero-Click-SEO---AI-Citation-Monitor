import React, { useEffect, useState } from 'react'
import { formatNumberCompact } from '../lib/utils'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'

import { OverviewAnalytics, SeriesPoint, TopDomain, PerfByEngine, CostsResponse } from '../types/analytics'

const API = '/api'

export default function Dashboard() {
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null)
  const [series, setSeries] = useState<SeriesPoint[] | null>(null)
  const [topDomains, setTopDomains] = useState<TopDomain[] | null>(null)
  const [perf, setPerf] = useState<PerfByEngine[] | null>(null)
  const [costs, setCosts] = useState<CostsResponse | null>(null)

  useEffect(() => {
    axios.get(`${API}/analytics/overview`).then((r) => setOverview(r.data))
    const sp = localStorage.getItem('theme_focus') || localStorage.getItem('subproject_focus')
    if (sp) {
      axios.get(`${API}/analytics/subprojects/${sp}/series`).then(r => setSeries(r.data))
      axios.get(`${API}/analytics/subprojects/${sp}/top-domains`).then(r => setTopDomains(r.data))
      axios.get(`${API}/analytics/performance-by-engine`, { params: { subproject_id: sp } }).then(r => setPerf(r.data))
      axios.get(`${API}/analytics/costs`, { params: { subproject_id: sp } }).then(r => setCosts(r.data)).catch(()=>{})
    } else {
      axios.get(`${API}/runs`).then((r) => {
        const s = (r.data as any[]).map((it) => ({ day: it.started_at || it.id, amr_avg: 0, dcr_avg: 0, zcrs_avg: it.zcrs || 0 }))
        setSeries(s.reverse().slice(-30))
      })
      axios.get(`${API}/analytics/performance-by-engine`).then(r => setPerf(r.data))
      axios.get(`${API}/analytics/costs`).then(r => setCosts(r.data)).catch(()=>{})
    }
  }, [])

  const fmtDate = (s: string) => {
    try {
      const d = new Date(s)
      if (!isNaN(d.getTime())) return d.toLocaleDateString('pt-BR')
      return (s || '').split('T')[0]
    } catch { return (s || '').split('T')[0] }
  }
  const fmtNum = (n: any, decimals = 2) => {
    const v = Number(n)
    if (!isFinite(v)) return n
    return v.toFixed(decimals)
  }

  return (
    <div className="space-y-4">
      <ActiveContextBar />
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <Button variant="secondary" className="ml-auto" onClick={() => window.location.href = '/runs'}>Nova Run</Button>
      </div>
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {overview ? (
          <>
            <KpiCard title="AMR" value={(overview.amr_avg * 100).toFixed(0) + '%'} subtitle="Absolute Mention Rate" barColor="bg-blue-500" />
            <KpiCard title="DCR" value={(overview.dcr_avg * 100).toFixed(0) + '%'} subtitle="Direct Citation Rate" barColor="bg-green-500" />
            <KpiCard title="ZCRS" value={(overview.zcrs_avg || 0).toFixed(0) + '%'} subtitle="Zero‑Click Rate Score" barColor="bg-purple-500" />
          </>
        ) : (
          <>
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </>
        )}
      </div>
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {costs ? (
          <>
            <KpiCard title="Custo (30d)" value={`$${(costs.total_cost_usd || 0).toFixed(4)}`} subtitle="Soma aproximada" barColor="bg-amber-500" />
            <KpiCard title="Tokens (30d)" value={formatNumberCompact(costs.total_tokens || 0)} subtitle="Total estimado" barColor="bg-zinc-500" />
            <KpiCard title="Média por Run" value={`$${(costs.avg_cost_per_run || 0).toFixed(4)}`} subtitle="Ticket médio" barColor="bg-sky-500" />
          </>
        ) : (
          <>
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </>
        )}
      </div>
      <div className="grid gap-3 grid-cols-1 lg:grid-cols-2">
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 p-3 md:p-4">
          <div className="text-sm opacity-70 mb-2">Evolução Temporal</div>
          {series ? (
            <div style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" hide />
                  <YAxis domain={[0, 100]} />
                  <Tooltip formatter={(value) => fmtNum(value)} labelFormatter={(label) => fmtDate(String(label))} />
                  <Legend />
                  <Line type="monotone" dataKey="zcrs_avg" name="ZCRS" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="amr_avg" name="AMR" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="dcr_avg" name="DCR" stroke="#22c55e" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <Skeleton className="h-[260px]" />}
        </div>
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 p-3 md:p-4">
          <div className="text-sm opacity-70 mb-2">Top Domínios Citados</div>
          {topDomains ? (
            <div style={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topDomains} layout="vertical" margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="domain" width={240} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value) => fmtNum(value, 0)} />
                  <Bar dataKey="count" fill="#111827" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <Skeleton className="h-[260px]" />}
        </div>
      </div>
      <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 p-3 md:p-4">
        <div className="text-sm opacity-70 mb-2">Desempenho por Engine</div>
        {perf ? (
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={perf} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="engine" />
                <YAxis domain={[0, 100]} />
                <Tooltip formatter={(value) => fmtNum(value)} />
                <Legend />
                <Bar dataKey="amr_avg" name="AMR" fill="#3b82f6" />
                <Bar dataKey="dcr_avg" name="DCR" fill="#22c55e" />
                <Bar dataKey="zcrs_avg" name="ZCRS" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <Skeleton className="h-[260px]" />}
      </div>
    </div>
  )
}

function ActiveContextBar() {
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([])
  const [projectId, setProjectId] = useState<string>('')
  const [themes, setThemes] = useState<Array<{ id: string; name: string }>>([])
  const [themeId, setThemeId] = useState<string>('')

  useEffect(() => {
    const pid = localStorage.getItem('project_id') || ''
    const sp = localStorage.getItem('theme_focus') || localStorage.getItem('subproject_focus') || ''
    setProjectId(pid)
    setThemeId(sp)
    axios.get('/api/projects').then(r => setProjects(r.data || []))
  }, [])

  useEffect(() => {
    if (!projectId) { setThemes([]); return }
    axios.get(`/api/projects/${projectId}/subprojects`).then(r => setThemes(r.data || []))
  }, [projectId])

  const onChangeProject = (id: string) => {
    setProjectId(id)
    localStorage.setItem('project_id', id)
    setThemeId('')
    localStorage.removeItem('theme_focus')
    localStorage.removeItem('subproject_focus')
    window.location.reload()
  }

  const onChangeTheme = (id: string) => {
    setThemeId(id)
    if (id) {
      localStorage.setItem('theme_focus', id)
      localStorage.setItem('subproject_focus', id)
    } else {
      localStorage.removeItem('theme_focus')
      localStorage.removeItem('subproject_focus')
    }
    window.location.reload()
  }

  const projectName = projects.find(p => p.id === projectId)?.name || projectId
  const themeName = themes.find(t => t.id === themeId)?.name || themeId

  return (
    <div className="text-xs px-2 py-2 border rounded-md flex flex-wrap items-center gap-2 bg-white dark:bg-neutral-900">
      <div className="flex items-center gap-2">
        <span className="opacity-70">Projeto:</span>
        <select
          className="px-2 py-1 rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent"
          value={projectId}
          onChange={(e) => onChangeProject(e.target.value)}
        >
          <option value="">— selecionar —</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>
      <div className="flex items-center gap-2">
        <span className="opacity-70">Tema:</span>
        <select
          className="px-2 py-1 rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent"
          value={themeId}
          onChange={(e) => onChangeTheme(e.target.value)}
          disabled={!projectId}
        >
          <option value="">— todos —</option>
          {themes.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>
      <span className="ml-auto" />
      {projectId && <span className="px-2 py-0.5 rounded border border-neutral-300 dark:border-neutral-700">{projectName}</span>}
      {themeId && <span className="px-2 py-0.5 rounded border border-neutral-300 dark:border-neutral-700">{themeName}</span>}
      <button
        className="underline"
        onClick={() => { localStorage.removeItem('theme_focus'); localStorage.removeItem('subproject_focus'); window.location.reload() }}
      >limpar</button>
    </div>
  )
}

function KpiCard({ title, value, subtitle, barColor }: { title: string; value: string; subtitle: string; barColor: string }) {
  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 space-y-2">
      <div className="text-sm font-semibold">{title}</div>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-xs opacity-70">{subtitle}</div>
      <div className="h-1 w-full rounded-full bg-neutral-200 dark:bg-neutral-800">
        <div className={`h-1 rounded-full ${barColor}`} style={{ width: value }} />
      </div>
    </div>
  )
}
