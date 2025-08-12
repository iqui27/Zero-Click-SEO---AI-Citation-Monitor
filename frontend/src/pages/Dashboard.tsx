import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'

const API = '/api'

type TopDomain = { domain: string; count: number }

type SeriesPoint = { day: string; amr_avg: number; dcr_avg: number; zcrs_avg: number }

export default function Dashboard() {
  const [overview, setOverview] = useState<{ total_runs: number; amr_avg: number; dcr_avg: number; zcrs_avg: number } | null>(null)
  const [series, setSeries] = useState<SeriesPoint[] | null>(null)
  const [topDomains, setTopDomains] = useState<TopDomain[] | null>(null)
  const [perf, setPerf] = useState<Array<{ engine: string; amr_avg: number; dcr_avg: number; zcrs_avg: number }> | null>(null)
  const [costs, setCosts] = useState<{ total_cost_usd: number; total_tokens: number; runs: number; avg_cost_per_run: number; series?: Array<{day: string; engine: string; cost_usd: number; tokens: number}> } | null>(null)

  useEffect(() => {
    axios.get(`${API}/analytics/overview`).then((r) => setOverview(r.data))
    const sp = localStorage.getItem('theme_focus') || localStorage.getItem('subproject_focus')
    if (sp) {
      axios.get(`${API}/analytics/subprojects/${sp}/series`).then(r => setSeries(r.data))
      axios.get(`${API}/analytics/subprojects/${sp}/top-domains`).then(r => setTopDomains(r.data))
      axios.get(`${API}/analytics/performance-by-engine`, { params: { subproject_id: sp } }).then(r => setPerf(r.data))
    } else {
      axios.get(`${API}/runs`).then((r) => {
        const s = (r.data as any[]).map((it) => ({ day: it.started_at || it.id, amr_avg: 0, dcr_avg: 0, zcrs_avg: it.zcrs || 0 }))
        setSeries(s.reverse().slice(-30))
      })
      axios.get(`${API}/analytics/performance-by-engine`).then(r => setPerf(r.data))
    }
    axios.get(`${API}/analytics/costs`).then(r => setCosts(r.data)).catch(()=>{})
  }, [])

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
            <KpiCard title="Tokens (30d)" value={String(costs.total_tokens || 0)} subtitle="Total estimado" barColor="bg-zinc-500" />
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
        <div className="border rounded-md p-2">
          <div className="text-sm opacity-70 px-2 py-1">Evolução Temporal</div>
          {series ? (
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" hide />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="zcrs_avg" name="ZCRS" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="amr_avg" name="AMR" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="dcr_avg" name="DCR" stroke="#22c55e" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <Skeleton className="h-[260px]" />}
        </div>
        <div className="border rounded-md p-2">
          <div className="text-sm opacity-70 px-2 py-1">Top Domínios Citados</div>
          {topDomains ? (
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topDomains} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="domain" width={140} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#111827" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <Skeleton className="h-[260px]" />}
        </div>
      </div>
      <div className="border rounded-md p-2">
        <div className="text-sm opacity-70 px-2 py-1">Desempenho por Engine</div>
        {perf ? (
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={perf}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="engine" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
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
  const [project, setProject] = useState<string>('')
  const [theme, setTheme] = useState<string>('')
  useEffect(() => {
    setProject(localStorage.getItem('project_id') || '')
    setTheme(localStorage.getItem('theme_focus') || localStorage.getItem('subproject_focus') || '')
  }, [])
  if (!project && !theme) return null
  return (
    <div className="text-xs px-2 py-1 border rounded-md flex items-center gap-2">
      {project && <span>Projeto: <span className="font-medium">{project}</span></span>}
      {theme && <span>Tema: <span className="font-medium">{theme}</span></span>}
      <a href="/settings" className="ml-auto underline">alterar</a>
      <button className="underline" onClick={() => { localStorage.removeItem('theme_focus'); localStorage.removeItem('subproject_focus'); window.location.reload() }}>limpar</button>
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
