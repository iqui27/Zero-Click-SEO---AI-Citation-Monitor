import React, { useEffect, useMemo, useState } from 'react'
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
  { name: 'perplexity', region: 'BR', device: 'desktop', config_json: { model: 'sonar-pro' }, label: 'Perplexity Sonar (Desktop)' },
  { name: 'google_serp', region: 'BR', device: 'desktop', config_json: { use_serpapi: true, serpapi_ai_overview: true, serpapi_no_cache: false }, label: 'Google SERP (AI Overview via SerpAPI)' },
  { name: 'google_serp', region: 'BR', device: 'desktop', config_json: { use_serpapi: true, serpapi_ai_mode: true, serpapi_no_cache: false }, label: 'Google AI Mode (SerpAPI)' },
]

type Monitor = {
  id: string
  name: string
  subproject_id?: string
  schedule_cron?: string
  engines_json: any
  active: boolean
  schedule_info?: {
    tz: string
    tz_label: string
    next_run_br?: string | null
    next_runs_br?: string[]
    until?: string | null
    daily_slots_br?: string[]
    next_index_today?: number | null
    total_today?: number | null
  } | null
}

type Template = { id: string; category: string; name: string; subproject_id?: string }

type MonitorTemplateLink = { id: string; template_id: string }

type Subproject = { id: string; name: string }

type Project = { id: string; name: string }

type MonitorRun = { id: string; status: string; started_at?: string; finished_at?: string; zcrs?: number | null; engine?: string | null; cycles_total?: number | null; cost_usd?: number | null; prompt_id?: string | null; prompt_name?: string | null; schedule_date?: string | null; schedule_slot?: string | null; schedule_source?: 'monitor'|'monitor_now'|'manual'|string }

