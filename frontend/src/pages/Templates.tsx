import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Toaster, toast } from 'sonner'
import { Copy, Plus, Trash2 } from 'lucide-react'

const API = '/api'

type Template = { id: string; category: string; name: string; text: string; intent?: string; persona?: string }

enum Mode { View, Edit, Create }

export default function TemplatesPage() {
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [projects, setProjects] = useState<Array<{id:string; name:string}>>([])
  const [items, setItems] = useState<Template[]>([])
  const [category, setCategory] = useState<string>('')
  const [mode, setMode] = useState<Mode>(Mode.View)
  const [form, setForm] = useState<Partial<Template>>({ category: '', name: '', text: '' })
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    if (!projectId) return
    const res = await axios.get(`${API}/projects/${projectId}/templates`, { params: category ? { category } : {} })
    setItems(res.data)
  }

  useEffect(() => { refresh() }, [projectId, category])
  useEffect(() => {
    axios.get(`${API}/projects`).then(r => {
      setProjects(r.data)
      if (!projectId && r.data[0]?.id) {
        setProjectId(r.data[0].id)
        localStorage.setItem('project_id', r.data[0].id)
      }
    })
  }, [])

  const categories = useMemo(() => Array.from(new Set(items.map(i => i.category))).sort(), [items])

  const save = async () => {
    if (!projectId) return toast.error('Selecione um projeto')
    if (!form.name?.trim() || !form.text?.trim()) return toast.error('Preencha nome e texto')
    setLoading(true)
    try {
      await axios.post(`${API}/projects/${projectId}/templates`, {
        category: form.category || 'Geral',
        name: form.name?.trim(),
        text: form.text?.trim(),
        intent: form.intent,
        persona: form.persona,
      })
      setMode(Mode.View)
      setForm({})
      await refresh()
      toast.success('Template criado')
    } catch (e: any) {
      toast.error('Falha ao criar template: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  const clone = async (tpl: Template) => {
    setForm({ category: tpl.category, name: `${tpl.name} (cópia)`, text: tpl.text, intent: tpl.intent, persona: tpl.persona })
    setMode(Mode.Create)
  }

  const copyText = async (tpl: Template) => {
    await navigator.clipboard.writeText(tpl.text)
    toast.success('Texto copiado')
  }

  const remove = async (id: string) => {
    if (!confirm('Remover template?')) return
    await axios.delete(`${API}/templates/${id}`)
    await refresh()
    toast.success('Template removido')
  }

  return (
    <div className="space-y-3">
      <Toaster richColors position="top-right" />
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Templates</h1>
        <Button className="ml-auto" onClick={() => setMode(Mode.Create)}><Plus className="h-4 w-4 mr-1" /> Novo Template</Button>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <Select value={projectId} onChange={(e) => { setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value) }}>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
        </Select>
        <Select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Todas as categorias</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </Select>
      </div>

      {mode === Mode.Create && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-lg p-4 w-[min(780px,100%)] space-y-3 border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-lg font-semibold">Novo Template</h2>
            <div className="grid gap-2">
              <Input placeholder="Categoria" value={form.category || ''} onChange={(e) => setForm({ ...form, category: e.target.value })} />
              <Input placeholder="Nome" value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <textarea placeholder="Texto do prompt" value={form.text || ''} onChange={(e) => setForm({ ...form, text: e.target.value })} rows={8} className="border rounded-md px-2 py-2 bg-transparent"></textarea>
              <div className="flex gap-2 justify-end">
                <Button variant="ghost" onClick={() => { setMode(Mode.View); setForm({}) }}>Cancelar</Button>
                <Button onClick={save} disabled={loading}>{loading ? 'Salvando…' : 'Salvar'}</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-2">
        {items.map(t => (
          <div key={t.id} className="border rounded-md p-3">
            <div className="flex items-center gap-2">
              <span className="text-xs opacity-70">{t.category}</span>
              <strong className="flex-1">{t.name}</strong>
              <Button variant="outline" size="sm" onClick={() => copyText(t)} title="Copiar"><Copy className="h-4 w-4" /></Button>
              <Button variant="outline" size="sm" onClick={() => clone(t)} title="Clonar">Clonar</Button>
              <Button variant="outline" size="sm" onClick={() => remove(t.id)} title="Remover"><Trash2 className="h-4 w-4" /></Button>
            </div>
            <pre className="whitespace-pre-wrap text-sm opacity-90 mt-2">{t.text}</pre>
          </div>
        ))}
        {!items.length && <div className="text-sm opacity-70">Nenhum template.</div>}
      </div>
    </div>
  )
}
