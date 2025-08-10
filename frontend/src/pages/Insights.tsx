import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Toaster, toast } from 'sonner'

const API = '/api'

type Insight = {
  id: string
  project_id: string
  run_id?: string
  title: string
  description?: string
  impact?: number
  effort?: number
  status?: string
  assignee?: string
}

export default function InsightsPage() {
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([])
  const [items, setItems] = useState<Insight[]>([])
  const [status, setStatus] = useState<string>('')
  const [impactMin, setImpactMin] = useState<string>('')
  const [q, setQ] = useState<string>('')

  const refresh = async () => {
    if (!projectId) return
    const res = await axios.get(`${API}/insights`, { params: { project_id: projectId } })
    setItems(res.data)
  }

  useEffect(() => {
    axios.get(`${API}/projects`).then(r => {
      setProjects(r.data)
      if (!projectId && r.data[0]?.id) {
        setProjectId(r.data[0].id)
        localStorage.setItem('project_id', r.data[0].id)
      }
    })
  }, [])

  useEffect(() => { refresh() }, [projectId])

  const filtered = useMemo(() => {
    return items.filter(i => {
      if (status && (i.status || '').toLowerCase() !== status) return false
      if (impactMin && (i.impact || 0) < parseInt(impactMin)) return false
      if (q) {
        const txt = `${i.title} ${i.description || ''}`.toLowerCase()
        if (!txt.includes(q.toLowerCase())) return false
      }
      return true
    })
  }, [items, status, impactMin, q])

  const copy = async (i: Insight, format: 'md'|'html') => {
    const header = `# ${i.title}\n\n`
    const body = i.description || ''
    const meta = `\n\nImpacto: ${i.impact ?? '-'} | Esforço: ${i.effort ?? '-'} | Status: ${i.status ?? 'open'}`
    const run = i.run_id ? `\n\nRun: ${window.location.origin}/runs/${i.run_id}` : ''
    const md = header + body + meta + run
    const html = `<article><h1>${escapeHtml(i.title)}</h1><p>${escapeHtml(body)}</p><p>Impacto: ${i.impact ?? '-'} | Esforço: ${i.effort ?? '-'} | Status: ${i.status ?? 'open'}</p>${i.run_id ? `<p>Run: <a href="${window.location.origin}/runs/${i.run_id}">${i.run_id}</a></p>` : ''}</article>`
    await navigator.clipboard.writeText(format === 'md' ? md : html)
    toast.success(format === 'md' ? 'Markdown copiado' : 'HTML copiado')
  }

  const createTask = async (i: Insight) => {
    // Sem integração direta: copiar payload formatado para colar no Linear
    await copy(i, 'md')
    toast.info('Conteúdo copiado. Cole no Linear para criar a tarefa.')
  }

  return (
    <div className="space-y-3">
      <Toaster richColors position="top-right" />
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Insights</h1>
        <Button className="ml-auto" variant="secondary" onClick={refresh}>Atualizar</Button>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <Select value={projectId} onChange={(e) => { setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value) }}>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
        </Select>
        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Todos</option>
          <option value="open">open</option>
          <option value="done">done</option>
        </Select>
        <Select value={impactMin} onChange={(e) => setImpactMin(e.target.value)}>
          <option value="">Impacto ≥ 0</option>
          {[1,2,3,4,5].map(n => <option key={n} value={String(n)}>Impacto ≥ {n}</option>)}
        </Select>
        <Input placeholder="Buscar" value={q} onChange={(e)=>setQ(e.target.value)} />
      </div>
      <div className="grid gap-2">
        {filtered.map(i => (
          <div key={i.id} className="border rounded-md p-3 grid gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-0.5 rounded-md border">Impacto {i.impact ?? '-'}</span>
              <span className="text-xs px-2 py-0.5 rounded-md border">Esforço {i.effort ?? '-'}</span>
              <span className="text-xs px-2 py-0.5 rounded-md border ml-2">{i.status || 'open'}</span>
              <strong className="flex-1">{i.title}</strong>
              {i.run_id && <a href={`/runs/${i.run_id}`} className="text-blue-600 text-xs">ver run</a>}
            </div>
            {i.description && <div className="text-sm opacity-90">{i.description}</div>}
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => copy(i, 'md')}>Copiar MD</Button>
              <Button variant="outline" size="sm" onClick={() => copy(i, 'html')}>Copiar HTML</Button>
              <Button size="sm" onClick={() => createTask(i)}>Criar tarefa</Button>
            </div>
          </div>
        ))}
        {!filtered.length && <div className="text-sm opacity-70">Nenhum insight.</div>}
      </div>
    </div>
  )
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"]{/g as any, (c: string) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'} as any)[c])
}



