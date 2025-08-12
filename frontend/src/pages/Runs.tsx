import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import RunsFilter from '../components/RunsFilter'
import { EngineLogo } from '../components/EngineLogo'
import { Toaster, toast } from 'sonner'
import { RefreshCw, Plus } from 'lucide-react'

const API = '/api'

type RunItem = {
  id: string
  engine: string
  status: string
  started_at?: string
  finished_at?: string
  zcrs?: number
  amr_flag?: boolean
  dcr_flag?: boolean
  template_name?: string
  subproject_name?: string
  cost_usd?: number
  tokens_total?: number
}

type Project = { id: string; name: string }

type Subproject = { id: string; name: string }

type Template = { id: string; name: string; text: string; category: string }

const TEMPLATES: { label: string; text: string }[] = [
  { label: 'Tarifas conta corrente BB 2025 (fontes)', text: 'Você é um avaliador. Use pesquisa na web quando necessário. Consulta: "tarifas de conta corrente do Banco do Brasil em 2025". Responda brevemente e LISTE AS FONTES com URLs completas (http) no final. Priorize páginas de bb.com.br e banco central.' },
  { label: 'Abrir conta PJ no BB (requisitos + fontes)', text: 'Explique como abrir conta PJ no Banco do Brasil: requisitos, documentos e prazos. Liste 3–5 fontes com URLs completas (bb.com.br, gov.br).' },
  { label: 'Poupança BB hoje (fontes Bacen/BB)', text: 'Qual é o rendimento da poupança no Banco do Brasil hoje? Explique a regra atual e cite fontes (Bacen e BB) com URLs.' },
  { label: 'Cartão Ourocard (taxas/anuidades + fontes)', text: 'Quais as taxas e anuidades dos cartões Ourocard? Liste modelos e forneça fontes oficiais do BB com URLs.' },
  { label: 'Empréstimo consignado BB (taxas atuais + fontes)', text: 'Quais as taxas atuais de empréstimo consignado do Banco do Brasil? Traga 3–5 fontes oficiais (bb.com.br e Bacen) com URLs.' },
  { label: 'Pix no BB (limites e tarifas + fontes)', text: 'Quais os limites e eventuais tarifas do Pix no Banco do Brasil? Liste fontes (bb.com.br, bacen) com URLs.' },
  { label: 'Seguro Auto BB (coberturas + fontes)', text: 'Quais coberturas do Seguro Auto BB Seguros e o que observar? Liste fontes oficiais com URLs (bbseguros.com.br).' },
  { label: 'Conta Universitária BB (benefícios + fontes)', text: 'Quais os benefícios e tarifas da conta universitária do Banco do Brasil? Cite fontes oficiais com URLs.' },
  { label: 'Tesouro Direto via BB (taxas + fontes)', text: 'Quais taxas de custódia/corretagem para investir em Tesouro via Banco do Brasil? Cite fontes (bb.com.br, tesourodireto.com.br) com URLs.' },
  { label: 'Canais e atendimento BB (horários + fontes)', text: 'Quais canais oficiais do Banco do Brasil e horários de atendimento? Liste fontes com URLs de bb.com.br.' },
]

const ENGINE_OPTIONS = [
  { label: 'OpenAI GPT-5 (web search — low context)', name: 'openai', config_json: { model: 'gpt-5', web_search: true, search_context_size: 'low', reasoning_effort: 'low' } },
  { label: 'OpenAI GPT-4.1 (web search — low context)', name: 'openai', config_json: { model: 'gpt-4.1', web_search: true, search_context_size: 'low', reasoning_effort: 'low' } },
  { label: 'Gemini 2.5 Pro (web search)', name: 'gemini', config_json: { model: 'gemini-2.5-pro' } },
  { label: 'Gemini 2.5 Flash (web search)', name: 'gemini', config_json: { model: 'gemini-2.5-flash' } },
  { label: 'Perplexity Sonar Pro (web search)', name: 'perplexity', config_json: { model: 'sonar-pro' } },
  { label: 'Google SERP (AI Overview via SerpAPI)', name: 'google_serp', config_json: { use_serpapi: true, serpapi_ai_overview: true, serpapi_no_cache: false } },
]