type MonitorHistoryItem = {
  monitor_id: string
  project_id: string
  subproject_id?: string | null
  name: string
  status: 'active' | 'deleted'
  runs_total: number
  runs_completed: number
  runs_failed: number
  deleted_at?: string | null
  inferred?: boolean
}

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
  const [deleting, setDeleting] = useState<Record<string, boolean>>({})
  const [stopping, setStopping] = useState<Record<string, boolean>>({})
  const [clearing, setClearing] = useState<Record<string, boolean>>({})
  const [stats, setStats] = useState<Record<string, { totals: { total: number; completed: number; failed: number }, by_day: Array<{ date: string; total: number; completed: number; failed: number }> }>>({})
  // Advanced schedule (Create)
  const [useAdvancedSchedule, setUseAdvancedSchedule] = useState<boolean>(false)
  const [timesPerDay, setTimesPerDay] = useState<number>(1)
  const [timeInputs, setTimeInputs] = useState<string[]>(['08:00'])
  const [durationType, setDurationType] = useState<'none'|'7d'|'10d'|'30d'|'custom'>('none')
  const [customUntil, setCustomUntil] = useState<string>('')
  // Advanced schedule (Per monitor editor)
  const [advOpen, setAdvOpen] = useState<Record<string, boolean>>({})
  const [advTimes, setAdvTimes] = useState<Record<string, string[]>>({})
  const [advCount, setAdvCount] = useState<Record<string, number>>({})
  const [advDuration, setAdvDuration] = useState<Record<string, 'none'|'7d'|'10d'|'30d'|'custom'>>({})
  const [advCustomUntil, setAdvCustomUntil] = useState<Record<string, string>>({})

  // History for export FULL (ativos / deletados / pré-snapshot)
  const [history, setHistory] = useState<MonitorHistoryItem[]>([])
  const [exportType, setExportType] = useState<'active'|'deleted'|'inferred'>('active')
  const [exportMonitorId, setExportMonitorId] = useState<string>('')

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get<MonitorHistoryItem[]>(`${API}/monitors/history`)
        setHistory(res.data || [])
      } catch (e) {
        // noop
      }
    }
    load()
  }, [projectId])

  const exportOptions = useMemo(() => {
    return (history || []).filter((h: MonitorHistoryItem) => {
      if (exportType === 'active') return h.status === 'active'
      if (exportType === 'deleted') return h.status === 'deleted' && !h.inferred
      return !!h.inferred
    })
  }, [history, exportType])

  useEffect(() => {
    // reset selected when type or options change
    if (!exportMonitorId || !exportOptions.find(o => o.monitor_id === exportMonitorId)) {
      setExportMonitorId(exportOptions[0]?.monitor_id || '')
    }
  }, [exportType, history])

  const downloadFullExport = () => {
    const sel = exportOptions.find(o => o.monitor_id === exportMonitorId)
    if (!sel) return
    if (exportType === 'active') {
      window.open(`${API}/monitors/${sel.monitor_id}/export_full.csv`, '_blank')
    } else if (exportType === 'deleted' && !sel.inferred) {
      window.open(`${API}/monitors/history/${sel.monitor_id}/export_full.csv`, '_blank')
    } else {
      const params = new URLSearchParams({ project_id: sel.project_id })
      if (sel.subproject_id) params.append('subproject_id', sel.subproject_id)
      window.open(`${API}/monitors/history/inferred_export_full.csv?${params.toString()}`, '_blank')
    }
  }

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

  const stopMonitor = async (monitorId: string) => {
    if (!window.confirm('Parar monitor agora? Runs em fila serão canceladas e o monitor ficará inativo.')) return
    setStopping((prev) => ({ ...prev, [monitorId]: true }))
    try {
      await axios.post(`${API}/monitors/${monitorId}/stop`, {})
      toast.success('Monitor parado')
      await refresh()
    } catch (e) {
      toast.error('Falha ao parar monitor')
    } finally {
      setStopping((prev) => ({ ...prev, [monitorId]: false }))
    }
  }

  const clearMonitorRuns = async (monitorId: string) => {
    if (!window.confirm('Apagar TODAS as runs deste monitor? Esta ação é irreversível.')) return
    setClearing((prev) => ({ ...prev, [monitorId]: true }))
    try {
      const r = await axios.delete(`${API}/monitors/${monitorId}/runs`)
      const n = (r.data?.deleted ?? 0)
      toast.success(`Apagadas ${n} runs`)
      await refresh()
    } catch (e) {
      toast.error('Falha ao apagar runs do monitor')
    } finally {
      setClearing((prev) => ({ ...prev, [monitorId]: false }))
    }
  }

  const deleteMonitor = async (monitorId: string) => {
    if (!window.confirm('Tem certeza que deseja apagar este monitor?\nAs runs antigas continuarão no histórico.')) return
    setDeleting(prev => ({ ...prev, [monitorId]: true }))
    try {
      await axios.delete(`${API}/monitors/${monitorId}`)
      toast.success('Monitor apagado')
      await refresh()
    } catch (e) {
      toast.error('Falha ao apagar monitor')
    } finally {
      setDeleting(prev => ({ ...prev, [monitorId]: false }))
    }
  }

  // Helper: vincular todos os templates restantes ao monitor
  const attachAllTemplates = async (monitorId: string, subId?: string) => {
    setBatchLinking((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: true }))
    try {
      const linksRes = await axios.get<MonitorTemplateLink[]>(`${API}/monitors/${monitorId}/templates`)
      const already = new Set((linksRes.data || []).map((l: MonitorTemplateLink) => l.template_id))
      const pool = templates.filter((t: Template) => (!subId || t.subproject_id === subId))
      const toLink = pool.filter((t: Template) => !already.has(t.id))
      if (!toLink.length) { toast.info('Nenhum template novo para vincular'); return }
      await Promise.all(toLink.map((t: Template) => axios.post(`${API}/monitors/${monitorId}/templates/${t.id}`)))
      toast.success(`Vinculados ${toLink.length} templates`)
      setTemplatesRefresh((prev: Record<string, number>) => ({ ...prev, [monitorId]: (prev[monitorId] || 0) + 1 }))
      setLinkPanelOpen((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: false }))
    } catch (e) {
      toast.error('Falha ao vincular todos os templates')
    } finally {
      setBatchLinking((prev: Record<string, boolean>) => ({ ...prev, [monitorId]: false }))
    }
  }

  // Helper: montar schedule com vários horários por dia e período
  // Conversão: entradas de horário são no fuso UTC-3 (Brasília). Convertê-las para UTC ao montar CRON.
  function _brTimeToUtcHour(h: number): number { return (h + 3) % 24 }
  function _shiftHourFieldToUTC(field: string): string {
    const f = (field || '').trim()
    if (!f || f === '*') return f
    // Suporte a lista de horas "6,12,18" e número simples "6". Outros padrões permanecem como estão.
    if (/^\d{1,2}$/.test(f)) {
      const h = parseInt(f, 10)
      if (!Number.isNaN(h)) return String(_brTimeToUtcHour(h))
      return f
    }
    if (/^\d{1,2}(,\d{1,2})+$/.test(f)) {
      const parts = f.split(',').map(x => parseInt(x, 10)).filter(x => !Number.isNaN(x))
      return parts.map(_brTimeToUtcHour).map(x => String(x)).join(',')
    }
    // range/step complexos não convertidos automaticamente
    return f
  }
  function _convertCronExprLocalBRtoUTC(expr: string): string {
    const parts = (expr || '').trim().split(/\s+/)
    if (parts.length < 2) return expr
    const mm = parts[0]
    const hh = _shiftHourFieldToUTC(parts[1])
    const rest = parts.slice(2).join(' ')
    return [mm, hh, rest].filter(Boolean).join(' ').trim()
  }
  function _convertScheduleLocalBRtoUTC(schedule: string | null): string | null {
    if (!schedule) return null
    // tratar sufixo "; until=YYYY-MM-DD" e expressões separadas por "|"
    const [cronPart, ...opts] = schedule.split(';')
    const exprs = cronPart.split('|').map(s => s.trim()).filter(Boolean)
    const converted = exprs.map(_convertCronExprLocalBRtoUTC).join(' | ')
    const suffix = opts.length ? ('; ' + opts.join(';').trim()) : ''
    return (converted + (suffix ? ' ' + suffix : '')).trim()
  }
  function buildScheduleFromTimes(times: string[], dur: 'none'|'7d'|'10d'|'30d'|'custom', custom: string): string | null {
    const normalized = (times || []).map(t => (t || '').trim()).filter(Boolean)
    if (!normalized.length) return null
    const exprs = normalized.map((t) => {
      const [hh, mm] = t.split(':')
      const h = parseInt(hh || '0', 10)
      const m = parseInt(mm || '0', 10)
      if (Number.isNaN(h) || Number.isNaN(m)) return ''
      const hUTC = _brTimeToUtcHour(h)
      return `${m} ${hUTC} * * *`
    }).filter(Boolean)
    if (!exprs.length) return null
    let out = exprs.join(' | ')
    let until: string | null = null
    if (dur === '7d' || dur === '10d' || dur === '30d') {
      const add = dur === '7d' ? 7 : dur === '10d' ? 10 : 30
      const d = new Date()
      d.setDate(d.getDate() + add)
      // Use date part in UTC
      until = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())).toISOString().slice(0,10)
    } else if (dur === 'custom' && custom) {
      until = custom
    }
    if (until) out += `; until=${until}`
    return out
  }

  // Helper: garantir quantidade de inputs de horário
  function ensureTimeInputs(n: number) {
    setTimesPerDay(n)
    setTimeInputs((prev: string[]) => {
      const arr = [...prev]
      while (arr.length < n) arr.push('08:00')
      if (arr.length > n) arr.length = n
      return arr
    })
  }

  const refresh = async () => {
    if (!projectId) return
    const res = await axios.get<Monitor[]>(`${API}/projects/${projectId}/monitors`)
    setItems(res.data)
    axios.get<Subproject[]>(`${API}/projects/${projectId}/subprojects`).then((r: { data: Subproject[] }) => setSubprojects(r.data))
    axios.get<Template[]>(`${API}/projects/${projectId}/templates`).then((r: { data: Template[] }) => setTemplates(r.data))

    // Update busy map for each monitor based on latest runs
    res.data.forEach((m: Monitor) => updateBusy(m.id))
    // Load stats for each monitor (last 7d)
    res.data.forEach(async (m: Monitor) => {
      try {
        const s = await axios.get(`${API}/monitors/${m.id}/stats`, { params: { days: 7 } })
        setStats((prev: any) => ({ ...prev, [m.id]: s.data }))
      } catch {}
    })
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
    // Montar CRON interpretando entradas como UTC-3 e convertendo para UTC antes de salvar
    const localCron = useAdvancedSchedule ? buildScheduleFromTimes(timeInputs, durationType, customUntil) : (selectedCronPreset || customCron || null)
    const finalCron = _convertScheduleLocalBRtoUTC(localCron)
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
    setUseAdvancedSchedule(false)
    setTimesPerDay(1)
    setTimeInputs(['08:00'])
    setDurationType('none')
    setCustomUntil('')
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
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold tracking-tight">Monitores</h1>
      <div className="rounded-xl border bg-neutral-50/60 dark:bg-neutral-900/60 p-4 shadow-sm backdrop-blur-sm transition-colors">
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
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
            window.open(`${API}/monitors/history.csv${q}`, '_blank')
          }}
          title="Exportar histórico de monitores (inclui monitores apagados)"
        >
          Exportar histórico (CSV)
        </Button>
        {/* Export FULL (runs completas) */}
        <span className="text-sm opacity-60">|</span>
        <Select value={exportType} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setExportType(e.target.value as any)}>
          <option value="active">Ativos</option>
          <option value="deleted">Apagados</option>
          <option value="inferred">Pré-snapshot</option>
        </Select>
        <Select value={exportMonitorId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setExportMonitorId(e.target.value)} disabled={!exportOptions.length}>
          {!exportOptions.length && <option value="">(nenhum)</option>}
          {exportOptions.map((opt: MonitorHistoryItem) => (
            <option key={opt.monitor_id} value={opt.monitor_id}>
              {opt.name} {opt.deleted_at ? '(apagado)' : ''} — {opt.runs_total} runs
            </option>
          ))}
        </Select>
        <Button size="sm" variant="outline" onClick={downloadFullExport} disabled={!exportOptions.length || !exportMonitorId}>Baixar runs (FULL CSV)</Button>
        {cleanMode && !showCreate && (
          <Button size="sm" onClick={() => setShowCreate(true)}>Novo monitor</Button>
        )}
      </div>

      {(!cleanMode || showCreate) && (
      <div className="border rounded-xl p-4 space-y-4 bg-neutral-50/60 dark:bg-neutral-900/60 shadow-sm backdrop-blur-sm transition-colors">
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

        <section className="border rounded-lg p-4 space-y-3">
          <div>
            <div className="text-sm font-medium">Agendamento</div>
            <div className="text-xs opacity-70">Escolha um preset recomendado, informe uma expressão CRON, ou use o modo avançado por horários.</div>
            <div className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
              Selecionado: {useAdvancedSchedule
                ? (buildScheduleFromTimes(timeInputs, durationType, customUntil) || '—')
                : selectedCronPreset
                  ? `${CRON_PRESETS.find(p => p.cron === selectedCronPreset)?.label} (${selectedCronPreset})`
                  : (customCron ? `Personalizado: ${customCron}` : '—')}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={useAdvancedSchedule} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUseAdvancedSchedule(e.target.checked)} />
              Usar modo avançado (várias vezes por dia + duração)
            </label>
          </div>
          {!useAdvancedSchedule && (
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
          )}
          {useAdvancedSchedule && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm">Vezes por dia:</span>
              <Select value={String(timesPerDay)} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => ensureTimeInputs(Number(e.target.value) || 1)}>
                {[1,2,3,4,6].map(n => <option key={n} value={n}>{n}x</option>)}
              </Select>
              <Button size="sm" variant="outline" onClick={() => { ensureTimeInputs(3); setTimeInputs(['08:00','12:00','18:00']) }}>Preset 3x (08:00, 12:00, 18:00)</Button>
              <Button size="sm" variant="outline" onClick={() => { ensureTimeInputs(4); setTimeInputs(['06:00','12:00','18:00','22:00']) }}>Preset 4x (06:00, 12:00, 18:00, 22:00)</Button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
              {timeInputs.slice(0, timesPerDay).map((t, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <label className="text-xs w-24">Horário {idx+1}</label>
                  <Input type="time" value={t} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTimeInputs(prev => prev.map((x, i) => i === idx ? e.target.value : x))} className="h-8 text-xs" />
                </div>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm">Duração:</span>
              <Select value={durationType} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setDurationType(e.target.value as any)}>
                <option value="none">Indefinido</option>
                <option value="7d">1 semana</option>
                <option value="10d">10 dias</option>
                <option value="30d">30 dias</option>
                <option value="custom">Data final…</option>
              </Select>
              {durationType === 'custom' && (
                <Input type="date" value={customUntil} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCustomUntil(e.target.value)} className="h-8 text-xs" />
              )}
            </div>
            <div className="text-xs opacity-70">Expressão salva: <span className="font-mono">{buildScheduleFromTimes(timeInputs, durationType, customUntil) || '—'}</span></div>
          </div>
          )}
        </section>

        <section className="border rounded-lg p-4 space-y-3 bg-neutral-50/60 dark:bg-neutral-900/60 shadow-sm backdrop-blur-sm transition-colors">
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
          <div key={m.id} className="border rounded-xl p-4 space-y-2 bg-neutral-50/60 dark:bg-neutral-900/60 transition-colors shadow-sm hover:shadow-md fade-in-up">
            <div className="flex items-center gap-2">
              <strong className="flex-1">{m.name}</strong>
              <span className={`text-xs px-2 py-0.5 rounded-full ${busy[m.id] ? 'bg-yellow-100 text-yellow-800' : (m.active ? 'bg-green-100 text-green-800' : 'bg-neutral-200 text-neutral-700')}`}>
                {busy[m.id] ? 'Rodando' : (m.active ? 'Ativo' : 'Inativo')}
              </span>
              <Button variant="secondary" onClick={() => runNow(m.id)} disabled={!!running[m.id] || !!busy[m.id]}>
                {running[m.id] ? 'Executando…' : busy[m.id] ? 'Em execução…' : 'Executar agora'}
              </Button>
              {!m.active && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-green-700 border-green-300 dark:border-green-800"
                  onClick={async () => { await axios.patch(`${API}/monitors/${m.id}`, { active: true }); toast.success('Monitor reativado'); await refresh() }}
                >
                  Retomar monitor
                </Button>
              )}
              <Button variant="outline" size="sm" className="text-red-600 border-red-300 dark:border-red-800" onClick={() => stopMonitor(m.id)} disabled={!!stopping[m.id]}>
                {stopping[m.id] ? 'Parando…' : 'Parar monitor'}
              </Button>
              <Button variant="outline" size="sm" onClick={() => clearMonitorRuns(m.id)} disabled={!!clearing[m.id]}>
                {clearing[m.id] ? 'Limpando…' : 'Limpar runs'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(`${API}/monitors/${m.id}/export.csv`, '_blank')}
                title="Baixar CSV com respostas e citações (apenas runs com resposta)"
              >
                Exportar CSV
              </Button>
              <Button variant="ghost" size="sm" onClick={() => deleteMonitor(m.id)} disabled={!!deleting[m.id]} className="text-red-600">
                {deleting[m.id] ? 'Apagando…' : 'Apagar'}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setExpanded((prev: Record<string, boolean>) => ({ ...prev, [m.id]: !prev[m.id] }))}>
                {expanded[m.id] ? 'Recolher' : 'Detalhes'}
              </Button>
            </div>
            {/* Schedule diagnostics (UTC-3 Brasília) */}
            {m.schedule_info && (
              <div className="text-xs flex flex-wrap items-center gap-2 opacity-80">
                <span className="px-2 py-0.5 rounded border">Timezone: <b>{m.schedule_info.tz_label || 'UTC-3'}</b></span>
                <span className="px-2 py-0.5 rounded border">Próxima (UTC-3): <b>{m.schedule_info.next_run_br || '—'}</b></span>
                <span className="px-2 py-0.5 rounded border">Próximas: {(m.schedule_info.next_runs_br || []).join(', ') || '—'}</span>
                {Array.isArray(m.schedule_info.daily_slots_br) && m.schedule_info.daily_slots_br.length > 0 && (
                  <span className="px-2 py-0.5 rounded border">Hoje: {(m.schedule_info.daily_slots_br || []).join(', ')}</span>
                )}
                {(typeof m.schedule_info.next_index_today === 'number') && (
                  <span className="px-2 py-0.5 rounded border">Próximo índice hoje: <b>{m.schedule_info.next_index_today}/{m.schedule_info.total_today || '-'}</b></span>
                )}
                {m.schedule_info.until && <span className="px-2 py-0.5 rounded border">Válido até: <b>{m.schedule_info.until}</b></span>}
                <span className="text-[10px] opacity-60">Horários já convertidos para Brasília (UTC-3)</span>
              </div>
            )}

            {/* Stats summary */}
            {stats[m.id] && (() => {
              const s = stats[m.id]
              const today = new Date().toISOString().slice(0,10)
              const rec = (s.by_day || []).find((d: any) => d.date === today)
              const tTotal = rec?.total || 0
              const tOk = rec?.completed || 0
              const tRate = tTotal > 0 ? Math.round((tOk / tTotal) * 100) : 0
              return (
                <div className="text-xs flex flex-wrap items-center gap-2 opacity-80">
                  <span className="px-2 py-0.5 rounded border">7d total: <b>{s.totals.total}</b></span>
                  <span className="px-2 py-0.5 rounded border text-green-700 dark:text-green-300 border-green-300 dark:border-green-800">ok: <b>{s.totals.completed}</b></span>
                  <span className="px-2 py-0.5 rounded border text-red-700 dark:text-red-300 border-red-300 dark:border-red-800">falhas: <b>{s.totals.failed}</b></span>
                  <span className="px-2 py-0.5 rounded border">hoje: <b>{tTotal}</b></span>
                  <span className="px-2 py-0.5 rounded border">sucesso hoje: <b>{tRate}%</b></span>
                </div>
              )
            })()}
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
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => attachAllTemplates(m.id, m.subproject_id)}
                      disabled={!!batchLinking[m.id]}
                    >
                      {batchLinking[m.id] ? 'Vinculando…' : 'Vincular TODOS os templates'}
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
              <MonitorRuns monitorId={m.id} scheduleInfo={m.schedule_info || undefined} />
            </div>
            <div className="flex items-center gap-2">
              <Select value={m.schedule_cron || ''} onChange={async (e: React.ChangeEvent<HTMLSelectElement>)=>{ await axios.patch(`${API}/monitors/${m.id}`, { schedule_cron: e.target.value || null }); await refresh() }}>
                <option value="">(sem agendamento)</option>
                {CRON_PRESETS.map(p => <option key={p.cron} value={p.cron}>{p.label}</option>)}
              </Select>
              <label className="flex items-center gap-1 text-xs">
                <input type="checkbox" defaultChecked={m.active} onChange={async (e: React.ChangeEvent<HTMLInputElement>)=>{ await axios.patch(`${API}/monitors/${m.id}`, { active: e.target.checked }); await refresh() }} /> ativo
              </label>
              <Button size="sm" variant="outline" onClick={() => setAdvOpen(prev => ({ ...prev, [m.id]: !prev[m.id] }))}>
                {advOpen[m.id] ? 'Fechar agendamento avançado' : 'Agendamento avançado'}
              </Button>
            </div>
            {advOpen[m.id] && (
              <div className="mt-2 border rounded-md p-3 space-y-2">
                {stats[m.id]?.by_day?.length ? (
                  <div className="overflow-auto text-xs">
                    <div className="font-medium mb-1">Execuções por dia (últimos 7d)</div>
                    <table className="min-w-[320px]">
                      <thead>
                        <tr>
                          <th className="text-left p-1">Dia</th>
                          <th className="text-right p-1">Total</th>
                          <th className="text-right p-1">OK</th>
                          <th className="text-right p-1">Falhas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats[m.id].by_day.map((d: any) => (
                          <tr key={d.date} className="border-t border-neutral-800">
                            <td className="p-1">{d.date}</td>
                            <td className="p-1 text-right">{d.total}</td>
                            <td className="p-1 text-right text-green-600">{d.completed}</td>
                            <td className="p-1 text-right text-red-600">{d.failed}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm">Vezes por dia:</span>
                  <Select value={String(advCount[m.id] || 1)} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                    const n = Number(e.target.value) || 1
                    setAdvCount(prev => ({ ...prev, [m.id]: n }))
                    setAdvTimes(prev => {
                      const cur = prev[m.id] || ['08:00']
                      const arr = [...cur]
                      while (arr.length < n) arr.push('08:00')
                      if (arr.length > n) arr.length = n
                      return { ...prev, [m.id]: arr }
                    })
                  }}>
                    {[1,2,3,4,6].map(n => <option key={n} value={n}>{n}x</option>)}
                  </Select>
                  <Button size="sm" variant="outline" onClick={() => setAdvTimes(prev => ({ ...prev, [m.id]: ['08:00','12:00','18:00'] }))}>Preset 3x</Button>
                  <Button size="sm" variant="outline" onClick={() => setAdvTimes(prev => ({ ...prev, [m.id]: ['06:00','12:00','18:00','22:00'] }))}>Preset 4x</Button>
                </div>
                <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
                  {(advTimes[m.id] || ['08:00']).slice(0, advCount[m.id] || 1).map((t, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <label className="text-xs w-24">Horário {idx+1}</label>
                      <input type="time" value={t} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdvTimes(prev => ({ ...prev, [m.id]: (prev[m.id] || ['08:00']).map((x, i) => i === idx ? e.target.value : x) }))} className="h-8 rounded-md border bg-transparent px-2 text-xs" />
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm">Duração:</span>
                  <Select value={advDuration[m.id] || 'none'} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setAdvDuration(prev => ({ ...prev, [m.id]: e.target.value as any }))}>
                    <option value="none">Indefinido</option>
                    <option value="7d">1 semana</option>
                    <option value="10d">10 dias</option>
                    <option value="30d">30 dias</option>
                    <option value="custom">Data final…</option>
                  </Select>
                  {(advDuration[m.id] || 'none') === 'custom' && (
                    <input type="date" value={advCustomUntil[m.id] || ''} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAdvCustomUntil(prev => ({ ...prev, [m.id]: e.target.value }))} className="h-8 rounded-md border bg-transparent px-2 text-xs" />
                  )}
                  <Button size="sm" onClick={async () => {
                    const expr = buildScheduleFromTimes(advTimes[m.id] || ['08:00'], (advDuration[m.id] || 'none'), advCustomUntil[m.id] || '')
                    await axios.patch(`${API}/monitors/${m.id}`, { schedule_cron: expr })
                    toast.success('Agendamento atualizado')
                    await refresh()
                  }}>Aplicar</Button>
                </div>
                <div className="text-xs opacity-70">Expressão: <span className="font-mono">{buildScheduleFromTimes(advTimes[m.id] || ['08:00'], (advDuration[m.id] || 'none'), advCustomUntil[m.id] || '') || '—'}</span></div>
              </div>
            )}
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

function MonitorRuns({ monitorId, scheduleInfo }: { monitorId: string; scheduleInfo?: { tz?: string; tz_label?: string; next_run_br?: string | null; next_runs_br?: string[]; daily_slots_br?: string[] } }) {
  const [runs, setRuns] = useState<MonitorRun[]>([])
  useEffect(() => { getMonitorRuns(monitorId).then(setRuns) }, [monitorId])
  const formatDate = (d?: string) => (d ? new Date(d).toLocaleString() : '-')
  const formatTime = (d?: string) => {
    if (!d) return '-'
    const dt = new Date(d)
    return isNaN(dt.getTime()) ? '-' : dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  const fmtCost = (v?: number | null) => (v == null ? '-' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 }).format(v))
  const grouped = useMemo(() => {
    const m = new Map<string, { promptId: string | null | undefined; promptName: string; items: MonitorRun[] }>()
    for (const r of runs) {
      const key = String(r.prompt_id || r.prompt_name || 'sem_prompt')
      const nameRaw = (r.prompt_name || 'Sem Prompt')
      const name = nameRaw.replace(/^Template:\s*/i, '').replace(/^Run:\s*/i, '').trim() || 'Sem Prompt'
      if (!m.has(key)) m.set(key, { promptId: r.prompt_id, promptName: name, items: [] })
      m.get(key)!.items.push(r)
    }
    const arr = Array.from(m.values())
    for (const g of arr) {
      g.items.sort((a, b) => String(a.started_at || '').localeCompare(String(b.started_at || '')))
    }
    arr.sort((a, b) => a.promptName.localeCompare(b.promptName))
    return arr
  }, [runs])

  const statusChip = (s: string, src?: string) => {
    if (s === 'completed') return 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/20 dark:text-green-300 dark:border-green-800'
    if (s === 'failed') return 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/20 dark:text-red-300 dark:border-red-800'
    if (s === 'running') return 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/20 dark:text-yellow-300 dark:border-yellow-800'
    // queued / pending — tint by source for clarity
    if (s === 'queued' && src === 'monitor_now') return 'bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-800'
    if (s === 'queued' && src === 'monitor') return 'bg-sky-100 text-sky-800 border-sky-300 dark:bg-sky-900/20 dark:text-sky-300 dark:border-sky-800'
    if (s === 'queued') return 'bg-neutral-100 text-neutral-800 border-neutral-300 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700'
    return 'bg-neutral-100 text-neutral-800 border-neutral-300 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700'
  }

  if (!runs.length) {
    return <div className="text-xs opacity-70">Sem runs.</div>
  }

  const nextRunLabel = (scheduleInfo?.next_run_br || (scheduleInfo?.next_runs_br || [])[0]) || ''
  return (
    <div className="space-y-3">
      {nextRunLabel && (
        <div className="flex items-center gap-2 text-xs opacity-80">
          <span className="px-2 py-0.5 rounded-full border bg-blue-50 text-blue-800 border-blue-200 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800">Próxima: {nextRunLabel}</span>
        </div>
      )}
      {grouped.map((g) => {
        const total = g.items.length
        const ok = g.items.filter(it => it.status === 'completed').length
        const fail = g.items.filter(it => it.status === 'failed').length
        return (
          <div key={`${g.promptId || g.promptName}`} className="rounded-md border border-neutral-200 dark:border-neutral-800">
            <div className="px-3 py-2 bg-white dark:bg-neutral-900 flex items-center justify-between">
              <div className="text-sm font-medium truncate">
                {g.promptName}
              </div>
              <div className="text-xs opacity-70 flex items-center gap-2">
                <span className="px-2 py-0.5 rounded border">total: <b>{total}</b></span>
                <span className="px-2 py-0.5 rounded border text-green-700 dark:text-green-300 border-green-300 dark:border-green-800">ok: <b>{ok}</b></span>
                <span className="px-2 py-0.5 rounded border text-red-700 dark:text-red-300 border-red-300 dark:border-red-800">falhas: <b>{fail}</b></span>
              </div>
            </div>
            <div className="p-3 overflow-x-auto">
              <div className="flex items-stretch gap-2 min-w-[600px]">
                {g.items.map((r) => (
                  <a key={r.id} href={`/runs/${r.id}`} className={`group w-[260px] flex-shrink-0 rounded-md border px-3 py-2 hover:shadow transition-all ${statusChip(String(r.status), String(r.schedule_source || ''))}`} title={`${g.promptName} • ${r.engine || ''}`}>
                    <div className="text-[11px] opacity-80 flex items-center justify-between">
                      <span className="font-mono">{r.id}</span>
                      <span>
                        {r.status === 'queued' && r.schedule_slot ? (
                          <span title="Agendado" className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border border-sky-300 bg-sky-50 text-sky-700 dark:bg-sky-900/20 dark:text-sky-300 dark:border-sky-800">{r.schedule_slot}</span>
                        ) : (
                          formatTime(r.started_at)
                        )}
                      </span>
                    </div>
                    <div className="mt-1 text-xs flex items-center justify-between opacity-90">
                      <span>{r.engine || '-'}</span>
                      <span>Ciclos: {r.cycles_total ?? 1}</span>
                    </div>
                    <div className="mt-1 text-[11px] flex items-center justify-between opacity-70">
                      <span>ZCRS: {r.zcrs ?? '-'}</span>
                      <span>{fmtCost(r.cost_usd)}</span>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
