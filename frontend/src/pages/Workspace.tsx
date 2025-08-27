import React, { useEffect, useMemo, useState } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { getProjects, createProject, updateProject, getSubprojects, createSubproject, updateSubproject, deleteProject, deleteSubproject, type Project, type Subproject } from '../lib/api'
import axios from 'axios'
import { ChevronDown, ChevronRight, FolderOpen, Layers, Pencil, Plus, Search, Sparkles, Trash2, X } from 'lucide-react'
import { Toaster, toast } from 'sonner'

const API = '/api'

// KPI types only for display
 type KPIs = { total_runs: number; amr_avg: number; dcr_avg: number; zcrs_avg: number }

export default function WorkspacePage() {
  // Projects state
  const [projects, setProjects] = useState<Project[]>([])
  const [projectQuery, setProjectQuery] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [creatingProject, setCreatingProject] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [editingProjectId, setEditingProjectId] = useState<string|null>(null)
  const [editProjectName, setEditProjectName] = useState('')

  // Subprojects state
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [kpis, setKpis] = useState<Record<string, KPIs>>({})
  const [showCreateTheme, setShowCreateTheme] = useState(false)
  const [themeName, setThemeName] = useState('')
  const [themeDesc, setThemeDesc] = useState('')
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  // Derived
  const filteredProjects = useMemo(() => {
    const q = projectQuery.trim().toLowerCase()
    if (!q) return projects
    return projects.filter(p => p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q))
  }, [projects, projectQuery])

  const selectedProject = useMemo(() => projects.find(p => p.id === selectedProjectId) || null, [projects, selectedProjectId])

  // Loaders
  const loadProjects = async () => {
    const list = await getProjects()
    setProjects(list)
    if (!selectedProjectId && list[0]?.id) {
      setSelectedProjectId(list[0].id)
      localStorage.setItem('project_id', list[0].id)
    }
  }

  const loadSubprojects = async (pid: string) => {
    try {
      const items = await getSubprojects(pid)
      setSubprojects(items)
      const entries = await Promise.all(items.map(async (sp) => {
        try {
          const r = await axios.get(`${API}/analytics/subprojects/${sp.id}/overview`)
          return [sp.id, r.data as KPIs] as const
        } catch {
          return [sp.id, { total_runs: 0, amr_avg: 0, dcr_avg: 0, zcrs_avg: 0 }] as const
        }
      }))
      const map: Record<string, KPIs> = {}
      entries.forEach(([id, data]) => map[id] = data)
      setKpis(map)
    } catch (e) {
      console.error(e)
    }
  }

  // Effects
  useEffect(() => { loadProjects() }, [])
  useEffect(() => { if (selectedProjectId) loadSubprojects(selectedProjectId) }, [selectedProjectId])

  // Actions: Projects
  const onSelectProject = (id: string) => {
    setSelectedProjectId(id)
    localStorage.setItem('project_id', id)
    setMobileSidebarOpen(false)
  }

  const onCreateProject = async () => {
    const name = (newProjectName || '').trim()
    if (!name) { toast.error('Informe um nome'); return }
    setCreatingProject(true)
    try {
      const p = await createProject({ name, country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
      setNewProjectName('')
      toast.success('Projeto criado')
      await loadProjects()
      onSelectProject(p.id)
    } catch {
      toast.error('Falha ao criar projeto')
    } finally {
      setCreatingProject(false)
    }
  }

  const startEditProject = (p: Project) => {
    setEditingProjectId(p.id)
    setEditProjectName(p.name)
  }

  const saveEditProject = async () => {
    const id = editingProjectId
    if (!id) return
    const newName = editProjectName.trim()
    if (!newName) { toast.error('Nome inválido'); return }
    try {
      await updateProject(id, { name: newName })
      toast.success('Projeto renomeado')
      setEditingProjectId(null)
      setEditProjectName('')
      await loadProjects()
    } catch {
      toast.error('Falha ao renomear projeto')
    }
  }

  const deleteSelectedProject = async () => {
    const id = selectedProjectId
    if (!id) return
    if (!confirm('Excluir este projeto? Esta ação não pode ser desfeita.')) return
    try {
      await deleteProject(id)
      toast.success('Projeto excluído')
      setSelectedProjectId('')
      localStorage.removeItem('project_id')
      setSubprojects([])
      await loadProjects()
    } catch {
      toast.error('Falha ao excluir projeto')
    }
  }

  // Actions: Subprojects
  const onCreateTheme = async () => {
    const name = themeName.trim()
    if (!selectedProjectId || !name) { toast.error('Informe nome do tema'); return }
    try {
      await createSubproject(selectedProjectId, { name, description: themeDesc || undefined })
      setThemeName(''); setThemeDesc(''); setShowCreateTheme(false)
      toast.success('Tema criado')
      await loadSubprojects(selectedProjectId)
    } catch {
      toast.error('Falha ao criar tema')
    }
  }

  const onRenameTheme = async (id: string, newName: string) => {
    const name = (newName || '').trim()
    if (!name) return
    try {
      await updateSubproject(id, { name })
      toast.success('Tema renomeado')
      if (selectedProjectId) await loadSubprojects(selectedProjectId)
    } catch {
      toast.error('Falha ao renomear tema')
    }
  }

  const onDeleteTheme = async (id: string) => {
    if (!confirm('Excluir este tema? Esta ação não pode ser desfeita.')) return
    try {
      await deleteSubproject(id)
      toast.success('Tema excluído')
      if (selectedProjectId) await loadSubprojects(selectedProjectId)
    } catch {
      toast.error('Falha ao excluir tema')
    }
  }

  return (
    <div className="h-full">
      <Toaster position="top-right" richColors />
      {/* Header */}
      <div className="sticky top-0 z-10 backdrop-blur supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-neutral-900/60 border-b border-neutral-200 dark:border-neutral-800">
        <div className="max-w-6xl mx-auto px-3 py-3 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-amber-500" />
          <div className="font-semibold">Projetos & Temas</div>
          <div className="ml-auto flex items-center gap-2">
            {/* Mobile toggle */}
            <Button className="sm:hidden" variant="outline" size="sm" onClick={() => setMobileSidebarOpen(v => !v)}>
              {mobileSidebarOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              <span className="ml-1">Projetos</span>
            </Button>
            {/* Project switcher */}
            <Select value={selectedProjectId} onChange={(e)=>onSelectProject(e.target.value)} className="hidden sm:block">
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
            <Button onClick={() => setShowCreateTheme(true)} disabled={!selectedProjectId}>+ Novo Tema</Button>
          </div>
        </div>
      </div>

      {/* Body layout */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-[minmax(260px,1fr)_2fr] gap-4 p-3">
        {/* Sidebar Projects */}
        <aside className={`transition-all duration-300 overflow-hidden ${mobileSidebarOpen ? 'max-h-[480px] sm:max-h-none' : 'max-h-0 sm:max-h-none'} sm:max-h-none`}>
          <div className="border rounded-xl p-3 bg-white dark:bg-neutral-900 shadow-sm">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="h-4 w-4 absolute left-2 top-2.5 opacity-60" />
                <Input value={projectQuery} onChange={(e)=>setProjectQuery(e.target.value)} placeholder="Buscar projeto" className="pl-8 h-9" />
              </div>
            </div>
            <div className="mt-3 space-y-1 max-h-[50vh] sm:max-h-[66vh] overflow-auto pr-1">
              {filteredProjects.map(p => (
                <button key={p.id}
                  onClick={() => onSelectProject(p.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 transition-all duration-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 ${selectedProjectId===p.id ? 'bg-neutral-100 dark:bg-neutral-800' : ''}`}>
                  <FolderOpen className="h-4 w-4 opacity-70" />
                  <span className="font-medium truncate">{p.name}</span>
                  {selectedProjectId===p.id && <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">ativo</span>}
                </button>
              ))}
              {!filteredProjects.length && <div className="text-xs opacity-70 px-1 py-2">Nenhum projeto.</div>}
            </div>
            <div className="mt-3 border-t pt-3 space-y-2">
              {editingProjectId ? (
                <div className="flex items-center gap-2">
                  <Input value={editProjectName} onChange={(e)=>setEditProjectName(e.target.value)} placeholder="Novo nome" className="h-9" />
                  <Button size="sm" onClick={saveEditProject}>Salvar</Button>
                  <Button size="sm" variant="ghost" onClick={()=>{ setEditingProjectId(null); setEditProjectName('') }}>Cancelar</Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Input value={newProjectName} onChange={(e)=>setNewProjectName(e.target.value)} placeholder="Novo projeto" className="h-9" />
                  <Button size="sm" onClick={onCreateProject} disabled={creatingProject}>{creatingProject ? 'Criando…' : <><Plus className="h-4 w-4" /><span className="ml-1">Criar</span></>}</Button>
                </div>
              )}
              {selectedProject && !editingProjectId && (
                <>
                  <Button size="sm" variant="outline" onClick={()=>startEditProject(selectedProject)} className="w-full"><Pencil className="h-4 w-4 mr-2" /> Renomear selecionado</Button>
                  <Button size="sm" variant="outline" onClick={deleteSelectedProject} className="w-full text-red-600 border-red-200 hover:bg-red-50"><Trash2 className="h-4 w-4 mr-2" /> Apagar projeto</Button>
                </>
              )}
            </div>
          </div>
        </aside>

        {/* Main content: Themes */}
        <section className="min-h-[60vh]">
          <div className="border rounded-xl p-3 sm:p-4 bg-white dark:bg-neutral-900 shadow-sm">
            <div className="flex items-center gap-3">
              <Layers className="h-5 w-5 opacity-70" />
              <h2 className="text-lg font-semibold">Temas do Projeto</h2>
              <span className="text-xs opacity-60">{selectedProject?.name || '—'}</span>
              <div className="ml-auto" />
              <Button variant="secondary" onClick={()=> selectedProjectId && loadSubprojects(selectedProjectId)}>Atualizar</Button>
              <Button onClick={()=>setShowCreateTheme(true)}>+ Novo Tema</Button>
            </div>

            {/* Grid */}
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {subprojects.map(sp => (
                <ThemeCard key={sp.id} sp={sp} kpi={kpis[sp.id]} onRename={onRenameTheme} onDelete={onDeleteTheme} />
              ))}
              {!subprojects.length && (
                <div className="text-sm opacity-70">Nenhum tema. Crie o primeiro com "+ Novo Tema".</div>
              )}
            </div>
          </div>
        </section>
      </div>

      {showCreateTheme && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm grid place-items-center p-4">
          <div className="w-[min(560px,100%)] border rounded-xl bg-white dark:bg-neutral-900 p-4 shadow-xl animate-in fade-in zoom-in duration-200">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold">Novo Tema</h3>
              <button className="ml-auto p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md" onClick={()=>setShowCreateTheme(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-3 space-y-2">
              <Input placeholder="Nome" value={themeName} onChange={(e)=>setThemeName(e.target.value)} />
              <Input placeholder="Descrição (opcional)" value={themeDesc} onChange={(e)=>setThemeDesc(e.target.value)} />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={()=>{ setShowCreateTheme(false); setThemeName(''); setThemeDesc('') }}>Cancelar</Button>
              <Button onClick={onCreateTheme} disabled={!selectedProjectId}>Criar</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ThemeCard({ sp, kpi, onRename, onDelete }: { sp: Subproject; kpi?: KPIs; onRename: (id: string, newName: string) => void | Promise<void>; onDelete: (id: string) => void | Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(sp.name)
  const amr = Math.round((kpi?.amr_avg || 0) * 100)
  const dcr = Math.round((kpi?.dcr_avg || 0) * 100)
  const zcrs = Math.round((kpi?.zcrs_avg || 0))
  const totalRuns = kpi?.total_runs || 0

  return (
    <div className="group relative border rounded-xl p-4 bg-gradient-to-br from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-950 shadow-sm hover:shadow-md transition-shadow duration-300 overflow-hidden">
      <div className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{ background: 'radial-gradient(600px circle at var(--x, 0) var(--y, 0), rgba(168,85,247,0.08), transparent 40%)' }} />
      <div className="flex items-center gap-2 relative">
        <div className="flex-1">
          <div className="text-base font-semibold flex items-center justify-between gap-2 min-w-0">
            {editing ? (
              <>
                <Input className="h-8" value={name} onChange={(e)=>setName(e.target.value)} />
                <Button size="sm" onClick={async ()=>{ await onRename(sp.id, name); setEditing(false) }}>Salvar</Button>
                <Button size="sm" variant="ghost" onClick={()=>{ setEditing(false); setName(sp.name) }}>Cancelar</Button>
              </>
            ) : (
              <>
                <span className="truncate max-w-full leading-tight" title={sp.name}>{sp.name}</span>
                <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    title="Renomear"
                    onClick={()=>{ setEditing(true); setName(sp.name) }}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    title="Excluir tema"
                    onClick={()=> onDelete(sp.id)}
                    className="h-8 w-8 p-0 text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </>
            )}
          </div>
          <div className="text-xs opacity-70">Monitoramento para {sp.name.toLowerCase()}</div>
        </div>
      </div>
      <div className="mt-3 space-y-2">
        <Metric label="AMR" value={amr} color="bg-blue-500" />
        <Metric label="DCR" value={dcr} color="bg-green-500" />
        <Metric label="ZCRS" value={zcrs} color="bg-purple-500" />
      </div>
      <div className="mt-2 text-xs opacity-70">{totalRuns} Runs</div>
    </div>
  )
}

function Metric({ label, value, color }: { label: string; value: number; color: string }) {
  const w = `${Math.max(0, Math.min(100, value))}%`
  return (
    <div>
      <div className="text-xs flex items-center justify-between"><span className="opacity-70">{label}</span><span className="font-medium">{value}</span></div>
      <div className="h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-800 overflow-hidden">
        <div className={`h-2 ${color} transition-all duration-500`} style={{ width: w }} />
      </div>
    </div>
  )
}