export default function Runs() {
  const location = useLocation()
  const navigate = useNavigate()
  const [runs, setRuns] = useState<RunItem[]>([])
  const [showModal, setShowModal] = useState(false)
  const [engineFilter, setEngineFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [query, setQuery] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [page, setPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(50)
  const [orderBy, setOrderBy] = useState<string>('started_at')
  const [orderDir, setOrderDir] = useState<'asc'|'desc'>('desc')

  const fetchRuns = async () => {
    const params: any = {}
    if (projectId) params.project_id = projectId
    if (subprojectId) params.subproject_id = subprojectId
    if (engineFilter) params.engine = engineFilter
    if (statusFilter) params.status = statusFilter
    if (dateFrom) params.date_from = `${dateFrom}T00:00:00`
    if (dateTo) params.date_to = `${dateTo}T23:59:59`
    params.page = page
    params.page_size = pageSize
    params.order_by = orderBy
    params.order_dir = orderDir
    const res = await axios.get(`${API}/runs`, { params })
    setRuns(res.data)
  }

  useEffect(() => {
    axios.get<Project[]>(`${API}/projects`).then((r) => {
      setProjects(r.data)
      if (!projectId && r.data[0]?.id) {
        setProjectId(r.data[0].id)
        localStorage.setItem('project_id', r.data[0].id)
      }
    })
  }, [])

  useEffect(() => {
    const p = new URLSearchParams(location.search)
    const q = p.get('q') || ''
    const openNew = p.get('new') === '1'
    setQuery(q)
    if (openNew) setShowModal(true)
  }, [location.search])

  useEffect(() => { fetchRuns() }, [engineFilter, statusFilter, subprojectId, dateFrom, dateTo, page, pageSize, orderBy, orderDir])
  useEffect(() => { const t = setInterval(fetchRuns, 5000); return () => clearInterval(t) }, [engineFilter, statusFilter, subprojectId, dateFrom, dateTo, page, pageSize, orderBy, orderDir])
  useEffect(() => { if (projectId) { setPage(1); fetchRuns() } }, [projectId])

  useEffect(() => {
    if (!projectId) return
    localStorage.setItem('project_id', projectId)
    axios.get<Subproject[]>(`${API}/projects/${projectId}/subprojects`).then((r) => setSubprojects(r.data))
  }, [projectId])

  const engines = useMemo(() => Array.from(new Set(runs.map((r: RunItem) => r.engine))), [runs])
  const filtered = useMemo(() => {
    const list = runs.filter((r: RunItem) => (!query || r.id.includes(query)))
    return list
  }, [runs, query])

  const projectName = useMemo(() => projects.find(p => p.id === projectId)?.name || '', [projects, projectId])
  const themeName = useMemo(() => subprojects.find(s => s.id === subprojectId)?.name || '', [subprojects, subprojectId])

  const clearThemeFocus = () => {
    setSubprojectId('')
    localStorage.removeItem('theme_focus')
    localStorage.removeItem('subproject_focus')
  }

  return (
    <div className="space-y-3">
      <Toaster richColors position="top-right" />
      <div className="text-xs px-3 py-2 border rounded-md flex flex-wrap items-center gap-2 bg-white dark:bg-neutral-900">
        {projectName && (
          <span>
            Projeto: <span className="font-medium">{projectName}</span>
          </span>
        )}
        {themeName && (
          <span>
            Tema: <span className="font-medium">{themeName}</span>
          </span>
        )}
        <a href="/settings" className="ml-auto underline">alterar</a>
        {themeName && (
          <button className="underline" onClick={clearThemeFocus}>limpar</button>
        )}
      </div>
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Runs</h1>
        <Button variant="outline" size="sm" onClick={() => { fetchRuns().then(()=>toast.success('Atualizado')) }} className="ml-2"><RefreshCw className="h-4 w-4" /></Button>
        <Button className="ml-auto" onClick={() => setShowModal(true)}><Plus className="h-4 w-4 mr-1" /> Nova Run</Button>
      </div>
      <RunsFilter
        projects={projects}
        projectId={projectId}
        setProjectId={setProjectId}
        subprojects={subprojects}
        subprojectId={subprojectId}
        setSubprojectId={setSubprojectId}
        engines={engines}
        engineFilter={engineFilter}
        setEngineFilter={setEngineFilter}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        dateFrom={dateFrom}
        setDateFrom={setDateFrom}
        dateTo={dateTo}
        setDateTo={setDateTo}
        query={query}
        setQuery={setQuery}
        onSearch={() => navigate(`/runs?q=${encodeURIComponent(query)}`)}
        onRefresh={fetchRuns}
        totalResults={filtered.length}
      />
      
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 text-sm">
          <span className="opacity-70">Página</span>
          <Button variant="outline" size="sm" onClick={() => setPage((p: number) => Math.max(1, p - 1))} disabled={page === 1}>Anterior</Button>
          <span className="px-2">{page}</span>
          <Button variant="outline" size="sm" onClick={() => setPage((p: number) => p + 1)} disabled={runs.length < pageSize}>Próxima</Button>
        </div>
        <div className="flex items-center gap-3 text-sm ml-auto mt-2 sm:mt-0">
          <span className="opacity-70">Ordenar por</span>
          <Select value={orderBy} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setOrderBy(e.target.value); setPage(1) }}>
            <option value="started_at">Início</option>
            <option value="finished_at">Fim</option>
            <option value="zcrs">ZCRS</option>
            <option value="cost_usd">Custo</option>
            <option value="tokens_total">Tokens</option>
            <option value="status">Status</option>
            <option value="engine">Engine</option>
          </Select>
          <Select value={orderDir} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setOrderDir(e.target.value as 'asc'|'desc'); setPage(1) }}>
            <option value="desc">Desc</option>
            <option value="asc">Asc</option>
          </Select>
          <span className="opacity-70 ml-2">Itens por página</span>
          <Select value={String(pageSize)} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setPageSize(parseInt(e.target.value)); setPage(1) }}>
            {[25,50,100,150,200].map((n: number) => <option key={n} value={n}>{n}</option>)}
          </Select>
        </div>
      </div>
      <div className="overflow-auto rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-sm">
        <table className="min-w-full text-sm table-fixed">
          <thead className="bg-neutral-50 dark:bg-neutral-900 z-10">
            <tr className="text-neutral-500 text-xs sticky top-0 z-10">
              <Th>ID</Th>
              <Th>Engine</Th>
              <Th>Status</Th>
              <Th>Início</Th>
              <Th>Fim</Th>
              <Th>ZCRS</Th>
              <Th>AMR</Th>
              <Th>DCR</Th>
              <Th>Template</Th>
              <Th>Tema</Th>
              <Th>Custo</Th>
              <Th>Tokens</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r: RunItem, idx: number) => (
              <tr key={r.id} className={`border-t border-neutral-200 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-900/40 ${idx % 2 === 1 ? 'bg-neutral-50/40 dark:bg-neutral-900/30' : ''}`}>
                <Td><a className="text-blue-600" href={`/runs/${r.id}`}>{r.id}</a></Td>
                <Td>
                  <div className="flex items-center gap-2">
                    <EngineLogo name={r.engine} className="h-5 w-5" />
                    <span className="font-medium tracking-tight">{r.engine}</span>
                  </div>
                </Td>
                <Td>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    r.status === 'completed' ? 'bg-green-100 text-green-800' :
                    r.status === 'failed' ? 'bg-red-100 text-red-800' :
                    r.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {r.status}
                  </span>
                </Td>
                <Td>{r.started_at || '-'}</Td>
                <Td>{r.finished_at || '-'}</Td>
                <Td>{r.zcrs?.toFixed(1) ?? '-'}</Td>
                <Td>{r.amr_flag ? '1' : '0'}</Td>
                <Td>{r.dcr_flag ? '1' : '0'}</Td>
                <Td>{r.template_name || '-'}</Td>
                <Td>{r.subproject_name || '-'}</Td>
                <Td>{typeof r.cost_usd === 'number' ? `$${r.cost_usd.toFixed(4)}` : '-'}</Td>
                <Td>{typeof r.tokens_total === 'number' ? r.tokens_total : '-'}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showModal && <NewRunModal onClose={() => { setShowModal(false); fetchRuns(); navigate('/runs', { replace: true }) }} />}
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

