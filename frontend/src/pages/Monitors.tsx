import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'

const API = '/api'

const CRON_PRESETS = [
  { label: 'Diário 02:00', cron: '0 2 * * *' },
  { label: 'Dias úteis 06:00', cron: '0 6 * * 1-5' },
  { label: 'Semanal (domingo 03:00)', cron: '0 3 * * 0' },
]

type Monitor = { id: string; name: string; subproject_id?: string; schedule_cron?: string; engines_json: any; active: boolean }

type Template = { id: string; category: string; name: string }

type Subproject = { id: string; name: string }

async function getMonitorRuns(monitorId: string) {
  const res = await axios.get(`${API}/monitors/${monitorId}/runs`)
  return res.data as { id: string; status: string; started_at?: string; finished_at?: string; zcrs?: number }[]
}

export default function MonitorsPage() {
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [items, setItems] = useState<Monitor[]>([])
  const [name, setName] = useState('')
  const [schedule, setSchedule] = useState('')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState('')
  const [engines, setEngines] = useState('[{"name":"gemini","region":"BR","device":"desktop","config_json":{"model":"gemini-2.5-pro"}}]')
  const [templates, setTemplates] = useState<Template[]>([])

  const refresh = async () => {
    if (!projectId) return
    const res = await axios.get(`${API}/projects/${projectId}/monitors`)
    setItems(res.data)
    axios.get(`${API}/projects/${projectId}/subprojects`).then(r => setSubprojects(r.data))
    axios.get(`${API}/projects/${projectId}/templates`).then(r => setTemplates(r.data))
  }
  useEffect(() => { refresh() }, [projectId])

  const create = async () => {
    await axios.post(`${API}/projects/${projectId}/monitors`, {
      name,
      subproject_id: subprojectId || null,
      schedule_cron: schedule || null,
      engines_json: { engines: JSON.parse(engines) },
    })
    setName(''); setSchedule(''); setEngines('[{"name":"gemini","region":"BR","device":"desktop","config_json":{"model":"gemini-2.5-pro"}}]')
    await refresh()
  }

  const attachTemplate = async (monitorId: string, templateId: string) => {
    await axios.post(`${API}/monitors/${monitorId}/templates/${templateId}`)
    await refresh()
  }

  const runNow = async (monitorId: string) => {
    const res = await axios.post(`${API}/monitors/${monitorId}/run`)
    alert(`Runs enfileiradas: ${res.data.queued_runs.length}`)
  }

  const removeTemplate = async (monitorId: string, templateId: string) => {
    await axios.delete(`${API}/monitors/${monitorId}/templates/${templateId}`)
  }

  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Monitores</h1>
      <div className="flex gap-2 items-center">
        <Input placeholder="Project ID" value={projectId} onChange={(e) => { setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value) }} />
      </div>

      <div className="border rounded-md p-3 grid gap-2">
        <div className="text-sm opacity-70">Criar monitor</div>
        <Input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} />
        <Select value={subprojectId} onChange={(e) => setSubprojectId(e.target.value)}>
          <option value="">(Sem subprojeto)</option>
          {subprojects.map(sp => <option key={sp.id} value={sp.id}>{sp.name}</option>)}
        </Select>
        <Input placeholder="CRON (opcional)" value={schedule} onChange={(e) => setSchedule(e.target.value)} />
        <textarea placeholder='Engines (JSON array)' value={engines} onChange={(e) => setEngines(e.target.value)} rows={3} className="border rounded-md px-2 py-2 bg-transparent" />
        <div className="flex justify-end"><Button onClick={create}>Criar</Button></div>
      </div>

      <div className="grid gap-3">
        {items.map(m => (
          <div key={m.id} className="border rounded-md p-3 space-y-2">
            <div className="flex items-center gap-2">
              <strong className="flex-1">{m.name}</strong>
              <span className="text-xs opacity-70">{m.id}</span>
              <Button variant="secondary" onClick={() => runNow(m.id)}>Executar agora</Button>
            </div>
            <div className="text-xs opacity-70">Subprojeto: {m.subproject_id || '—'} | Engines: {JSON.stringify(m.engines_json.engines)}</div>
            <div className="grid gap-1">
              <div className="text-sm opacity-70">Vincular template</div>
              <div className="flex flex-wrap gap-2">
                {templates.map(t => (
                  <Button key={t.id} variant="outline" size="sm" onClick={() => attachTemplate(m.id, t.id)}>{t.category} • {t.name}</Button>
                ))}
              </div>
            </div>
            <div className="grid gap-1">
              <div className="text-sm opacity-70">Histórico</div>
              <MonitorRuns monitorId={m.id} />
            </div>
            <div className="flex items-center gap-2">
              <Select value={m.schedule_cron || ''} onChange={async (e)=>{ await axios.patch(`${API}/monitors/${m.id}`, { schedule_cron: e.target.value || null }); await refresh() }}>
                <option value="">(sem agendamento)</option>
                {CRON_PRESETS.map(p => <option key={p.cron} value={p.cron}>{p.label}</option>)}
              </Select>
              <label className="flex items-center gap-1 text-xs">
                <input type="checkbox" defaultChecked={m.active} onChange={async (e)=>{ await axios.patch(`${API}/monitors/${m.id}`, { active: e.target.checked }); await refresh() }} /> ativo
              </label>
            </div>
          </div>
        ))}
        {!items.length && <div className="text-sm opacity-70">Nenhum monitor.</div>}
      </div>
    </div>
  )
}

function MonitorRuns({ monitorId }: { monitorId: string }) {
  const [runs, setRuns] = useState<any[]>([])
  useEffect(() => { getMonitorRuns(monitorId).then(setRuns) }, [monitorId])
  return (
    <div className="overflow-auto text-xs">
      <table className="min-w-full">
        <thead><tr><th className="text-left p-1">Run</th><th className="text-left p-1">Status</th><th className="text-left p-1">Início</th><th className="text-left p-1">ZCRS</th></tr></thead>
        <tbody>
          {runs.map(r => (
            <tr key={r.id} className="border-t border-neutral-800">
              <td className="p-1"><a className="text-blue-600" href={`/runs/${r.id}`}>{r.id}</a></td>
              <td className="p-1">{r.status}</td>
              <td className="p-1">{r.started_at || '-'}</td>
              <td className="p-1">{r.zcrs ?? '-'}</td>
            </tr>
          ))}
          {!runs.length && <tr><td className="p-1" colSpan={4}>Sem runs.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
