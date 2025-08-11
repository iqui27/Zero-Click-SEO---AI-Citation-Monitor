import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts'

const API = '/api'

type Overview = { total_runs: number; amr_avg: number; dcr_avg: number; zcrs_avg: number }

type SeriesPoint = { day: string; zcrs_avg: number }

type TopDomain = { domain: string; count: number }

type RunItem = {
  id: string
  engine: string
  status: string
  started_at?: string
  finished_at?: string
  zcrs?: number
  amr_flag?: boolean
  dcr_flag?: boolean
  template_name?: string
  subproject_name?: string
  cost_usd?: number
  tokens_total?: number
}

type PerfByEngine = { engine: string; amr_avg: number; dcr_avg: number; zcrs_avg: number; runs: number }

export default function SubprojectDetail() {
  const { id } = useParams()
  const [ov, setOv] = useState<Overview | null>(null)
  const [series, setSeries] = useState<SeriesPoint[]>([])
  const [tops, setTops] = useState<TopDomain[]>([])
  const [runs, setRuns] = useState<RunItem[]>([])
  const [perf, setPerf] = useState<PerfByEngine[]>([])
  const [projectName, setProjectName] = useState<string>('')
  const [projectId, setProjectId] = useState<string>('')
  const [subprojectName, setSubprojectName] = useState<string>('')

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
            break
          }
        }
      } catch {}
    }
    resolveNames()
  }, [id])

  // agregados simples sobre a amostra de runs carregadas
  const sampleCost = runs.reduce((acc, r) => acc + (r.cost_usd || 0), 0)
  const sampleTokens = runs.reduce((acc, r) => acc + (r.tokens_total || 0), 0)

  return (
    <div className="space-y-4 px-3 sm:px-4 md:px-6 max-w-[1200px] mx-auto">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">{subprojectName || `Subprojeto ${id}`}</h1>
        {projectName && (
          <span className="text-xs px-2 py-1 rounded-full border border-neutral-300 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300">Projeto: {projectName}</span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <a className="px-3 py-2 border rounded-md text-sm" href={`${API}/analytics/subprojects/${id}/export.csv`}>Exportar CSV</a>
          <Link to="/runs" className="px-3 py-2 border rounded-md text-sm">Ver Runs</Link>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-6 gap-2">
        <Card title="Total Runs" value={ov?.total_runs ?? 0} />
        <Card title="AMR médio" value={(ov?.amr_avg ?? 0).toFixed(2)} />
        <Card title="DCR médio" value={(ov?.dcr_avg ?? 0).toFixed(2)} />
        <Card title="ZCRS médio" value={(ov?.zcrs_avg ?? 0).toFixed(1)} />
        <Card title="Custo (amostra)" value={`$${sampleCost.toFixed(4)}`} />
        <Card title="Tokens (amostra)" value={sampleTokens} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="col-span-2 h-280 border rounded-md p-2">
          <div className="text-sm opacity-70 mb-1">ZCRS médio por dia</div>
          <div style={{ height: 260 }}>
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
        <div className="border rounded-md p-2">
          <div className="text-sm opacity-70 mb-1">Domínios mais citados</div>
          <ul className="text-sm list-decimal pl-5">
            {tops.map((t, i) => (
              <li key={i} className="truncate">{t.domain} — {t.count}</li>
            ))}
            {!tops.length && <div className="text-sm opacity-70">Sem dados.</div>}
          </ul>
        </div>
      </div>

      {!!perf.length && (
        <div className="border rounded-md p-2">
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

      <div className="border rounded-md">
        <div className="p-2 text-sm opacity-70">Últimas runs do subprojeto</div>
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
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
              {runs.map((r) => (
                <tr key={r.id} className="border-t border-neutral-200 dark:border-neutral-800">
                  <td className="px-2 py-1"><a className="text-blue-600" href={`/runs/${r.id}`}>{r.id}</a></td>
                  <td className="px-2 py-1">{r.engine}</td>
                  <td className="px-2 py-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                      r.status === 'completed' ? 'bg-green-100 text-green-800' :
                      r.status === 'failed' ? 'bg-red-100 text-red-800' :
                      r.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>{r.status}</span>
                  </td>
                  <td className="px-2 py-1">{r.started_at || '-'}</td>
                  <td className="px-2 py-1">{r.finished_at || '-'}</td>
                  <td className="px-2 py-1 text-right">{typeof r.zcrs === 'number' ? r.zcrs.toFixed(1) : '-'}</td>
                  <td className="px-2 py-1 text-right">{typeof r.cost_usd === 'number' ? `$${r.cost_usd.toFixed(4)}` : '-'}</td>
                  <td className="px-2 py-1 text-right">{typeof r.tokens_total === 'number' ? r.tokens_total : '-'}</td>
                </tr>
              ))}
              {!runs.length && (
                <tr>
                  <td colSpan={8} className="px-2 py-3 text-sm opacity-70">Nenhuma run encontrada.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
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