function FilterBar(props: {
  projects: Project[]
  projectId: string
  setProjectId: (v: string) => void
  subprojects: Subproject[]
  subprojectId: string
  setSubprojectId: (v: string) => void
  engines: string[]
  engineFilter: string
  setEngineFilter: (v: string) => void
  statusFilter: string
  setStatusFilter: (v: string) => void
  dateFrom: string
  setDateFrom: (v: string) => void
  dateTo: string
  setDateTo: (v: string) => void
  query: string
  setQuery: (v: string) => void
  onSearch: () => void
}) {
  const [open, setOpen] = useState<boolean>(false)
  const projectName = props.projects.find(p => p.id === props.projectId)?.name
  const themeName = props.subprojects.find(s => s.id === props.subprojectId)?.name

  const fmtChipDate = (s: string) => {
    if (!s) return ''
    try {
      const d = new Date(s)
      const dd = String(d.getDate()).padStart(2, '0')
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      return `${dd}/${mm}`
    } catch {
      return s
    }
  }

  const activeChips: Array<{ key: string; label: string; onClear: () => void }> = []
  if (projectName) activeChips.push({ key: 'project', label: `Projeto: ${projectName}`, onClear: () => {} })
  if (themeName) activeChips.push({ key: 'theme', label: `Tema: ${themeName}`, onClear: () => props.setSubprojectId('') })
  if (props.engineFilter) activeChips.push({ key: 'engine', label: `Engine: ${props.engineFilter}`, onClear: () => props.setEngineFilter('') })
  if (props.statusFilter) activeChips.push({ key: 'status', label: `Status: ${props.statusFilter}`, onClear: () => props.setStatusFilter('') })
  if (props.dateFrom) activeChips.push({ key: 'from', label: `De: ${fmtChipDate(props.dateFrom)}`, onClear: () => props.setDateFrom('') })
  if (props.dateTo) activeChips.push({ key: 'to', label: `Até: ${fmtChipDate(props.dateTo)}`, onClear: () => props.setDateTo('') })
  if (props.query) activeChips.push({ key: 'q', label: `ID: ${props.query}`, onClear: () => props.setQuery('') })

  const setQuickRange = (range: 'today' | 7 | 30 | 'all') => {
    if (range === 'all') { props.setDateFrom(''); props.setDateTo(''); return }
    const now = new Date()
    const end = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()))
    const start = new Date(end)
    if (range === 'today') {
      // start == end
    } else {
      start.setUTCDate(start.getUTCDate() - (range as number))
    }
    const fmt = (d: Date) => `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`
    props.setDateFrom(fmt(start))
    props.setDateTo(fmt(end))
  }

  const resetAll = () => {
    // Mantém projeto, limpa demais filtros
    props.setSubprojectId('')
    props.setEngineFilter('')
    props.setStatusFilter('')
    props.setDateFrom('')
    props.setDateTo('')
    props.setQuery('')
  }

  return (
    <div className="border rounded-md">
      <div className="p-2 flex items-center gap-2">
        <div className="text-sm font-medium">Filtros</div>
        <div className="flex flex-wrap gap-1">
          {activeChips.length ? activeChips.map(ch => (
            <button key={ch.key} className="text-xs px-2 py-0.5 border rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-800" onClick={ch.onClear}>
              {ch.label} ×
            </button>
          )) : <span className="text-xs opacity-60">Nenhum filtro ativo</span>}
        </div>
        <div className="ml-auto flex items-center gap-1 text-xs">
          <Button variant="outline" size="sm" onClick={() => setQuickRange('today')}>Hoje</Button>
          <Button variant="outline" size="sm" onClick={() => setQuickRange(7)}>7d</Button>
          <Button variant="outline" size="sm" onClick={() => setQuickRange(30)}>30d</Button>
          <Button variant="outline" size="sm" onClick={() => setQuickRange('all')}>Tudo</Button>
          <Button variant="outline" size="sm" onClick={resetAll}>Limpar</Button>
          <Button variant="outline" size="sm" onClick={() => setOpen(v=>!v)}>{open ? 'Ocultar' : 'Mostrar'}</Button>
        </div>
      </div>
      {open && (
        <div className="p-2 grid gap-2 items-center" style={{ gridTemplateColumns: 'repeat(12, minmax(0, 1fr))' }}>
          <Select value={props.projectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setProjectId(e.target.value)} className="col-span-12 sm:col-span-3">
            {props.projects.map((p: Project) => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
          </Select>
          <Select value={props.subprojectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setSubprojectId(e.target.value)} className="col-span-12 sm:col-span-3">
            <option value="">Todos os temas</option>
            {props.subprojects.map((sp: Subproject) => <option key={sp.id} value={sp.id}>{sp.name}</option>)}
          </Select>
          <Select value={props.engineFilter} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setEngineFilter(e.target.value)} className="col-span-6 sm:col-span-2">
            <option value="">Todas as engines</option>
            {props.engines.map((e: string) => <option key={e} value={e}>{e}</option>)}
          </Select>
          <Select value={props.statusFilter} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setStatusFilter(e.target.value)} className="col-span-6 sm:col-span-2">
            <option value="">Todos os status</option>
            {['queued','running','completed','failed'].map((s: string) => <option key={s} value={s}>{s}</option>)}
          </Select>
          <div className="col-span-12 sm:col-span-2 flex items-center gap-1 text-xs">
            <span className="opacity-70">De</span>
            <Input type="date" value={props.dateFrom} onChange={(e: React.ChangeEvent<HTMLInputElement>) => props.setDateFrom(e.target.value)} />
            <span className="opacity-70">Até</span>
            <Input type="date" value={props.dateTo} onChange={(e: React.ChangeEvent<HTMLInputElement>) => props.setDateTo(e.target.value)} />
          </div>
          <div className="col-span-12 sm:col-span-4 flex items-center gap-2">
            <Input placeholder="Buscar por ID" value={props.query} onChange={(e: React.ChangeEvent<HTMLInputElement>) => props.setQuery(e.target.value)} onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => { if (e.key === 'Enter') props.onSearch() }} />
            <Button variant="secondary" size="sm" onClick={props.onSearch}>Buscar</Button>
          </div>
        </div>
      )}
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="text-left p-2">{children}</th>
}
function Td({ children }: { children: React.ReactNode }) {
  return <td className="p-2">{children}</td>
}

