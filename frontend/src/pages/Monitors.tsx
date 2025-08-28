import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { toast } from 'sonner'
import { Timer, Brain, BarChart3 } from 'lucide-react'

const API = '/api'

const CRON_PRESETS = [
  { label: 'Diário 02:00', cron: '0 2 * * *', description: 'Executa todos os dias às 2h da manhã' },
  { label: 'Dias úteis 06:00', cron: '0 6 * * 1-5', description: 'Executa de segunda a sexta às 6h da manhã' },
  { label: 'Semanal (domingo 03:00)', cron: '0 3 * * 0', description: 'Executa todo domingo às 3h da manhã' },
]

type EnginePreset = { name: string; region: string; device: 'desktop' | 'mobile'; config_json: Record<string, any>; label: string }
const ENGINE_PRESETS: EnginePreset[] = [
  { name: 'gemini', region: 'BR', device: 'desktop', config_json: { model: 'gemini-2.5-pro' }, label: 'Gemini 2.5 Pro (Desktop)' },
  { name: 'gemini', region: 'BR', device: 'mobile', config_json: { model: 'gemini-2.5-pro' }, label: 'Gemini 2.5 Pro (Mobile)' },
  { name: 'gemini', region: 'BR', device: 'desktop', config_json: { model: 'gemini-2.5-flash' }, label: 'Gemini 2.5 Flash (Desktop)' },
  { name: 'gemini', region: 'BR', device: 'mobile', config_json: { model: 'gemini-2.5-flash' }, label: 'Gemini 2.5 Flash (Mobile)' },
  { name: 'openai', region: 'BR', device: 'desktop', config_json: { model: 'gpt-4o' }, label: 'GPT-4o (Desktop)' },
  { name: 'openai', region: 'BR', device: 'mobile', config_json: { model: 'gpt-4o' }, label: 'GPT-4o (Mobile)' },
  { name: 'openai', region: 'BR', device: 'desktop', config_json: { model: 'gpt-4o-mini' }, label: 'GPT-4o mini (Desktop)' },
  { name: 'openai', region: 'BR', device: 'mobile', config_json: { model: 'gpt-4o-mini' }, label: 'GPT-4o mini (Mobile)' },
  { name: 'openai', region: 'BR', device: 'desktop', config_json: { model: 'o5' }, label: 'OpenAI o5 (Desktop)' },
  { name: 'openai', region: 'BR', device: 'mobile', config_json: { model: 'o5' }, label: 'OpenAI o5 (Mobile)' },
  { name: 'openai', region: 'BR', device: 'desktop', config_json: { model: 'o5-mini' }, label: 'OpenAI o5-mini (Desktop)' },
  { name: 'openai', region: 'BR', device: 'mobile', config_json: { model: 'o5-mini' }, label: 'OpenAI o5-mini (Mobile)' },
  { name: 'perplexity', region: 'BR', device: 'desktop', config_json: { model: 'llama-3.1-sonar-huge-128k-online' }, label: 'Perplexity Sonar (Desktop)' },
]

type Monitor = { id: string; name: string; subproject_id?: string; schedule_cron?: string; engines_json: any; active: boolean }

type Template = { id: string; category: string; name: string; subproject_id?: string }

type MonitorTemplateLink = { id: string; template_id: string }

type Subproject = { id: string; name: string }

type Project = { id: string; name: string }

type MonitorRun = { id: string; status: string; started_at?: string; finished_at?: string; zcrs?: number | null }
async function getMonitorRuns(monitorId: string): Promise<MonitorRun[]> {
  const res = await axios.get<MonitorRun[]>(`${API}/monitors/${monitorId}/runs`)
  return res.data
}

