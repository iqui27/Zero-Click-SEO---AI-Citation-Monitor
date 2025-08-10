import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts'

const API = '/api'

type Overview = { total_runs: number; amr_avg: number; dcr_avg: number; zcrs_avg: number }

type SeriesPoint = { day: string; zcrs_avg: number }

type TopDomain = { domain: string; count: number }

export default function SubprojectDetail() {
  const { id } = useParams()
  const [ov, setOv] = useState<Overview | null>(null)
  const [series, setSeries] = useState<SeriesPoint[]>([])
  const [tops, setTops] = useState<TopDomain[]>([])

  useEffect(() => {
    if (!id) return
    axios.get(`${API}/analytics/subprojects/${id}/overview`).then(r => setOv(r.data))
    axios.get(`${API}/analytics/subprojects/${id}/series`).then(r => setSeries(r.data))
    axios.get(`${API}/analytics/subprojects/${id}/top-domains`).then(r => setTops(r.data))
  }, [id])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Subprojeto {id}</h1>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <Card title="Total Runs" value={ov?.total_runs ?? 0} />
        <Card title="AMR médio" value={(ov?.amr_avg ?? 0).toFixed(2)} />
        <Card title="DCR médio" value={(ov?.dcr_avg ?? 0).toFixed(2)} />
        <Card title="ZCRS médio" value={(ov?.zcrs_avg ?? 0).toFixed(1)} />
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
      <div>
        <Link to="/runs" className="px-3 py-2 border rounded-md">Ver Runs</Link>
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
