import React, { useEffect, useMemo, useState } from 'react'
import { getProjects, getTemplates, createTemplate, deleteTemplate, getSubprojects } from '../lib/api'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Toaster, toast } from 'sonner'
import { Copy, Plus, Trash2 } from 'lucide-react'


type Template = { id: string; category: string; name: string; text: string; intent?: string; persona?: string; subproject_id?: string }
type Subproject = { id: string; name: string }

enum Mode { View, Edit, Create }

export default function TemplatesPage() {
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [projects, setProjects] = useState<Array<{id:string; name:string}>>([])
  const [items, setItems] = useState<Template[]>([])
  const [category, setCategory] = useState<string>('')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState<string>('')
  const [mode, setMode] = useState<Mode>(Mode.View)
  const [form, setForm] = useState<Partial<Template>>({ category: '', name: '', text: '', subproject_id: '' })
  const [loading, setLoading] = useState(false)
  const [customCats, setCustomCats] = useState<string[]>([])
  const [showNewCat, setShowNewCat] = useState(false)
  const [newCatName, setNewCatName] = useState('')

  const refresh = async () => {
    if (!projectId) return
    const res = await getTemplates(projectId, category, subprojectId || undefined)
    setItems(res)
  }

  useEffect(() => { refresh() }, [projectId, category, subprojectId])
  useEffect(() => {
    getProjects().then(r => {
      setProjects(r)
      if (!projectId && r[0]?.id) {
        setProjectId(r[0].id)
        localStorage.setItem('project_id', r[0].id)
      }
    })
  }, [])

  useEffect(() => {
    if (!projectId) return
    getSubprojects(projectId).then(setSubprojects)
  }, [projectId])

  const categories = useMemo(() => Array.from(new Set(items.map(i => i.category))).sort(), [items])
  const catOptions = useMemo(() => Array.from(new Set([...(categories||[]), ...(customCats||[])])).filter(Boolean).sort(), [categories, customCats])

  const save = async () => {
    if (!projectId) return toast.error('Selecione um projeto')
    if (!form.name?.trim() || !form.text?.trim()) return toast.error('Preencha nome e texto')
    setLoading(true)
    try {
      await createTemplate(projectId, {
        category: form.category || 'Geral',
        name: form.name?.trim(),
        text: form.text?.trim(),
        intent: form.intent,
        persona: form.persona,
        subproject_id: form.subproject_id || null,
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
    await deleteTemplate(id)
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
        <Select value={subprojectId} onChange={(e) => setSubprojectId(e.target.value)}>
          <option value="">Todos os temas</option>
          {subprojects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>
      </div>

      {mode === Mode.Create && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-lg p-4 w-[min(780px,100%)] space-y-3 border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-lg font-semibold">Novo Template</h2>
            <div className="grid gap-2">
              <div className="grid gap-1">
                <div className="flex items-center gap-2">
                  <Select value={form.category || ''} onChange={(e)=>setForm({ ...form, category: e.target.value })} className="min-w-[240px]">
                    <option value="">Selecione uma categoria</option>
                    {catOptions.map(c => (<option key={c} value={c}>{c}</option>))}
                  </Select>
                  <Button variant="outline" size="sm" onClick={()=>setShowNewCat(v=>!v)}>{showNewCat ? 'Cancelar' : '+ Nova categoria'}</Button>
                </div>
                {showNewCat && (
                  <div className="flex items-center gap-2">
                    <Input placeholder="Nome da categoria" value={newCatName} onChange={(e)=>setNewCatName(e.target.value)} />
                    <Button size="sm" onClick={()=>{
                      const name = newCatName.trim()
                      if (!name) return
                      if (!catOptions.includes(name)) setCustomCats(prev => [...prev, name])
                      setForm(f => ({ ...f, category: name }))
                      setNewCatName('')
                      setShowNewCat(false)
                    }}>Adicionar</Button>
                  </div>
                )}
                <div className="grid gap-1 mt-2">
                  <div className="text-sm text-neutral-500">Tema (opcional)</div>
                  <Select value={form.subproject_id || ''} onChange={(e)=>setForm({ ...form, subproject_id: e.target.value })} className="min-w-[240px]">
                    <option value="">—</option>
                    {subprojects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </Select>
                </div>
              </div>
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
              {t.subproject_id && (
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-800">
                  {subprojects.find(s => s.id === t.subproject_id)?.name || 'Tema'}
                </span>
              )}
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