export default function MonitorsPage() {
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [projects, setProjects] = useState<Project[]>([])
  const [items, setItems] = useState<Monitor[]>([])
  const [name, setName] = useState('')
  const [selectedCronPreset, setSelectedCronPreset] = useState('')
  const [customCron, setCustomCron] = useState('')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState('')
  const [selectedEngines, setSelectedEngines] = useState<number[]>([0]) // Default to first engine
  const [templates, setTemplates] = useState<Template[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [running, setRunning] = useState<Record<string, boolean>>({})
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [linkSelect, setLinkSelect] = useState<Record<string, string>>({})
  const [templatesRefresh, setTemplatesRefresh] = useState<Record<string, number>>({})
  const [categorySelect, setCategorySelect] = useState<Record<string, string>>({})
  const [cleanMode, setCleanMode] = useState<boolean>(true)
  const [showCreate, setShowCreate] = useState<boolean>(false)
  const [monitorFilter, setMonitorFilter] = useState<'all' | 'running' | 'active' | 'inactive'>('all')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [linkPanelOpen, setLinkPanelOpen] = useState<Record<string, boolean>>({})
  const [showAdvancedLink, setShowAdvancedLink] = useState<Record<string, boolean>>({})
  const [linking, setLinking] = useState<Record<string, boolean>>({})
  const [batchLinking, setBatchLinking] = useState<Record<string, boolean>>({})

  const loadProjects = async () => {
    try {
      const res = await axios.get(`${API}/projects`)
      setProjects(res.data)
      if (res.data.length > 0 && !projectId) {
        const firstProject = res.data[0].id
        setProjectId(firstProject)
        localStorage.setItem('project_id', firstProject)
      }
    } catch (error) {
      console.error('Error loading projects:', error)
    }
  }

  const refresh = async () => {
    if (!projectId) return
    const res = await axios.get<Monitor[]>(`${API}/projects/${projectId}/monitors`)
    setItems(res.data)
    axios.get<Subproject[]>(`${API}/projects/${projectId}/subprojects`).then((r: { data: Subproject[] }) => setSubprojects(r.data))
    axios.get<Template[]>(`${API}/projects/${projectId}/templates`).then((r: { data: Template[] }) => setTemplates(r.data))

    // Update busy map for each monitor based on latest runs
    res.data.forEach((m: Monitor) => updateBusy(m.id))
  }
  
  useEffect(() => { loadProjects() }, [])
  useEffect(() => { refresh() }, [projectId])

  const updateBusy = async (monitorId: string) => {
    try {
      const runs = await getMonitorRuns(monitorId)
      const hasActive = runs.some((r) => ['queued', 'running'].includes(String(r.status).toLowerCase()))
      setBusy((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: hasActive }))
    } catch (e) {
      // ignore
    }
  }

  const pollBusyUntilIdle = (monitorId: string, intervalMs = 5000) => {
    let cleared = false
    const h = setInterval(async () => {
      // compute based on fresh fetch to avoid stale state
      try {
        const runs = await getMonitorRuns(monitorId)
        const hasActive = runs.some((r) => ['queued', 'running'].includes(String(r.status).toLowerCase()))
        setBusy((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: hasActive }))
        if (!hasActive) {
          clearInterval(h)
          cleared = true
        }
      } catch {
        // ignore errors during polling
      }
    }, intervalMs)
    // Safety stop after 10 minutes
    setTimeout(() => { if (!cleared) clearInterval(h) }, 10 * 60 * 1000)
  }

  const create = async () => {
    if (!projectId) { toast.error('Selecione um projeto para continuar'); return }
    const finalCron = selectedCronPreset || customCron || null
    const finalEngines = selectedEngines.map((index: number) => ENGINE_PRESETS[index])

    setIsCreating(true)
    try {
      await axios.post(`${API}/projects/${projectId}/monitors`, {
        name,
        subproject_id: subprojectId || null,
        schedule_cron: finalCron,
        engines_json: { engines: finalEngines },
      })
      setName(''); setSelectedCronPreset(''); setCustomCron(''); setSelectedEngines([0])
      await refresh()
      toast.success('Monitor criado com sucesso')
    } catch (error) {
      console.error('Erro ao criar monitor:', error)
      toast.error('Falha ao criar monitor')
    } finally {
      setIsCreating(false)
    }
  }

  const resetForm = () => {
    setName('')
    setSelectedCronPreset('')
    setCustomCron('')
    setSelectedEngines([0])
    setSubprojectId('')
  }

  const toggleEngine = (index: number) => {
    setSelectedEngines((prev: number[]) => 
      prev.includes(index) 
        ? prev.filter((i) => i !== index)
        : [...prev, index]
    )
  }

  const attachTemplate = async (monitorId: string, templateId: string) => {
    setLinking((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: true }))
    try {
      await axios.post(`${API}/monitors/${monitorId}/templates/${templateId}`)
      await refresh()
      toast.success('Template vinculado com sucesso')
      setLinkSelect((prev: Record<string, string>) => ({ ...prev, [monitorId]: '' }))
      setTemplatesRefresh((prev: Record<string, number>) => ({ ...prev, [monitorId]: (prev[monitorId] || 0) + 1 }))
      setLinkPanelOpen((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: false }))
    } catch (e) {
      toast.error('Falha ao vincular template')
    } finally {
      setLinking((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: false }))
    }
  }

  const attachAllInCategory = async (monitorId: string, category: string, subId?: string) => {
    if (!category) return
    setBatchLinking((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: true }))
    try {
      // Buscar já vinculados para evitar duplicação
      const linksRes = await axios.get<MonitorTemplateLink[]>(`${API}/monitors/${monitorId}/templates`)
      const already = new Set((linksRes.data || []).map((l: MonitorTemplateLink) => l.template_id))
      const pool = templates.filter((t: Template) => t.category === category && (!subId || t.subproject_id === subId))
      const toLink = pool.filter((t: Template) => !already.has(t.id))
      if (!toLink.length) {
        toast.info('Nenhum template novo para vincular nessa categoria')
        return
      }
      await Promise.all(toLink.map((t: Template) => axios.post(`${API}/monitors/${monitorId}/templates/${t.id}`)))
      toast.success(`Vinculados ${toLink.length} templates da categoria "${category}"`)
      setTemplatesRefresh((prev: Record<string, number>) => ({ ...prev, [monitorId]: (prev[monitorId] || 0) + 1 }))
      setCategorySelect((prev: Record<string, string>) => ({ ...prev, [monitorId]: '' }))
      setLinkPanelOpen((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: false }))
    } catch (e) {
      toast.error('Falha ao vincular todos da categoria')
    } finally {
      setBatchLinking((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: false }))
    }
  }

  const runNow = async (monitorId: string) => {
    setRunning((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: true }))
    setBusy((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: true }))
    try {
      const res = await axios.post(`${API}/monitors/${monitorId}/run`)
      toast.success(`Runs enfileiradas: ${res.data.queued_runs.length}`)
      // Start polling to re-enable when finished
      pollBusyUntilIdle(monitorId)
    } catch (error) {
      console.error('Erro ao enfileirar execução:', error)
      toast.error('Falha ao enfileirar execução')
    } finally {
      setRunning((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: false }))
    }
  }

  const removeTemplate = async (monitorId: string, templateId: string) => {
    try {
      await axios.delete(`${API}/monitors/${monitorId}/templates/${templateId}`)
      toast.success('Template desvinculado')
      setTemplatesRefresh((prev: Record<string, number>) => ({ ...prev, [monitorId]: (prev[monitorId] || 0) + 1 }))
    } catch (e) {
      toast.error('Falha ao desvincular template')
    }
  }

  const itemsToRender = items.filter((m: Monitor) => {
    if (monitorFilter === 'running') return !!busy[m.id]
    if (monitorFilter === 'active') return !!m.active
    if (monitorFilter === 'inactive') return !m.active
    return true
  })

  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold">Monitores</h1>
      <div className="rounded-md border bg-neutral-50 dark:bg-neutral-900 p-3">
        <p className="text-sm text-neutral-700 dark:text-neutral-300">
          Automatize a execução dos seus templates de SEO. Selecione um projeto, defina o agendamento (ou use um preset) e escolha as engines de IA. Você pode executar manualmente a qualquer momento e acompanhar o histórico de runs abaixo.
        </p>
        <div className="mt-2 grid grid-cols-1 gap-2 text-xs text-neutral-600 dark:text-neutral-400 sm:grid-cols-3">
          <div className="flex items-center gap-2"><Timer className="h-4 w-4" /><span>Presets prontos ou CRON personalizado</span></div>
          <div className="flex items-center gap-2"><Brain className="h-4 w-4" /><span>Engines em BR por padrão</span></div>
          <div className="flex items-center gap-2"><BarChart3 className="h-4 w-4" /><span>Histórico de execuções e status</span></div>
        </div>
      </div>
      <div className="flex gap-2 items-center">
        <Select value={projectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value) }}>
          <option value="">Selecione um projeto</option>
          {projects.map((p: Project) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </Select>
        {!projectId && <div className="text-sm text-red-500">Selecione um projeto para continuar</div>}
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <Select value={monitorFilter} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setMonitorFilter(e.target.value as any)}>
          <option value="all">Todos</option>
          <option value="running">Rodando</option>
          <option value="active">Ativos</option>
          <option value="inactive">Inativos</option>
        </Select>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={cleanMode} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCleanMode(e.target.checked)} />
          Modo clean
        </label>
        {cleanMode && !showCreate && (
          <Button size="sm" onClick={() => setShowCreate(true)}>Novo monitor</Button>
        )}
      </div>

      {(!cleanMode || showCreate) && (
      <div className="border rounded-md p-4 space-y-4">
        <div className="text-lg font-medium">Criar Monitor</div>
        
        <div className="space-y-2">
          <label className="text-sm font-medium">Nome do Monitor</label>
          <Input placeholder="Ex: Monitor SEO Diário" value={name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)} />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Tema (Subprojeto)</label>
          <Select value={subprojectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSubprojectId(e.target.value)}>
            <option value="">(Sem tema específico)</option>
            {subprojects.map((sp: Subproject) => <option key={sp.id} value={sp.id}>{sp.name}</option>)}
          </Select>
        </div>

        <section className="border rounded-md p-4 space-y-3">
          <div>
            <div className="text-sm font-medium">Agendamento</div>
            <div className="text-xs opacity-70">Escolha um preset recomendado ou informe uma expressão CRON.</div>
            <div className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
              Selecionado: {selectedCronPreset
                ? `${CRON_PRESETS.find(p => p.cron === selectedCronPreset)?.label} (${selectedCronPreset})`
                : (customCron ? `Personalizado: ${customCron}` : '—')}
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {CRON_PRESETS.map((preset: { label: string; cron: string; description: string }, index: number) => (
              <label
                key={index}
                className={`flex items-start gap-3 p-3 border rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-900 cursor-pointer ${selectedCronPreset === preset.cron ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-neutral-800' : ''}`}
              >
                <input
                  type="radio"
                  name="cronPreset"
                  value={preset.cron}
                  checked={selectedCronPreset === preset.cron}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setSelectedCronPreset(e.target.value); setCustomCron('') }}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <div className="font-medium text-sm">{preset.label}</div>
                  <div className="text-xs opacity-70">{preset.description}</div>
                  <div className="text-xs font-mono opacity-50">{preset.cron}</div>
                </div>
              </label>
            ))}
            <label
              className={`flex items-center gap-3 p-3 border rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-900 cursor-pointer ${customCron ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-neutral-800' : ''}`}
            >
              <input
                type="radio"
                name="cronPreset"
                value="custom"
                checked={!!customCron}
                onChange={() => { setSelectedCronPreset(''); }}
              />
              <div className="flex-1 space-y-2">
                <div className="font-medium text-sm">Personalizado</div>
                <Input
                  placeholder="Ex: 0 8 * * 1-5 (seg-sex 8h)"
                  value={customCron}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => { setCustomCron(e.target.value); setSelectedCronPreset('') }}
                  className="text-xs font-mono"
                />
              </div>
            </label>
          </div>
        </section>

        <section className="border rounded-md p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Engines de IA</div>
              <div className="text-xs opacity-70">Selecione uma ou mais engines (região BR por padrão).</div>
              <div className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">Selecionadas: {selectedEngines.length}/{ENGINE_PRESETS.length}</div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedEngines(ENGINE_PRESETS.map((_, i) => i))}
              >Selecionar todas</Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedEngines([])}
              >Limpar</Button>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {ENGINE_PRESETS.map((engine: EnginePreset, index: number) => {
              const isSelected = selectedEngines.includes(index)
              return (
                <label
                  key={index}
                  className={`flex items-center gap-3 p-3 border rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-900 cursor-pointer ${isSelected ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-neutral-800' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleEngine(index)}
                  />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{engine.label}</div>
                    <div className="text-xs opacity-70">{engine.name} • {engine.region} • {engine.device}</div>
                  </div>
                </label>
              )
            })}
          </div>
        </section>

        <div className="flex justify-end pt-2 gap-2">
          <Button variant="outline" onClick={resetForm} disabled={isCreating}>Cancelar</Button>
          <Button onClick={create} disabled={isCreating || !name || selectedEngines.length === 0}>
            {isCreating ? 'Criando…' : 'Criar Monitor'}
          </Button>
          {cleanMode && (
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Fechar</Button>
          )}
        </div>
      </div>
      )}

      <div className="grid gap-3">
        {itemsToRender.map((m: Monitor) => (
          <div key={m.id} className="border rounded-md p-3 space-y-2">
            <div className="flex items-center gap-2">
              <strong className="flex-1">{m.name}</strong>
              <span className={`text-xs px-2 py-0.5 rounded-full ${busy[m.id] ? 'bg-yellow-100 text-yellow-800' : (m.active ? 'bg-green-100 text-green-800' : 'bg-neutral-200 text-neutral-700')}`}>
                {busy[m.id] ? 'Rodando' : (m.active ? 'Ativo' : 'Inativo')}
              </span>
              <Button variant="secondary" onClick={() => runNow(m.id)} disabled={!!running[m.id] || !!busy[m.id]}>
                {running[m.id] ? 'Executando…' : busy[m.id] ? 'Em execução…' : 'Executar agora'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setExpanded((prev: Record<string, boolean>) => ({ ...prev, [m.id]: !prev[m.id] }))}>
                {expanded[m.id] ? 'Recolher' : 'Detalhes'}
              </Button>
            </div>
            {!cleanMode && <div className="text-xs opacity-70">Tema: {m.subproject_id || '—'} | Engines: {JSON.stringify(m.engines_json.engines)}</div>}

            {(!cleanMode || expanded[m.id]) && (
            <>
            <div className="grid gap-1">
              <div className="text-sm opacity-70">Templates vinculados</div>
              <MonitorTemplates
                monitorId={m.id}
                subprojectId={m.subproject_id}
                allTemplates={templates}
                refreshToken={templatesRefresh[m.id] || 0}
                onRemove={async (tplId: string) => removeTemplate(m.id, tplId)}
              />
            </div>
            <div className="grid gap-1">
              <div className="flex items-center justify-between">
                <div className="text-sm opacity-70">Vincular template</div>
                {!linkPanelOpen[m.id] ? (
                  <Button size="sm" variant="outline" onClick={() => setLinkPanelOpen((prev: Record<string, boolean>) => ({ ...prev, [m.id]: true }))}>Abrir</Button>
                ) : (
                  <Button size="sm" variant="ghost" onClick={() => setLinkPanelOpen((prev: Record<string, boolean>) => ({ ...prev, [m.id]: false }))}>Fechar</Button>
                )}
              </div>
              {linkPanelOpen[m.id] && (
              <div className="flex flex-wrap items-center gap-2">
                <Select
                  value={linkSelect[m.id] || ''}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLinkSelect((prev: Record<string, string>) => ({ ...prev, [m.id]: e.target.value }))}
                  disabled={!!linking[m.id] || !!batchLinking[m.id]}
                >
                  <option value="">Selecione um template…</option>
                  {templates
                    .filter((t: Template) => !m.subproject_id || t.subproject_id === m.subproject_id)
                    .map((t: Template) => (
                    <option key={t.id} value={t.id}>{t.category} • {t.name}</option>
                  ))}
                </Select>
                <Button
                  size="sm"
                  onClick={() => linkSelect[m.id] && attachTemplate(m.id, linkSelect[m.id])}
                  disabled={!!linking[m.id] || !linkSelect[m.id]}
                >
                  {linking[m.id] ? 'Vinculando…' : 'Vincular'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowAdvancedLink((prev: Record<string, boolean>) => ({ ...prev, [m.id]: !prev[m.id] }))}>
                  {showAdvancedLink[m.id] ? 'Ocultar avançado' : 'Avançado'}
                </Button>
                {showAdvancedLink[m.id] && (
                  <>
                    <span className="text-xs opacity-60">•</span>
                    <Select
                      value={categorySelect[m.id] || ''}
                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setCategorySelect((prev: Record<string, string>) => ({ ...prev, [m.id]: e.target.value }))}
                      disabled={!!batchLinking[m.id] || !!linking[m.id]}
                    >
                      <option value="">Categoria…</option>
                      {Array.from(new Set<string>(templates
                        .filter((t: Template) => !m.subproject_id || t.subproject_id === m.subproject_id)
                        .map((t: Template) => t.category)
                      ))
                        .sort()
                        .map((cat: string) => (
                          <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </Select>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => categorySelect[m.id] && attachAllInCategory(m.id, categorySelect[m.id], m.subproject_id)}
                      disabled={!!batchLinking[m.id] || !categorySelect[m.id]}
                    >
                      {batchLinking[m.id] ? 'Vinculando…' : 'Vincular todos da categoria'}
                    </Button>
                  </>
                )}
                {linkSelect[m.id] && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setLinkSelect((prev: Record<string, string>) => ({ ...prev, [m.id]: '' }))}
                  >
                    Cancelar
                  </Button>
                )}
              </div>
              )}
            </div>
            <div className="grid gap-1">
              <div className="text-sm opacity-70">Histórico</div>
              <MonitorRuns monitorId={m.id} />
            </div>
            <div className="flex items-center gap-2">
              <Select value={m.schedule_cron || ''} onChange={async (e: React.ChangeEvent<HTMLSelectElement>)=>{ await axios.patch(`${API}/monitors/${m.id}`, { schedule_cron: e.target.value || null }); await refresh() }}>
                <option value="">(sem agendamento)</option>
                {CRON_PRESETS.map(p => <option key={p.cron} value={p.cron}>{p.label}</option>)}
              </Select>
              <label className="flex items-center gap-1 text-xs">
                <input type="checkbox" defaultChecked={m.active} onChange={async (e: React.ChangeEvent<HTMLInputElement>)=>{ await axios.patch(`${API}/monitors/${m.id}`, { active: e.target.checked }); await refresh() }} /> ativo
              </label>
            </div>
            </>
            )}
          </div>
        ))}
        {!items.length && <div className="text-sm opacity-70">Nenhum monitor.</div>}
      </div>
    </div>
  )
}

function MonitorTemplates(
  {
    monitorId,
    subprojectId,
    allTemplates,
    refreshToken,
    onRemove,
  }: {
    monitorId: string
    subprojectId?: string
    allTemplates: Template[]
    refreshToken: number
    onRemove: (templateId: string) => Promise<void>
  }
) {
  const [linked, setLinked] = useState<MonitorTemplateLink[]>([])
  const [removing, setRemoving] = useState<Record<string, boolean>>({})

  useEffect(() => {
    let cancelled = false
    axios
      .get<MonitorTemplateLink[]>(`${API}/monitors/${monitorId}/templates`)
      .then((res: { data: MonitorTemplateLink[] }) => { if (!cancelled) setLinked(res.data) })
      .catch(() => { /* noop */ })
    return () => { cancelled = true }
  }, [monitorId, refreshToken])

  // Resolver para objetos Template completos, usando a lista recebida por props
  const resolved: Template[] = linked
    .map((l: MonitorTemplateLink) => allTemplates.find((t: Template) => t.id === l.template_id))
    .filter((t: Template | undefined): t is Template => Boolean(t))

  const filtered = resolved.filter((t: Template) => !subprojectId || t.subproject_id === subprojectId)

  if (!filtered.length) {
    return <div className="text-xs opacity-60">Nenhum template vinculado.</div>
  }

  return (
    <div className="flex flex-wrap gap-2">
      {filtered.map((t: Template) => (
        <span key={t.id} className="inline-flex items-center gap-2 text-xs border rounded-full px-2 py-0.5 bg-neutral-50 dark:bg-neutral-900">
          <span className="opacity-80">{t.category} • {t.name}</span>
          <button
            className="text-red-600 hover:underline"
            onClick={async () => {
              if (removing[t.id]) return
              setRemoving((prev: Record<string, boolean>) => ({ ...prev, [t.id]: true }))
              try {
                await onRemove(t.id)
              } finally {
                setRemoving((prev: Record<string, boolean>) => ({ ...prev, [t.id]: false }))
              }
            }}
            disabled={!!removing[t.id]}
            title="Remover"
          >{removing[t.id] ? 'Removendo…' : '×'}</button>
        </span>
      ))}
    </div>
  )
}

function MonitorRuns({ monitorId }: { monitorId: string }) {
  const [runs, setRuns] = useState<MonitorRun[]>([])
  useEffect(() => { getMonitorRuns(monitorId).then(setRuns) }, [monitorId])
  const formatDate = (d?: string) => (d ? new Date(d).toLocaleString() : '-')
  return (
    <div className="overflow-auto text-xs">
      <table className="min-w-full">
        <thead><tr><th className="text-left p-1">Run</th><th className="text-left p-1">Status</th><th className="text-left p-1">Início</th><th className="text-left p-1">Fim</th><th className="text-left p-1">ZCRS</th></tr></thead>
        <tbody>
          {runs.map((r: MonitorRun) => (
            <tr key={r.id} className="border-t border-neutral-800">
              <td className="p-1"><a className="text-blue-600" href={`/runs/${r.id}`}>{r.id}</a></td>
              <td className="p-1">{r.status}</td>
              <td className="p-1">{formatDate(r.started_at)}</td>
              <td className="p-1">{formatDate(r.finished_at)}</td>
              <td className="p-1">{r.zcrs ?? '-'}</td>
            </tr>
          ))}
          {!runs.length && <tr><td className="p-1" colSpan={5}>Sem runs.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
