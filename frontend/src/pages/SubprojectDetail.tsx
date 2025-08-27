import React, { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'
import { Button } from '../components/ui/button'
import { formatNumberCompact } from '../lib/utils'
import KpiExplainer from '../components/KpiExplainer'
import { Toaster, toast } from 'sonner'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Download, BarChart2, Target, Table as TableIcon } from 'lucide-react'
import {
  OverviewAnalytics,
  SeriesPoint,
  TopDomain,
  RunItem,
  PerfByEngine,
  RunsBySubprojectGroup,
} from '../types/analytics'

const API = '/api'

export default function SubprojectDetail() {
  const { id } = useParams()
  const [ov, setOv] = useState<OverviewAnalytics | null>(null)
  const [series, setSeries] = useState<SeriesPoint[]>([])
  const [tops, setTops] = useState<TopDomain[]>([])
  const [runs, setRuns] = useState<RunItem[]>([])
  const [perf, setPerf] = useState<PerfByEngine[]>([])
  const [projectName, setProjectName] = useState<string>('')
  const [projectId, setProjectId] = useState<string>('')
  const [projectDomains, setProjectDomains] = useState<{ id: string; domain: string; is_primary: boolean }[]>([])
  const [subprojectName, setSubprojectName] = useState<string>('')
  const [tab, setTab] = useState<'overview'|'runs'|'compare'|'insights'>('overview')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [engineFilter, setEngineFilter] = useState<string>('')
  const [q, setQ] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [showFilters, setShowFilters] = useState<boolean>(false)
  const [page, setPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(25)
  const [orderBy, setOrderBy] = useState<string>('started_at')
  const [orderDir, setOrderDir] = useState<'asc'|'desc'>('desc')
  // comparison state
  const [groups, setGroups] = useState<RunsBySubprojectGroup[]>([])
  const [limitPerGroup, setLimitPerGroup] = useState<number>(5)
  const [loadingCompare, setLoadingCompare] = useState<boolean>(false)

  useEffect(() => {
    if (!id) return
    axios.get(`${API}/analytics/subprojects/${id}/overview`).then(r => setOv(r.data))
    axios.get(`${API}/analytics/subprojects/${id}/series`).then(r => setSeries(r.data))
    axios.get(`${API}/analytics/subprojects/${id}/top-domains`).then(r => setTops(r.data))
    axios.get(`${API}/analytics/performance-by-engine`, { params: { subproject_id: id } }).then(r => setPerf(r.data))
    axios
      .get(`${API}/runs`, {
        params: { subproject_id: id, page_size: 50, order_by: 'started_at', order_dir: 'desc' },
      })
      .then(r => {
        setRuns(r.data)
        if (!subprojectName && r.data?.[0]?.subproject_name) setSubprojectName(r.data[0].subproject_name)
      })
    // Resolver nomes de projeto/subprojeto
    const resolveNames = async () => {
      try {
        const pr = await axios.get(`${API}/projects`)
        const projects: { id: string; name: string }[] = pr.data || []
        for (const p of projects) {
          const sp = await axios.get(`${API}/projects/${p.id}/subprojects`)
          const list: { id: string; name: string }[] = sp.data || []
          const found = list.find(s => s.id === id)
          if (found) {
            setProjectName(p.name)
            setProjectId(p.id)
            if (!subprojectName) setSubprojectName(found.name)
            try {
              const dom = await axios.get(`${API}/projects/${p.id}/domains`).then(r => r.data)
              setProjectDomains(dom.map((d: any) => ({ id: d.id, domain: d.domain, is_primary: !!d.is_primary })))
            } catch {}
            break
          }
        }
      } catch {}
    }
    resolveNames()
  }, [id])

  // Fetch grouped data when entering compare tab
  useEffect(() => {
    const fetchGrouped = async () => {
      if (!id || tab !== 'compare') return
      setLoadingCompare(true)
      try {
        const r = await axios.get(`${API}/runs/grouped`, { params: { subproject_id: id, limit_per_group: limitPerGroup } })
        setGroups(r.data || [])
      } catch (e: any) {
        console.error(e)
        toast.error('Falha ao carregar grupos para comparação')
      }
      finally { setLoadingCompare(false) }
    }
    fetchGrouped()
  }, [id, tab, limitPerGroup])

  const refreshCompare = async () => {
    if (!id) return
    setLoadingCompare(true)
    try {
      const r = await axios.get(`${API}/runs/grouped`, { params: { subproject_id: id, limit_per_group: limitPerGroup } })
      setGroups(r.data || [])
    } catch (e: any) {
      console.error(e)
      toast.error('Falha ao atualizar comparação')
    } finally {
      setLoadingCompare(false)
    }
  }

  // agregados simples sobre a amostra de runs carregadas
  const sampleCost = runs.reduce((acc, r) => acc + (r.cost_usd || 0), 0)
  const sampleTokens = runs.reduce((acc, r) => acc + (r.tokens_total || 0), 0)
  const maxTop = useMemo(() => Math.max(1, ...tops.map(t => t.count || 0)), [tops])
  const engines = useMemo(() => Array.from(new Set(runs.map(r => r.engine))).filter(Boolean), [runs])
  const filteredRuns = useMemo(() => {
    const inRange = (ts?: string) => {
      if (!ts) return true
      if (!dateFrom && !dateTo) return true
      try {
        const d = new Date(ts)
        const dOnly = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
        const from = dateFrom ? new Date(`${dateFrom}T00:00:00Z`) : null
        const to = dateTo ? new Date(`${dateTo}T23:59:59Z`) : null
        if (from && dOnly < from) return false
        if (to && dOnly > to) return false
        return true
      } catch { return true }
    }
    return runs.filter(r => (
      (!statusFilter || r.status === statusFilter) &&
      (!engineFilter || r.engine === engineFilter) &&
      (!q || r.id.includes(q)) &&
      inRange(r.started_at)
    ))
  }, [runs, statusFilter, engineFilter, q, dateFrom, dateTo])
  const sortedRuns = useMemo(() => {
    const list = [...filteredRuns]
    const dir = orderDir === 'asc' ? 1 : -1
    list.sort((a, b) => {
      const key = orderBy
      const va: any = (a as any)[key]
      const vb: any = (b as any)[key]
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * dir
      const sa = String(va)
      const sb = String(vb)
      return sa.localeCompare(sb) * dir
    })
    return list
  }, [filteredRuns, orderBy, orderDir])
  const totalPages = Math.max(1, Math.ceil(sortedRuns.length / pageSize))
  const pageRuns = useMemo(() => {
    const p = Math.max(1, Math.min(page, totalPages))
    const start = (p - 1) * pageSize
    return sortedRuns.slice(start, start + pageSize)
  }, [sortedRuns, page, pageSize, totalPages])
  const countsByStatus = useMemo(() => {
    const map: Record<string, number> = {}
    for (const r of runs) map[r.status] = (map[r.status] || 0) + 1
    return map
  }, [runs])

  const refreshRuns = async () => {
    if (!id) return
    const r = await axios.get(`${API}/runs`, { params: { subproject_id: id, page_size: 50, order_by: 'started_at', order_dir: 'desc' } })
    setRuns(r.data)
  }

  const setQuickRange = (range: 'today' | 7 | 30 | 'all') => {
    if (range === 'all') { setDateFrom(''); setDateTo(''); return }
    const now = new Date()
    const end = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()))
    const start = new Date(end)
    if (range !== 'today') start.setUTCDate(start.getUTCDate() - (range as number))
    const fmt = (d: Date) => `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`
    setDateFrom(fmt(start))
    setDateTo(fmt(end))
  }

  const fmt = (ts?: string) => {
    if (!ts) return '-'
    try { return new Date(ts).toLocaleString() } catch { return ts }
  }

  return (
    <div className="space-y-5 md:space-y-6">
      {/* Cabeçalho e ações */}
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">{subprojectName || `Tema ${id}`}</h1>
        {projectName && (
          <span className="text-xs px-2 py-1 rounded-full border border-neutral-300 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300">Projeto: {projectName}</span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <a href={`${API}/analytics/subprojects/${id}/export.csv`}><Download className="h-4 w-4 mr-1" /> Exportar CSV</a>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href="/runs"><TableIcon className="h-4 w-4 mr-1" /> Ver runs</a>
          </Button>
          <Button size="sm" onClick={() => { localStorage.setItem('theme_focus', id || ''); localStorage.setItem('subproject_focus', id || ''); toast.success('Foco do tema definido no dashboard'); }}>
            <Target className="h-4 w-4 mr-1" /> Focar no dashboard
          </Button>
        </div>
      </div>

      {/* Domínios do projeto */}
      {!!projectDomains.length && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs opacity-70 mr-1">Domínios do projeto:</span>
          {projectDomains.map(d => (
            <span key={d.id} className={`text-xs px-2 py-0.5 rounded-full border ${d.is_primary ? 'border-blue-300 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300' : 'border-neutral-300 dark:border-neutral-700'}`}>
              {d.domain}{d.is_primary ? ' (primário)' : ''}
            </span>
          ))}
        </div>
      )}

      

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        <Card title="Total Runs" value={ov?.total_runs ?? 0} />
        <Card title="AMR médio" value={(ov?.amr_avg ?? 0).toFixed(2)} />
        <Card title="DCR médio" value={(ov?.dcr_avg ?? 0).toFixed(2)} />
        <Card title="ZCRS médio" value={(ov?.zcrs_avg ?? 0).toFixed(1)} />
        <Card title="Custo (amostra)" value={`$${sampleCost.toFixed(4)}`} />
        <Card title="Tokens (amostra)" value={formatNumberCompact(sampleTokens)} />
      </div>

      <KpiExplainer />

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-neutral-200 dark:border-neutral-800">
        <button onClick={() => setTab('overview')} className={`px-3 py-1.5 text-sm ${tab==='overview' ? 'border-b-2 border-neutral-900 dark:border-neutral-100 font-medium' : 'opacity-70 hover:opacity-100'}`}>
          <BarChart2 className="inline-block h-4 w-4 mr-1" /> Visão geral
        </button>
        <button onClick={() => setTab('runs')} className={`px-3 py-1.5 text-sm ${tab==='runs' ? 'border-b-2 border-neutral-900 dark:border-neutral-100 font-medium' : 'opacity-70 hover:opacity-100'}`}>
          <TableIcon className="inline-block h-4 w-4 mr-1" /> Runs
        </button>
        <button onClick={() => setTab('compare')} className={`px-3 py-1.5 text-sm ${tab==='compare' ? 'border-b-2 border-neutral-900 dark:border-neutral-100 font-medium' : 'opacity-70 hover:opacity-100'}`}>
          <TableIcon className="inline-block h-4 w-4 mr-1" /> Comparar
        </button>
        <button onClick={() => setTab('insights')} className={`px-3 py-1.5 text-sm ${tab==='insights' ? 'border-b-2 border-neutral-900 dark:border-neutral-100 font-medium' : 'opacity-70 hover:opacity-100'}`}>
          Insights
        </button>
      </div>

      {tab === 'overview' && (
        <>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="col-span-2 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 p-3 md:p-4">
          <div className="text-sm opacity-70 mb-2">ZCRS médio por dia</div>
          <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" hide />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Line type="monotone" dataKey="zcrs_avg" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 p-3 md:p-4">
          <div className="text-sm opacity-70 mb-2">Domínios mais citados</div>
              <div className="grid gap-2 text-sm">
                {tops.map((t, i) => (
                  <div key={i} className="grid gap-1">
                    <div className="flex items-center justify-between">
                      <span className="truncate">{t.domain}</span>
                      <span className="opacity-70">{t.count}</span>
                    </div>
                <div className="h-2 bg-neutral-200 dark:bg-neutral-800 rounded">
                  <div className="h-2 bg-neutral-900 dark:bg-neutral-100 rounded" style={{ width: `${Math.min(100, Math.round((t.count / maxTop) * 100))}%` }} />
                    </div>
                  </div>
                ))}
                {!tops.length && <div className="text-sm opacity-70">Sem dados.</div>}
              </div>
            </div>
          </div>

      {!!perf.length && (
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 p-3 md:p-4">
          <div className="text-sm opacity-70 mb-2">Performance por Engine</div>
          <div style={{ height: 300 }}>
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
            </div>
          )}
        </>
      )}

      {!!perf.length && (
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 p-3 md:p-4">
          <div className="text-sm opacity-70 mb-2">Performance por Engine</div>
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-neutral-500">
                  <th className="text-left px-2 py-1">Engine</th>
                  <th className="text-right px-2 py-1">Runs</th>
                  <th className="text-right px-2 py-1">AMR</th>
                  <th className="text-right px-2 py-1">DCR</th>
                  <th className="text-right px-2 py-1">ZCRS</th>
                </tr>
              </thead>
              <tbody>
                {perf.map((p, i) => (
                  <tr key={i} className="border-t border-neutral-200 dark:border-neutral-800">
                    <td className="px-2 py-1">{p.engine}</td>
                    <td className="px-2 py-1 text-right">{p.runs}</td>
                    <td className="px-2 py-1 text-right">{p.amr_avg.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right">{p.dcr_avg.toFixed(2)}</td>
                    <td className="px-2 py-1 text-right">{p.zcrs_avg.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'runs' && (
        <div className="border rounded-md shadow-sm bg-white dark:bg-neutral-900">
          {/* Barra de contexto */}
          <div className="px-2 pt-2">
            <div className="text-xs px-2 py-1 border rounded-md flex flex-wrap items-center gap-2">
              {projectName && <span>Projeto: <span className="font-medium">{projectName}</span></span>}
              {subprojectName && <span>Tema: <span className="font-medium">{subprojectName}</span></span>}
              <button
                className="ml-auto underline"
                onClick={() => { localStorage.removeItem('theme_focus'); localStorage.removeItem('subproject_focus'); }}
              >limpar</button>
            </div>
          </div>

          <div className="p-2 flex flex-wrap items-center gap-2">
            <div className="text-sm opacity-70">Últimas runs do tema</div>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              {/* Presets de período */}
              <Button variant="outline" size="sm" onClick={() => setQuickRange('today')}>Hoje</Button>
              <Button variant="outline" size="sm" onClick={() => setQuickRange(7)}>7d</Button>
              <Button variant="outline" size="sm" onClick={() => setQuickRange(30)}>30d</Button>
              <Button variant="outline" size="sm" onClick={() => setQuickRange('all')}>Tudo</Button>
              <div className="hidden sm:flex items-center gap-2 text-xs opacity-80">
                <span>ok</span><span className="px-1.5 border rounded">{countsByStatus['completed'] || 0}</span>
                <span>fail</span><span className="px-1.5 border rounded">{countsByStatus['failed'] || 0}</span>
                <span>run</span><span className="px-1.5 border rounded">{countsByStatus['running'] || 0}</span>
              </div>
              <Button variant="outline" size="sm" onClick={() => setShowFilters(v=>!v)}>{showFilters ? 'Ocultar filtros' : 'Filtros'}</Button>
              <Button variant="secondary" size="sm" onClick={refreshRuns}>Atualizar</Button>
            </div>
          </div>
          {showFilters && (
            <div className="p-3 border-t grid gap-3 sm:grid-cols-6">
              <Select value={engineFilter} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setEngineFilter(e.target.value)} className="sm:col-span-2">
                <option value="">Todas as engines</option>
                {engines.map(en => (<option key={en} value={en}>{en}</option>))}
              </Select>
              <Select value={statusFilter} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStatusFilter(e.target.value)} className="sm:col-span-2">
                <option value="">Todos os status</option>
                {['queued','running','completed','failed'].map(s => (<option key={s} value={s}>{s}</option>))}
              </Select>
              <div className="sm:col-span-2 flex items-center gap-2">
                <Input type="date" value={dateFrom} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDateFrom(e.target.value)} />
                <Input type="date" value={dateTo} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDateTo(e.target.value)} />
              </div>
              <Input placeholder="Buscar por ID" value={q} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQ(e.target.value)} className="sm:col-span-3" />
              <div className="sm:col-span-3" />
            </div>
          )}
          {/* Ordenação e paginação */}
          <div className="p-3 border-t flex flex-wrap items-center gap-3 text-sm">
            <span className="opacity-70">Ordenar por</span>
            <Select value={orderBy} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setOrderBy(e.target.value); setPage(1) }}>
              <option value="started_at">Início</option>
              <option value="finished_at">Fim</option>
              <option value="zcrs">ZCRS</option>
              <option value="cost_usd">Custo</option>
              <option value="tokens_total">Tokens</option>
              <option value="status">Status</option>
              <option value="engine">Engine</option>
            </Select>
            <Select value={orderDir} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setOrderDir(e.target.value as any); setPage(1) }}>
              <option value="desc">Desc</option>
              <option value="asc">Asc</option>
            </Select>
            <div className="ml-auto flex items-center gap-3">
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>Anterior</Button>
              <span className="px-2">{page}/{totalPages}</span>
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>Próxima</Button>
              <span className="opacity-70 ml-2">Itens por página</span>
              <Select value={String(pageSize)} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setPageSize(parseInt(e.target.value)); setPage(1) }}>
                {[10,25,50,100].map(n => <option key={n} value={n}>{n}</option>)}
              </Select>
              {/* Ver run no Runs */}
              <Button
                asChild
                className="bg-neutral-900 hover:bg-neutral-800 text-white px-4"
              >
                <a
                  href={`/runs?${new URLSearchParams({
                    ...(id ? { subproject_id: id } : {}),
                    ...(engineFilter ? { engine: engineFilter } : {}),
                    ...(statusFilter ? { status: statusFilter } : {}),
                    ...(q ? { q } : {}),
                  }).toString()}`}
                >Ver run</a>
              </Button>
            </div>
          </div>
          <div className="overflow-auto rounded-b-md">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-neutral-50 dark:bg-neutral-900 z-10">
                <tr className="text-neutral-500 text-xs">
                  <th className="text-left px-2 py-1">ID</th>
                  <th className="text-left px-2 py-1">Engine</th>
                  <th className="text-left px-2 py-1">Status</th>
                  <th className="text-left px-2 py-1">Início</th>
                  <th className="text-left px-2 py-1">Fim</th>
                  <th className="text-right px-2 py-1">ZCRS</th>
                  <th className="text-right px-2 py-1">Custo</th>
                  <th className="text-right px-2 py-1">Tokens</th>
                </tr>
              </thead>
              <tbody>
                {pageRuns.map((r, idx) => (
                  <tr key={r.id} className={`border-t border-neutral-200 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-900/40 ${idx % 2 === 1 ? 'bg-neutral-50/40 dark:bg-neutral-900/30' : ''}`}>
                    <td className="px-2 py-1"><a className="text-blue-600 font-mono text-xs" href={`/runs/${r.id}`}>{r.id}</a></td>
                    <td className="px-2 py-1"><span className="px-2 py-0.5 border rounded-md text-xs">{r.engine}</span></td>
                    <td className="px-2 py-1">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        r.status === 'completed' ? 'bg-green-100 text-green-800' :
                        r.status === 'failed' ? 'bg-red-100 text-red-800' :
                        r.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>{r.status}</span>
                    </td>
                    <td className="px-2 py-1">{fmt(r.started_at)}</td>
                    <td className="px-2 py-1">{fmt(r.finished_at)}</td>
                    <td className="px-2 py-1 text-right">{typeof r.zcrs === 'number' ? r.zcrs.toFixed(1) : '-'}</td>
                    <td className="px-2 py-1 text-right">{typeof r.cost_usd === 'number' ? `$${r.cost_usd.toFixed(4)}` : '-'}</td>
                    <td className="px-2 py-1 text-right">{typeof r.tokens_total === 'number' ? r.tokens_total : '-'}</td>
                  </tr>
                ))}
                {!filteredRuns.length && (
                  <tr>
                    <td colSpan={8} className="px-2 py-6">
                      <div className="text-center text-sm opacity-70">Nenhuma run encontrada com os filtros atuais.</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'compare' && (
        <div className="border rounded-md shadow-sm bg-white dark:bg-neutral-900">
          <div className="p-2 flex items-center gap-2">
            <div className="text-sm opacity-70">Comparar respostas de runs do tema</div>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs opacity-70">Runs por grupo</span>
              <Select value={String(limitPerGroup)} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLimitPerGroup(parseInt(e.target.value))}>
                {[3,5,10,20].map(n => <option key={n} value={n}>{n}</option>)}
              </Select>
              <Button variant="secondary" size="sm" onClick={refreshCompare} disabled={loadingCompare}>
                {loadingCompare ? 'Carregando…' : 'Atualizar'}
              </Button>
            </div>
          </div>
          <div className="border-t">
            {loadingCompare && !groups.length ? (
              <div className="p-6 text-sm opacity-70">Carregando…</div>
            ) : !groups.length ? (
              <div className="p-6 text-sm opacity-70">Sem dados para comparar.</div>
            ) : (
              <div className="p-2 space-y-4">
                {groups.map((g, gi) => (
                  <div key={gi} className="border rounded-md">
                    <div className="px-2 py-1 text-sm flex items-center gap-2">
                      <span className="font-medium">{g.subproject_name || '—'}</span>
                      <span className="opacity-60">({g.runs.length} runs)</span>
                    </div>
                    <div className="border-t">
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-2">
                        {g.runs.map(run => (
                          <div key={run.id} className="border rounded-md p-2 bg-white dark:bg-neutral-900">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 border rounded text-xs">{run.engine}</span>
                              <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                                run.status === 'completed' ? 'bg-green-100 text-green-800' :
                                run.status === 'failed' ? 'bg-red-100 text-red-800' :
                                run.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>{run.status}</span>
                              <a className="ml-auto text-xs text-blue-600" href={`/runs/${run.id}`}>abrir</a>
                            </div>
                            <div className="mt-2 text-xs opacity-70">Prompt</div>
                            <div className="text-xs whitespace-pre-wrap max-h-24 overflow-auto break-anywhere">{run.prompt_text || '-'}</div>
                            {!!run.evidences?.length && (
                              <div className="mt-2">
                                <div className="text-xs font-medium mb-1">Evidências</div>
                                <div className="space-y-1">
                                  {run.evidences.map(ev => (
                                    <details key={ev.id} className="text-xs">
                                      <summary className="cursor-pointer">Evidência {ev.id.slice(0, 8)}</summary>
                                      <pre className="mt-1 p-2 rounded bg-neutral-50 dark:bg-neutral-900 overflow-auto max-h-48 text-[11px] break-anywhere">
                                        {JSON.stringify(ev.parsed_json, null, 2)}
                                      </pre>
                                    </details>
                                  ))}
                                </div>
                              </div>
                            )}
                            {!run.evidences?.length && <div className="mt-2 text-xs opacity-60">Sem evidências.</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'insights' && (
        <InsightsPanel subprojectId={id || ''} />
      )}
      <Toaster richColors position="top-right" />
    </div>
  )
}

function Card({ title, value }: { title: string; value: React.ReactNode }) {
  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4">
      <div className="text-xs text-neutral-500">{title}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}

function InsightsPanel({ subprojectId }: { subprojectId: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<{
    summary: string[]
    recommendations: { title: string; impact?: string; effort?: string }[]
    quick_wins: string[]
    topics: string[]
    keywords: string[]
    wordcloud: { token: string; weight: number }[]
  } | null>(null)

  const generate = async () => {
    if (!subprojectId) return
    setLoading(true)
    setError(null)
    try {
      const r = await axios.post(`${API}/analytics/subprojects/${subprojectId}/generate-insights`)
      setData(r.data)
      toast.success('Insights gerados com sucesso')
    } catch (e: any) {
      setError(e?.message || 'Falha ao gerar insights')
      toast.error('Falha ao gerar insights')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border rounded-md">
      <div className="p-2 flex items-center gap-2">
        <div className="text-sm opacity-70">Gerar insights do tema</div>
        <div className="ml-auto">
          <Button onClick={generate} disabled={loading}>
            {loading ? 'Gerando…' : 'Gerar insight'}
          </Button>
        </div>
      </div>
      {error && <div className="px-3 pb-2 text-sm text-red-600">{error}</div>}
      {!data && !loading && (
        <div className="px-3 pb-4 text-sm opacity-70">Clique em “Gerar insight” para consolidar as runs e obter recomendações acionáveis.</div>
      )}
      {data && (
        <div className="p-3 grid gap-4">
          {/* Debug opcional do JSON */}
          <details className="text-xs opacity-80">
            <summary className="cursor-pointer">Ver JSON</summary>
            <pre className="mt-2 p-2 rounded bg-neutral-50 dark:bg-neutral-900 overflow-auto max-h-60 text-[11px]">
              {JSON.stringify(data, null, 2)}
            </pre>
          </details>
          {!!data.summary?.length && (
            <section>
              <div className="text-sm font-medium mb-1">Resumo executivo</div>
              <ul className="list-disc pl-5 text-sm">
                {data.summary.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </section>
          )}
          {!data.summary?.length && <div className="text-sm opacity-60">Sem resumo.</div>}
          {!!data.recommendations?.length && (
            <section>
              <div className="text-sm font-medium mb-1">Recomendações priorizadas</div>
              <ul className="grid gap-2">
                {data.recommendations.map((r, i) => (
                  <li key={i} className="p-2 rounded border">
                    <div className="text-sm font-medium">{r.title}</div>
                    <div className="text-xs opacity-70">Impacto: {r.impact || '-'} · Esforço: {r.effort || '-'}</div>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {!data.recommendations?.length && <div className="text-sm opacity-60">Sem recomendações.</div>}
          {!!data.quick_wins?.length && (
            <section>
              <div className="text-sm font-medium mb-1">Quick wins</div>
              <ul className="list-disc pl-5 text-sm">
                {data.quick_wins.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </section>
          )}
          {!data.quick_wins?.length && <div className="text-sm opacity-60">Sem quick wins.</div>}
          {!!data.topics?.length && (
            <section>
              <div className="text-sm font-medium mb-1">Tópicos e lacunas</div>
              <div className="flex flex-wrap gap-2">
                {data.topics.map((t, i) => <span key={i} className="px-2 py-0.5 rounded-full border text-xs">{t}</span>)}
              </div>
            </section>
          )}
          {!data.topics?.length && <div className="text-sm opacity-60">Sem tópicos destacados.</div>}
          {!!data.keywords?.length && (
            <section>
              <div className="text-sm font-medium mb-1">Palavras‑chave sugeridas</div>
              <div className="flex flex-wrap gap-2">
                {data.keywords.map((t, i) => <span key={i} className="px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-xs">{t}</span>)}
              </div>
            </section>
          )}
          {!data.keywords?.length && <div className="text-sm opacity-60">Sem palavras‑chave sugeridas.</div>}
          {!!data.wordcloud?.length && (
            <section>
              <div className="text-sm font-medium mb-1">Wordcloud (esboço)</div>
              <div className="flex flex-wrap gap-1">
                {data.wordcloud.map((w, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded text-xs border" style={{ opacity: Math.max(0.4, Math.min(1, w.weight / (data.wordcloud[0]?.weight || 1))) }}>
                    {w.token}
                  </span>
                ))}
              </div>
            </section>
          )}
          {!data.wordcloud?.length && <div className="text-sm opacity-60">Sem dados de wordcloud.</div>}
        </div>
      )}
    </div>
  )
}