function NewRunModal({ onClose }: { onClose: () => void }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState<string>('')
  const [templateIdx, setTemplateIdx] = useState(0)
  const [engineIdx, setEngineIdx] = useState(0)
  const [customPrompt, setCustomPrompt] = useState('')
  const [cycles, setCycles] = useState(1)
  const [creating, setCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState('Projeto Banco – BR pt-BR')
  const [templates, setTemplates] = useState<Template[]>([])
  const [category, setCategory] = useState<string>('')
  // OpenAI opções avançadas
  const isOpenAI = ENGINE_OPTIONS[engineIdx]?.name === 'openai'
  const [webSearch, setWebSearch] = useState<boolean>(true)
  const [forceTool, setForceTool] = useState<boolean>(false)
  const [searchContextSize, setSearchContextSize] = useState<'low'|'medium'|'high'>('low')
  const [reasoningEffort, setReasoningEffort] = useState<'low'|'medium'|'high'>('low')
  const [maxOutputTokens, setMaxOutputTokens] = useState<string>('2048')
  const [systemPrompt, setSystemPrompt] = useState<string>(
    'Você é um analista objetivo. Não faça perguntas nem peça confirmações. Responda diretamente, de forma assertiva e organizada. Sempre liste as fontes no final com URLs completas (http).'
  )
  const [country, setCountry] = useState<string>('')
  const [city, setCity] = useState<string>('')
  const [region, setRegion] = useState<string>('')
  // Google SERP opções
  const isGoogleSerp = ENGINE_OPTIONS[engineIdx]?.name === 'google_serp'
  const [serpUseSerpapi, setSerpUseSerpapi] = useState<boolean>(true)
  const [serpAiOverview, setSerpAiOverview] = useState<boolean>(true)
  const [serpNoCache, setSerpNoCache] = useState<boolean>(false)

  useEffect(() => {
    axios.get<Project[]>(`${API}/projects`).then((r) => {
      setProjects(r.data)
      if (!projectId && r.data[0]?.id) setProjectId(r.data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!projectId) return
    axios.get<Subproject[]>(`${API}/projects/${projectId}/subprojects`).then((r) => setSubprojects(r.data))
    const params = category ? { params: { category } } : undefined
    axios.get<Template[]>(`${API}/projects/${projectId}/templates`, params as any).then((r) => setTemplates(r.data))
  }, [projectId, category])

  const createQuickProject = async () => {
    const res = await axios.post(`${API}/projects`, { name: newProjectName, country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
    const id = res.data.id as string
    setProjects((prev: Project[]) => [{ id, name: newProjectName }, ...prev])
    setProjectId(id)
    localStorage.setItem('project_id', id)
  }

  const submit = async () => {
    try {
      if (!projectId) throw new Error('Selecione ou crie um projeto')
      localStorage.setItem('project_id', projectId)
      setCreating(true)

      // Se há prompt customizado, usa ele diretamente; caso contrário, usa template (remoto ou local)
      if (customPrompt.trim()) {
        const promptRes = await axios.post(`${API}/projects/${projectId}/prompts`, {
          name: `Prompt custom (${new Date().toISOString()})`,
          text: customPrompt,
          intent: 'Ad-hoc',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.data.id
        const pvRes = await axios.get(`${API}/prompts/${promptId}/versions`)
        const versions = pvRes.data as any[]
        const pvId = versions[versions.length - 1].id
        const engine = ENGINE_OPTIONS[engineIdx]
        // montar config_json com opções avançadas
        let cfg: any = { ...(engine.config_json || {}) }
        if (engine.name === 'openai') {
          cfg = {
            ...cfg,
            web_search: webSearch,
            search_context_size: searchContextSize,
            reasoning_effort: reasoningEffort,
            ...(maxOutputTokens ? { max_output_tokens: parseInt(maxOutputTokens) } : {}),
            ...(forceTool ? { web_search_force: true } : {}),
            ...((country || city || region) ? { user_location: { type: 'approximate', country: country || undefined, city: city || undefined, region: region || undefined } } : {}),
            ...(systemPrompt ? { system: systemPrompt } : {}),
          }
        } else if (engine.name === 'google_serp') {
          cfg = {
            ...cfg,
            use_serpapi: serpUseSerpapi,
            serpapi_ai_overview: serpAiOverview,
            serpapi_no_cache: serpNoCache,
          }
        }
        await axios.post(`${API}/runs`, {
          project_id: projectId,
          prompt_version_id: pvId,
          engines: [{ name: engine.name, region: 'BR', device: 'desktop', config_json: cfg }],
          cycles,
          subproject_id: subprojectId || null,
        })
      } else if (templates.length) {
        const t = templates[templateIdx]
        const promptRes = await axios.post(`${API}/projects/${projectId}/prompts`, {
          name: `Template: ${t.name}`,
          text: t.text,
          intent: 'Informacional',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.data.id
        const pvRes = await axios.get(`${API}/prompts/${promptId}/versions`)
        const versions = pvRes.data as any[]
        const pvId = versions[versions.length - 1].id
        const engine = ENGINE_OPTIONS[engineIdx]
        let cfg: any = { ...(engine.config_json || {}) }
        if (engine.name === 'openai') {
          cfg = {
            ...cfg,
            web_search: webSearch,
            search_context_size: searchContextSize,
            reasoning_effort: reasoningEffort,
            ...(maxOutputTokens ? { max_output_tokens: parseInt(maxOutputTokens) } : {}),
            ...(forceTool ? { web_search_force: true } : {}),
            ...((country || city || region) ? { user_location: { type: 'approximate', country: country || undefined, city: city || undefined, region: region || undefined } } : {}),
            ...(systemPrompt ? { system: systemPrompt } : {}),
          }
        } else if (engine.name === 'google_serp') {
          cfg = {
            ...cfg,
            use_serpapi: serpUseSerpapi,
            serpapi_ai_overview: serpAiOverview,
            serpapi_no_cache: serpNoCache,
          }
        }
        await axios.post(`${API}/runs`, {
          project_id: projectId,
          prompt_version_id: pvId,
          engines: [{ name: engine.name, region: 'BR', device: 'desktop', config_json: cfg }],
          cycles,
          subproject_id: subprojectId || null,
        })
      } else {
        const promptRes = await axios.post(`${API}/projects/${projectId}/prompts`, {
          name: `Template: ${TEMPLATES[templateIdx].label}`,
          text: TEMPLATES[templateIdx].text,
          intent: 'Informacional',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.data.id
        const pvRes = await axios.get(`${API}/prompts/${promptId}/versions`)
        const versions = pvRes.data as any[]
        const pvId = versions[versions.length - 1].id
        const engine = ENGINE_OPTIONS[engineIdx]
        let cfg: any = { ...(engine.config_json || {}) }
        if (engine.name === 'openai') {
          cfg = {
            ...cfg,
            web_search: webSearch,
            search_context_size: searchContextSize,
            reasoning_effort: reasoningEffort,
            ...(maxOutputTokens ? { max_output_tokens: parseInt(maxOutputTokens) } : {}),
            ...(forceTool ? { web_search_force: true } : {}),
            ...((country || city || region) ? { user_location: { type: 'approximate', country: country || undefined, city: city || undefined, region: region || undefined } } : {}),
            ...(systemPrompt ? { system: systemPrompt } : {}),
          }
        } else if (engine.name === 'google_serp') {
          cfg = {
            ...cfg,
            use_serpapi: serpUseSerpapi,
            serpapi_ai_overview: serpAiOverview,
            serpapi_no_cache: serpNoCache,
          }
        }
        await axios.post(`${API}/runs`, {
          project_id: projectId,
          prompt_version_id: pvId,
          engines: [{ name: engine.name, region: 'BR', device: 'desktop', config_json: cfg }],
          cycles,
          subproject_id: subprojectId || null,
        })
      }

      toast.success('Nova run criada')
      onClose()
      window.location.href = '/runs'
    } catch (e: any) {
      toast.error('Erro ao criar run: ' + e.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 grid place-items-center p-4 z-50">
      <div className="bg-white dark:bg-neutral-900 rounded-lg p-4 w:[min(820px,100%)] w-[min(820px,100%)] space-y-3 border border-neutral-200 dark:border-neutral-800 shadow-lg">
        <h2 className="text-lg font-semibold">Nova Run</h2>
        <div className="grid gap-3">
          <div className="grid gap-1">
            <div className="text-sm text-neutral-500">Projeto</div>
            <div className="flex gap-2 items-center">
              <Select value={projectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setProjectId(e.target.value)} className="min-w-[280px]">
                {projects.map((p: Project) => (
                  <option key={p.id} value={p.id}>{p.name} ({p.id})</option>
                ))}
              </Select>
              <Button variant="secondary" onClick={createQuickProject}>Criar rápido</Button>
            </div>
          </div>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Subprojeto (opcional)</div>
            <Select value={subprojectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSubprojectId(e.target.value)}>
              <option value="">—</option>
              {subprojects.map((s: Subproject) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
          </label>
          <div className="grid gap-1">
            <div className="text-sm text-neutral-500">Categoria de Template</div>
            <Input placeholder="(opcional) Filtrar categoria" value={category} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCategory(e.target.value)} />
          </div>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Template</div>
            <Select value={String(templateIdx)} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTemplateIdx(parseInt(e.target.value))}>
              {templates.length ? templates.map((t: Template, i: number) => (<option key={t.id} value={i}>{t.category} • {t.name}</option>)) : TEMPLATES.map((t, i) => (<option key={i} value={i}>{t.label}</option>))}
            </Select>
          </label>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Prompt personalizado (opcional)</div>
            <textarea value={customPrompt} onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCustomPrompt(e.target.value)} placeholder="Escreva aqui seu prompt..." className="min-h-[120px] p-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent" />
            <div className="text-[11px] opacity-60">Se preenchido, será usado como prompt no lugar do template.</div>
          </label>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Engine</div>
            <Select value={String(engineIdx)} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setEngineIdx(parseInt(e.target.value))}>
              {ENGINE_OPTIONS.map((e, i: number) => (
                <option key={i} value={i}>{e.label}</option>
              ))}
            </Select>
          </label>
          {isOpenAI && (
            <div className="grid gap-2 p-3 rounded-md border border-neutral-200 dark:border-neutral-800">
              <div className="text-sm font-medium">OpenAI – Opções avançadas</div>
              <label className="text-sm flex items-center gap-2">
                <input type="checkbox" checked={webSearch} onChange={(e) => setWebSearch(e.target.checked)} /> Usar web search
              </label>
              <label className="text-sm flex items-center gap-2">
                <input type="checkbox" checked={forceTool} onChange={(e) => setForceTool(e.target.checked)} /> Forçar tool web_search
              </label>
              <div className="grid sm:grid-cols-3 gap-2">
                <label className="grid gap-1">
                  <div className="text-xs opacity-70">Search context size</div>
                  <Select value={searchContextSize} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSearchContextSize(e.target.value as any)}>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </Select>
                </label>
                <label className="grid gap-1">
                  <div className="text-xs opacity-70">Reasoning effort</div>
                  <Select value={reasoningEffort} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setReasoningEffort(e.target.value as any)}>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </Select>
                </label>
                <label className="grid gap-1">
                  <div className="text-xs opacity-70">max_output_tokens</div>
                  <Input type="number" min={16} value={maxOutputTokens} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMaxOutputTokens(e.target.value)} />
                </label>
              </div>
              <div className="grid sm:grid-cols-3 gap-2">
                <label className="grid gap-1">
                  <div className="text-xs opacity-70">País (ISO‑2)</div>
                  <Input placeholder="BR" value={country} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCountry(e.target.value.toUpperCase())} />
                </label>
                <label className="grid gap-1">
                  <div className="text-xs opacity-70">Cidade</div>
                  <Input placeholder="São Paulo" value={city} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCity(e.target.value)} />
                </label>
                <label className="grid gap-1">
                  <div className="text-xs opacity-70">Região/Estado</div>
                  <Input placeholder="SP" value={region} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRegion(e.target.value)} />
                </label>
              </div>
              <label className="grid gap-1">
                <div className="text-xs opacity-70">System prompt</div>
                <textarea value={systemPrompt} onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setSystemPrompt(e.target.value)} className="min-h-[80px] p-2 rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent" />
              </label>
              <div className="text-[11px] opacity-60">Dica: use search_context_size = low para reduzir tokens (in).</div>
            </div>
          )}
          {isGoogleSerp && (
            <div className="grid gap-2 p-3 rounded-md border border-neutral-200 dark:border-neutral-800">
              <div className="text-sm font-medium">Google SERP – SerpApi / AI Overview</div>
              <label className="text-sm flex items-center gap-2">
                <input type="checkbox" checked={serpUseSerpapi} onChange={(e) => setSerpUseSerpapi(e.target.checked)} /> Usar SerpApi
              </label>
              <label className="text-sm flex items-center gap-2">
                <input type="checkbox" checked={serpAiOverview} onChange={(e) => setSerpAiOverview(e.target.checked)} /> Preferir AI Overview
              </label>
              <label className="text-sm flex items-center gap-2">
                <input type="checkbox" checked={serpNoCache} onChange={(e) => setSerpNoCache(e.target.checked)} /> Ignorar cache (no_cache)
              </label>
              <div className="text-[11px] opacity-60">Requer chave SerpApi válida em Configurações. AI Overview será usado quando disponível; caso contrário, cai para resultados orgânicos ou Playwright.</div>
            </div>
          )}
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Cycles</div>
            <Input type="number" min={1} value={String(cycles)} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCycles(parseInt(e.target.value || '1'))} className="w-24" />
          </label>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button onClick={submit} disabled={creating}>{creating ? 'Criando…' : 'Criar'}</Button>
        </div>
      </div>
    </div>
  )
}
