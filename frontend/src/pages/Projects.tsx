import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { FolderOpen, LineChart } from 'lucide-react'

const API = '/api'

type Project = { id: string; name: string; country?: string; language?: string }

type Stats = { runs: number; subprojects: number }

export default function ProjectsPage() {
  const [items, setItems] = useState<Project[]>([])
  const [stats, setStats] = useState<Record<string, Stats>>({})
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('Banco Digital')

  const refresh = async () => {
    const res = await axios.get(`${API}/projects`)
    const list = res.data as Project[]
    setItems(list)
    const entries = await Promise.all(list.map(async (p) => {
      try { const r = await axios.get(`${API}/projects/${p.id}/stats`); return [p.id, r.data] as const } catch { return [p.id, { runs: 0, subprojects: 0 }] as const }
    }))
    const map: Record<string, Stats> = {}
    entries.forEach(([id, st]) => { map[id] = st })
    setStats(map)
  }

  useEffect(() => { refresh() }, [])

  const createQuick = async () => {
    setCreating(true)
    try {
      const r = await axios.post(`${API}/projects`, { name, country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
      localStorage.setItem('project_id', r.data.id)
      await refresh()
    } finally {
      setCreating(false)
    }
  }

  const openDetails = (id: string) => {
    localStorage.setItem('project_id', id)
    window.location.href = '/temas'
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Projetos</h1>
        <div className="ml-auto flex items-center gap-2">
          <input value={name} onChange={(e)=>setName(e.target.value)} placeholder="Nome do projeto" className="border rounded-md px-2 py-2 bg-transparent border-neutral-300 dark:border-neutral-700" />
          <Button onClick={createQuick} disabled={creating}>{creating ? 'Criando…' : '+ Novo Projeto'}</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {items.map(p => (
          <div key={p.id} className="border rounded-xl p-4 space-y-3 bg-white dark:bg-neutral-900 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <div className="text-lg font-semibold flex items-center gap-2"><FolderOpen className="h-5 w-5" /> {p.name}</div>
                <div className="text-sm opacity-70">{p.country || '—'} · {p.language || '—'}</div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => openDetails(p.id)}><LineChart className="h-4 w-4 mr-1" /> Ver detalhes</Button>
            </div>
            <div className="text-sm opacity-70">Monitoramento por tema</div>
            <div className="flex items-center gap-6 text-sm">
              <span className="opacity-80">{stats[p.id]?.runs ?? 0} Runs</span>
              <span className="opacity-80">{stats[p.id]?.subprojects ?? 0} Temas</span>
            </div>
          </div>
        ))}
        {!items.length && (
          <div className="border rounded-xl p-6 text-center text-sm opacity-70 bg-white dark:bg-neutral-900">
            Nenhum projeto criado ainda — use “+ Novo Projeto”.
          </div>
        )}
        <div className="border border-dashed rounded-xl p-4 grid place-items-center text-sm opacity-70 bg-white dark:bg-neutral-900">
          <div className="grid gap-2 place-items-center">
            <div className="text-3xl">+</div>
            <div>Criar Rápido</div>
            <Button variant="secondary" onClick={createQuick} disabled={creating}>{creating ? 'Criando…' : 'Criar'}</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
