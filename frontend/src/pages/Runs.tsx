import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { listRuns, getProjects, getSubprojects, getTemplates, createProject, createPrompt, getPromptVersions, createRun, deleteRun } from '../lib/api'
import { Button } from '../components/ui/button'
import { formatNumberCompact } from '../lib/utils'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import SimpleRunsFilter from '../components/SimpleRunsFilter'
import { Toaster, toast } from 'sonner'
import { RefreshCw, Plus, Trash2 } from 'lucide-react'
import { Skeleton } from '../components/ui/skeleton'

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
  template_category?: string
  subproject_name?: string
  cost_usd?: number
  tokens_total?: number
}

type Project = { id: string; name: string }

type Subproject = { id: string; name: string }

type Template = { id: string; name: string; text: string; category: string; subproject_id?: string }

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
  { label: 'OpenAI GPT-5 mini (web search — low context)', name: 'openai', config_json: { model: 'gpt-5-mini', web_search: true, search_context_size: 'low', reasoning_effort: 'low' } },
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
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  // Map template name -> { category, subproject_id }
  const [templateCatIndex, setTemplateCatIndex] = useState<Record<string, { category: string; subproject_id?: string }>>({})

  const fetchRuns = async () => {
    const params: any = {}
    if (projectId) params.project_id = projectId
    if (subprojectId) params.subproject_id = subprojectId
    if (engineFilter) params.engine = engineFilter
    setLoading(true)
    try {
      const res = await listRuns(params)
      setRuns(res)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    getProjects().then((r) => {
      setProjects(r)
      if (!projectId && r[0]?.id) {
        setProjectId(r[0].id)
        localStorage.setItem('project_id', r[0].id)
      }
    })
  }, [])

  useEffect(() => {
    const p = new URLSearchParams(location.search)
    const openNew = p.get('new') === '1'
    if (openNew) setShowModal(true)
  }, [location.search])

  useEffect(() => { fetchRuns() }, [engineFilter, subprojectId])
  useEffect(() => { const t = setInterval(fetchRuns, 5000); return () => clearInterval(t) }, [engineFilter, subprojectId])
  useEffect(() => { if (projectId) { fetchRuns() } }, [projectId])

  // Build template name -> category index for current project
  useEffect(() => {
    if (!projectId) return
    getTemplates(projectId, undefined, undefined).then((tpls: any[]) => {
      const idx: Record<string, { category: string; subproject_id?: string }> = {}
      for (const t of tpls) idx[t.name] = { category: t.category, subproject_id: t.subproject_id }
      setTemplateCatIndex(idx)
    })
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    localStorage.setItem('project_id', projectId)
    getSubprojects(projectId).then((r) => setSubprojects(r))
  }, [projectId])

  const engines = useMemo(() => Array.from(new Set(runs.map((r: RunItem) => r.engine))), [runs])
  const grouped = useMemo(() => {
    const m = new Map<string, RunItem[]>()
    for (const r of runs) {
      const k = r.subproject_name || 'Sem tema'
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(r)
    }
    const arr = Array.from(m.entries()) as Array<[string, RunItem[]]>
    // sort items (newest first) and groups by theme name
    for (const [, items] of arr) {
      items.sort((a, b) => String(b.started_at || '').localeCompare(String(a.started_at || '')))
    }
    arr.sort((a, b) => a[0].localeCompare(b[0]))
    return arr
  }, [runs])

  const sortedRuns = useMemo(() => {
    const copy = [...runs]
    copy.sort((a, b) => String(b.started_at || '').localeCompare(String(a.started_at || '')))
    return copy
  }, [runs])

  const projectName = useMemo(() => projects.find(p => p.id === projectId)?.name || '', [projects, projectId])
  const themeName = useMemo(() => subprojects.find(s => s.id === subprojectId)?.name || '', [subprojects, subprojectId])

  const clearThemeFocus = () => {
    setSubprojectId('')
    localStorage.removeItem('theme_focus')
    localStorage.removeItem('subproject_focus')
  }

  const handleDeleteRun = async (id: string) => {
    if (!confirm('Excluir esta run? Esta ação não pode ser desfeita.')) return
    try {
      await deleteRun(id)
      toast.success('Run excluída')
      await fetchRuns()
    } catch (e: any) {
      toast.error('Erro ao excluir run')
    }
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
        <span className="ml-auto" />
        {themeName && (
          <button className="underline" onClick={clearThemeFocus}>limpar</button>
        )}
      </div>
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Runs</h1>
        <Button variant="outline" size="sm" onClick={() => { fetchRuns().then(()=>toast.success('Atualizado')) }} className="ml-2"><RefreshCw className="h-4 w-4" /></Button>
        <Button className="ml-auto" onClick={() => setShowModal(true)}><Plus className="h-4 w-4 mr-1" /> Nova Run</Button>
      </div>
      <SimpleRunsFilter
        subprojects={subprojects}
        subprojectId={subprojectId}
        setSubprojectId={setSubprojectId}
        engines={engines}
        engineFilter={engineFilter}
        setEngineFilter={setEngineFilter}
        onRefresh={fetchRuns}
      />
      <div className="space-y-4">
        {loading && runs.length === 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="rounded-md border border-neutral-200 dark:border-neutral-800 p-3">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-4 w-12 rounded-full" />
                </div>
                <Skeleton className="h-4 w-28 mt-3" />
                <Skeleton className="h-3 w-40 mt-2" />
                <div className="flex gap-3 mt-3">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            ))}
          </div>
        ) : runs.length === 0 ? (
          <div className="p-10 text-center border rounded-md border-neutral-200 dark:border-neutral-800">
            <div className="text-sm opacity-70">Nenhuma run encontrada.</div>
            <Button className="mt-3" onClick={() => setShowModal(true)}><Plus className="h-4 w-4 mr-1" /> Nova Run</Button>
          </div>
        ) : !subprojectId ? (
          grouped.map(([theme, items]) => {
            // group items by category; prefer backend template_category, fallback to client-side mapping
            const byCat = new Map<string, RunItem[]>()
            for (const r of items) {
              let cat = (r.template_category || '').trim()
              if (!cat) {
                if (r.template_name) {
                  const nm = r.template_name.replace(/^Template:\s*/i, '').trim()
                  const idx = templateCatIndex[nm]
                  if (idx?.category) cat = idx.category
                }
              }
              if (!cat) cat = 'Outros'
              if (!byCat.has(cat)) byCat.set(cat, [])
              byCat.get(cat)!.push(r)
            }
            const cats = Array.from(byCat.entries()).sort((a, b) => a[0].localeCompare(b[0]))
            return (
              <div key={theme} className="rounded-lg border border-neutral-200 dark:border-neutral-800 overflow-hidden fade-in-up">
                <div className="px-3 py-2 bg-neutral-50 dark:bg-neutral-900 flex items-center justify-between">
                  <div className="text-sm font-medium">{theme}</div>
                  <div className="text-xs opacity-60">{items.length} runs</div>
                </div>
                <div className="p-3 space-y-4">
                  {cats.map(([cat, catItems]) => (
                    <div key={cat} className="rounded-md border border-neutral-200 dark:border-neutral-800">
                      <div className="px-3 py-2 bg-white dark:bg-neutral-900 flex items-center justify-between">
                        <div className="text-sm font-medium">{cat}</div>
                        <div className="text-xs opacity-60">{catItems.length} runs</div>
                      </div>
                      <div className="p-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {catItems.map((r) => (<RunCard key={r.id} r={r} onDelete={handleDeleteRun} />))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })
        ) : (
          // When a single theme is selected, group the visible runs by category as well
          (() => {
            const byCat = new Map<string, RunItem[]>()
            for (const r of sortedRuns) {
              let cat = (r.template_category || '').trim()
              if (!cat) {
                if (r.template_name) {
                  const nm = r.template_name.replace(/^Template:\s*/i, '').trim()
                  const idx = templateCatIndex[nm]
                  if (idx?.category) cat = idx.category
                }
              }
              if (!cat) cat = 'Outros'
              if (!byCat.has(cat)) byCat.set(cat, [])
              byCat.get(cat)!.push(r)
            }
            const cats = Array.from(byCat.entries()).sort((a, b) => a[0].localeCompare(b[0]))
            return (
              <div className="space-y-4">
                {cats.map(([cat, catItems]) => (
                  <div key={cat} className="rounded-lg border border-neutral-200 dark:border-neutral-800 overflow-hidden">
                    <div className="px-3 py-2 bg-neutral-50 dark:bg-neutral-900 flex items-center justify-between">
                      <div className="text-sm font-medium">{cat}</div>
                      <div className="text-xs opacity-60">{catItems.length} runs</div>
                    </div>
                    <div className="p-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                      {catItems.map((r) => (<RunCard key={r.id} r={r} onDelete={handleDeleteRun} />))}
                    </div>
                  </div>
                ))}
              </div>
            )
          })()
        )}
      </div>
      {showModal && <NewRunModal onClose={() => { setShowModal(false); fetchRuns(); navigate('/runs', { replace: true }) }} />}
    </div>
  )
}

function RunCard({ r, onDelete }: { r: RunItem, onDelete: (id: string) => void | Promise<void> }) {
  const statusCls =
    r.status === 'completed' ? 'bg-green-100 text-green-800' :
    r.status === 'failed' ? 'bg-red-100 text-red-800' :
    r.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
    'bg-gray-100 text-gray-800'
  return (
    <a href={`/runs/${r.id}`} className="group block rounded-md border border-neutral-200 dark:border-neutral-800 p-3 hover:shadow-sm transition duration-200 fade-in-up">
      <div className="flex items-center justify-between">
        <div className="font-mono text-xs text-blue-600 group-hover:underline">{r.id}</div>
        <div className="flex items-center gap-2">
          <button
            title="Excluir run"
            className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-950"
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(r.id) }}
          >
            <Trash2 className="h-4 w-4 text-red-600" />
          </button>
          <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${statusCls}`}>{r.status}</span>
        </div>
      </div>
      <div className="mt-2 text-sm font-medium">{r.engine}</div>
      <div className="mt-1 text-xs opacity-70">
        <span>Início: {r.started_at || '-'}</span>
        {r.finished_at ? <span> • Fim: {r.finished_at}</span> : null}
      </div>
      <div className="mt-2 flex items-center gap-3 text-xs">
        <span>ZCRS: {r.zcrs?.toFixed(1) ?? '-'}</span>
        <span>Tokens: {typeof r.tokens_total === 'number' ? formatNumberCompact(r.tokens_total) : '-'}</span>
        <span>Custo: {typeof r.cost_usd === 'number' ? `$${r.cost_usd.toFixed(4)}` : '-'}</span>
      </div>
      {r.template_name && (
        <div className="mt-2 text-[11px] opacity-70 truncate">{r.template_name}</div>
      )}
    </a>
  )
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
  const [allTemplates, setAllTemplates] = useState<Template[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [categories, setCategories] = useState<string[]>([])
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
    getProjects().then((r) => {
      setProjects(r)
      if (!projectId && r[0]?.id) setProjectId(r[0].id)
    })
  }, [])

  useEffect(() => {
    if (!projectId) return
    getSubprojects(projectId).then((r) => setSubprojects(r))
    // Fetch all templates (unfiltered) for the selected project/theme to derive categories and allow client-side filtering
    getTemplates(projectId, undefined, subprojectId || undefined).then((r) => {
      setAllTemplates(r)
      setTemplates(category ? r.filter((t: Template) => t.category === category) : r)
      const cats = Array.from(new Set(r.map((t: Template) => t.category))).sort()
      setCategories(cats)
    })
  }, [projectId, subprojectId])

  // Update visible templates when category changes
  useEffect(() => {
    setTemplates(category ? allTemplates.filter((t: Template) => t.category === category) : allTemplates)
  }, [category, allTemplates])

  // Ensure selected template index is valid when the list changes (e.g., after filtering by category)
  useEffect(() => {
    if (templateIdx >= templates.length) setTemplateIdx(0)
  }, [templates, templateIdx])

  const createQuickProject = async () => {
    const res = await createProject({ name: newProjectName, country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
    const id = res.id as string
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
        const promptRes = await createPrompt(projectId, {
          name: `Prompt custom (${new Date().toISOString()})`,
          text: customPrompt,
          intent: 'Ad-hoc',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.id as string
        const versions = await getPromptVersions(promptId)
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
        await createRun({
          project_id: projectId,
          prompt_version_id: pvId,
          engines: [{ name: engine.name, region: 'BR', device: 'desktop', config_json: cfg }],
          cycles,
          subproject_id: subprojectId || null,
        })
      } else if (templates.length) {
        const t = templates[templateIdx]
        const promptRes = await createPrompt(projectId, {
          name: `Template: ${t.name}`,
          text: t.text,
          intent: 'Informacional',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.id as string
        const versions = await getPromptVersions(promptId)
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
        const subprojectToUse = subprojectId || t.subproject_id || null
        await createRun({
          project_id: projectId,
          prompt_version_id: pvId,
          engines: [{ name: engine.name, region: 'BR', device: 'desktop', config_json: cfg }],
          cycles,
          subproject_id: subprojectToUse,
        })
      } else {
        const promptRes = await createPrompt(projectId, {
          name: `Template: ${TEMPLATES[templateIdx].label}`,
          text: TEMPLATES[templateIdx].text,
          intent: 'Informacional',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.id as string
        const versions = await getPromptVersions(promptId)
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
        await createRun({
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
            <div className="text-sm text-neutral-500">Tema (opcional)</div>
            <Select value={subprojectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSubprojectId(e.target.value)}>
              <option value="">—</option>
              {subprojects.map((s: Subproject) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
          </label>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Categoria de Template</div>
            <Select value={category} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setCategory(e.target.value)}>
              <option value="">—</option>
              {categories.map((c: string) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </Select>
          </label>
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
