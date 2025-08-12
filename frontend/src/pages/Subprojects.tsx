import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { BarChart2, ExternalLink, Play } from 'lucide-react'

const API = '/api'

type Project = { id: string; name: string }

type Subproject = { id: string; name: string; description?: string }

type KPIs = { total_runs: number; amr_avg: number; dcr_avg: number; zcrs_avg: number }

export default function SubprojectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [items, setItems] = useState<Subproject[]>([])
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [kpis, setKpis] = useState<Record<string, KPIs>>({})
  const [showCreate, setShowCreate] = useState(false)

  const loadProjects = async () => {
    const res = await axios.get(`${API}/projects`)
    const list = res.data as Project[]
    setProjects(list)
    if (!projectId && list[0]?.id) {
      setProjectId(list[0].id)
      localStorage.setItem('project_id', list[0].id)
    }
  }

  const ensureProject = async (): Promise<string | null> => {
    try {
      if (projectId) return projectId
      await loadProjects()
      if (projects[0]?.id) return projects[0].id
      const created = await axios.post(`${API}/projects`, { name: 'Projeto Demo', country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
      const id = created.data.id as string
      setProjectId(id)
      localStorage.setItem('project_id', id)
      await loadProjects()
      return id
    } catch {
      return null
    }
  }

  const refresh = async () => {
    const pid = await ensureProject()
    if (!pid) return
    const res = await axios.get(`${API}/projects/${pid}/subprojects`)
    setItems(res.data)
    const entries = await Promise.all(res.data.map(async (sp: Subproject) => {
      try {
        const r = await axios.get(`${API}/analytics/subprojects/${sp.id}/overview`)
        return [sp.id, r.data]
      } catch { return [sp.id, { total_runs: 0, amr_avg: 0, dcr_avg: 0, zcrs_avg: 0 }] }
    }))
    const map: Record<string, KPIs> = {}
    entries.forEach(([id, data]: any) => map[id] = data)
    setKpis(map)
  }

  useEffect(() => { loadProjects().then(refresh) }, [])

  const createQuickProject = async () => {
    const created = await axios.post(`${API}/projects`, { name: 'Projeto Demo', country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
    const id = created.data.id as string
    setProjectId(id)
    localStorage.setItem('project_id', id)
    await loadProjects()
    await refresh()
  }

  const create = async () => {
    const pid = await ensureProject()
    if (!pid || !name.trim()) return
    await axios.post(`${API}/projects/${pid}/subprojects`, { name: name.trim(), description: desc || null })
    setName(''); setDesc(''); setShowCreate(false)
    await refresh()
  }

  const setFocus = (id: string) => {
    localStorage.setItem('theme_focus', id)
    localStorage.setItem('subproject_focus', id)
    alert('Foco do tema definido para o dashboard.')
  }

  return (
    <div className="space-y-3">
      <ActiveContextBar />
      <h1 className="text-2xl font-semibold">Temas</h1>
      <div className="flex flex-wrap gap-2 items-center">
        <Select value={projectId} onChange={(e) => { setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value); refresh() }}>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
        </Select>
        <Button variant="secondary" onClick={refresh}>Atualizar</Button>
        <Button variant="outline" onClick={createQuickProject}>Criar rápido</Button>
        <div className="ml-auto" />
        <Button onClick={() => setShowCreate(true)}>+ Novo Tema</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {items.map(sp => (
          <SubprojectCard key={sp.id} sp={sp} kpi={kpis[sp.id]} onFocus={setFocus} />
        ))}
        {!items.length && <div className="text-sm opacity-70">Nenhum tema.</div>}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-lg p-4 w-[min(560px,100%)] space-y-3 border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-lg font-semibold">Novo Tema</h2>
            <Input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} />
            <Input placeholder="Descrição (opcional)" value={desc} onChange={(e) => setDesc(e.target.value)} />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => { setShowCreate(false); setName(''); setDesc('') }}>Cancelar</Button>
              <Button onClick={create}>Criar</Button>
            </div>
          </div>
        </div>
      )}
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

function Bar({ value, className }: { value: number; className: string }) {
  return (
    <div className="h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-800">
      <div className={`h-2 rounded-full ${className}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

function SubprojectCard({ sp, kpi, onFocus }: { sp: Subproject; kpi?: KPIs; onFocus: (id: string) => void }) {
  const amr = Math.round((kpi?.amr_avg || 0) * 100)
  const dcr = Math.round((kpi?.dcr_avg || 0) * 100)
  const zcrs = Math.round((kpi?.zcrs_avg || 0))
  const totalRuns = kpi?.total_runs || 0
  return (
    <div className="border rounded-xl p-4 space-y-3 bg-white dark:bg-neutral-900 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="text-lg font-semibold flex-1">{sp.name}</div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" title="Focar no dashboard" onClick={() => onFocus(sp.id)}><BarChart2 className="h-4 w-4" /></Button>
          <a href={`/subprojects/${sp.id}`} title="Abrir detalhes" className="px-2 py-1 border rounded-md"><ExternalLink className="h-4 w-4" /></a>
          <a href={`/runs`} title="Ver runs" className="px-2 py-1 border rounded-md"><Play className="h-4 w-4" /></a>
        </div>
      </div>
      <div className="text-sm opacity-70">Monitoramento para {sp.name.toLowerCase()}</div>
      <div className="space-y-2">
        <div className="text-xs">AMR</div>
        <Bar value={amr} className="bg-blue-500" />
        <div className="text-xs">DCR</div>
        <Bar value={dcr} className="bg-green-500" />
        <div className="text-xs">ZCRS</div>
        <Bar value={zcrs} className="bg-purple-500" />
      </div>
      <div className="text-xs opacity-70">{totalRuns} Runs</div>
    </div>
  )
}

