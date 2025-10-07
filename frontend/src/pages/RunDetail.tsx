// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getRun, getRunReport, getRunEvidences, getRunEvents, createRun, getUrlTitle, openRunStream, getRunSemanticInsights } from '../lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { formatNumberCompact } from '../lib/utils'
import { AiOverview } from '../components/AiOverview'
import { Toaster, toast } from 'sonner'
import { Search, Bot, Camera, Globe, Target, Zap } from 'lucide-react'
import { IMMetricsCard } from '../components/IMMetricsCard'

// API base handled by centralized api.ts

type Citation = { domain: string; url?: string; anchor?: string; type?: string; is_ours: boolean }

type Report = {
  id: string
  amr: number
  dcr: number
  zcrs: number
  citations: Citation[]
}

type Evidence = { id: string; run_id: string; parsed_json: any }

type EventItem = { step: string; status: string; message?: string; created_at: string }

type RunDetail = {
  id: string
  project_id: string
  prompt_version_id: string
  engine: { name: string; region?: string; device?: string; config_json?: any }
  status: string
  started_at?: string
  finished_at?: string
  subproject_id?: string
  prompt_text?: string
  model_name?: string
  tokens_input?: number
  tokens_output?: number
  tokens_total?: number
  cost_usd?: number
  latency_ms?: number
  cycles_total?: number
  cycle_delay_seconds?: number
  // monitor/schedule
  monitor_id?: string
  schedule_date?: string
  schedule_slot?: string
  schedule_index_today?: number
  schedule_total_today?: number
  schedule_source?: 'manual'|'monitor'|'monitor_now'
}

const perceptionLabels: Record<string, string> = {
  inovacao: 'Inovação & tecnologia',
  tradicao: 'Tradição & segurança',
  custo: 'Baixo custo',
  atendimento: 'Atendimento & relacionamento',
}

const STEP_LABELS: Record<string, string> = {
  queued: 'Fila / início',
  opts: 'Configuração efetiva',
  fetch: 'Coleta do motor',
  chunk: 'Texto parcial recebido',
  persist: 'Persistência de evidências',
  extract: 'Extração de citações',
  classify: 'Classificação Zero-Click',
  im_metrics: 'Cálculo IM-SEO / IA',
  search_console: 'Google Search Console',
  post_processing: 'Pós-processamento',
  semantic_insights: 'Insights semânticos',
  completed: 'Conclusão',
  error: 'Erro',
}

const STEP_ORDER = [
  'queued',
  'opts',
  'fetch',
  'chunk',
  'persist',
  'extract',
  'classify',
  'im_metrics',
  'search_console',
  'post_processing',
  'semantic_insights',
  'completed',
  'error',
]

// helper simples para renderizar markdown minimalista
function renderSimpleMarkdown(md: string) {
  const lines = md.split(/\n/)
  return (
    <div className="prose prose-invert max-w-none">
      {lines.map((line, idx) => {
        if (line.startsWith('### ')) return <h3 key={idx}>{line.replace(/^###\s+/, '')}</h3>
        if (line.startsWith('## ')) return <h2 key={idx}>{line.replace(/^##\s+/, '')}</h2>
        if (line.startsWith('* ') || line.startsWith('- ')) return <li key={idx}>{line.replace(/^[-*]\s+/, '')}</li>
        // bold **text**
        const parts = line.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : p))
        return <p key={idx}>{parts}</p>
      })}
    </div>
  )
}

// toolbelt inferido a partir de eventos: search, serp, llm, screenshot
function Toolbelt({ events }: { events: EventItem[] }) {
  const tools = {
    search: 'idle',
    serp: 'idle',
    llm: 'idle',
    screenshot: 'idle',
  } as Record<string, 'idle'|'started'|'ok'|'error'>
  for (const e of events) {
    if (e.step.startsWith('fetch')) tools.llm = e.status as any
    if (e.step === 'extract') tools.search = e.status as any
    if (e.step === 'persist') tools.serp = e.status as any
    if (e.step === 'screenshot') tools.screenshot = e.status as any
  }
  const cls = (s: string) => s==='ok'?'text-green-600':s==='started'?'text-blue-600':s==='error'?'text-red-600':'text-neutral-500'
  return (
    <div className="flex flex-wrap gap-3 text-xs items-center">
      <span className={`flex items-center gap-1 ${cls(tools.llm)}`}><Bot className="h-4 w-4" /> LLM ({tools.llm})</span>
      <span className={`flex items-center gap-1 ${cls(tools.search)}`}><Search className="h-4 w-4" /> Search ({tools.search})</span>
      <span className={`flex items-center gap-1 ${cls(tools.serp)}`}><Globe className="h-4 w-4" /> SERP ({tools.serp})</span>
      <span className={`flex items-center gap-1 ${cls(tools.screenshot)}`}><Camera className="h-4 w-4" /> Screenshot ({tools.screenshot})</span>
    </div>
  )
}

// util favicon
const getFavicon = (url?: string) => {
  try {
    if (!url) return ''
    const u = new URL(url)
    return `https://www.google.com/s2/favicons?domain=${u.hostname}&sz=32`
  } catch { return '' }
}
export default function RunDetail() {
  const { id } = useParams()
  const [report, setReport] = useState<Report | null>(null)
  const [evidences, setEvidences] = useState<Evidence[]>([])
  const [events, setEvents] = useState<EventItem[]>([])
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [streamText, setStreamText] = useState('')
  const [titles, setTitles] = useState<Record<string, string>>({})
  const [reprocessing, setReprocessing] = useState(false)
  const [useSearch, setUseSearch] = useState(false)
  const [selectedCycle, setSelectedCycle] = useState(1)
  const [imMetrics, setImMetrics] = useState<any>(null)
  const [loadingMetrics, setLoadingMetrics] = useState(false)
  const [semantic, setSemantic] = useState<any>(null)
  const esRef = useRef<EventSource | null>(null)
  const pollRef = useRef<number | null>(null)
  const lastTsRef = useRef<string | null>(null)
  const [hasLiveEvents, setHasLiveEvents] = useState(false)

  const fetchAllData = async () => {
    if (!id) return
    try {
      const [r1, r2, r4, r5] = await Promise.allSettled([
        getRunReport(id),
        getRunEvidences(id),
        getRun(id),
        getRunSemanticInsights(id),
      ])
      if (r1.status === 'fulfilled' && r1.value) setReport(r1.value)
      if (r2.status === 'fulfilled' && r2.value) setEvidences(r2.value)
      if (r4.status === 'fulfilled' && r4.value) {
        setDetail(r4.value)
        const cfg = r4.value.engine?.config_json || {}
        setUseSearch(cfg.use_search !== false)
      }
      if (r5.status === 'fulfilled' && r5.value) {
        setSemantic(r5.value)
      }
    } catch (e) {
      console.error('fetchAllData error:', e)
    }
  }

  const fetchIMMetrics = async () => {
    if (!id) return
    setLoadingMetrics(true)
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/runs/${id}/metrics`)
      if (response.ok) {
        const data = await response.json()
        setImMetrics(data)
      }
    } catch (e) {
      console.error('Failed to load IM metrics:', e)
    } finally {
      setLoadingMetrics(false)
    }
  }

  useEffect(() => {
    fetchAllData()
    fetchIMMetrics()
  }, [id])

  useEffect(() => {
    const loadTitles = async () => {
      if (!report?.citations) return
      const urls = Array.from(new Set(report.citations.map(c => c.url).filter(Boolean))) as string[]
      const entries = await Promise.all(urls.map(async (u) => {
        try { const r = await getUrlTitle(u); return [u, r.title] as const } catch { return [u, u] as const }
      }))
      const map: Record<string, string> = {}
      entries.forEach(([u, t]) => map[u] = t)
      setTitles(map)
    }
    loadTitles()
  }, [report?.citations?.length])

  // SSE + fallback polling
  useEffect(() => {
    if (!id) return
    const es = openRunStream(id)
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        setHasLiveEvents(true)
        setEvents((prev) => [...prev, data])
        lastTsRef.current = data.created_at
        if (data.step === 'chunk' && typeof data.message === 'string') {
          setStreamText((t) => (t ? t + '\n' : '') + data.message)
        }
        
        // Auto-refresh citations when cycle completes or run finishes
        const step = (data.step || '').toLowerCase()
        const status = (data.status || '').toLowerCase()
        if ((step === 'extract' && status === 'ok') || 
            (step === 'completed' && status === 'ok') ||
            (step === 'persist' && status === 'ok')) {
          // Delay refresh to ensure backend has processed citations
          setTimeout(() => {
            fetchAllData()
          }, 1500)
        }
      } catch {}
    }
    es.onopen = () => {
      localStorage.setItem('live_mode', 'Live via SSE')
    }
    es.onerror = () => {
      es.close()
      localStorage.setItem('live_mode', 'Live via Polling')
      // fallback polling /events
      if (pollRef.current) return
      const poll = window.setInterval(async () => {
        try {
          const list = await getRunEvents(id)
          // se temos lastTs, só anexar novos
          const news = lastTsRef.current ? list.filter(ev => ev.created_at > (lastTsRef.current as string)) : list
          if (news.length) {
            setEvents((prev) => [...prev, ...news])
            lastTsRef.current = news[news.length - 1].created_at
            const chunk = news.find(n => n.step === 'chunk' && typeof n.message === 'string')
            if (chunk?.message) setStreamText((t) => (t ? t + '\n' : '') + chunk.message)
            
            // Auto-refresh citations when cycle completes or run finishes (polling fallback)
            const shouldRefresh = news.some(event => {
              const step = (event.step || '').toLowerCase()
              const status = (event.status || '').toLowerCase()
              return (step === 'extract' && status === 'ok') || 
                     (step === 'completed' && status === 'ok') ||
                     (step === 'persist' && status === 'ok')
            })
            
            if (shouldRefresh) {
              setTimeout(() => {
                fetchAllData()
              }, 1500)
            }
          }
        } catch {}
      }, 1000)
      pollRef.current = poll
    }
    esRef.current = es
    return () => {
      es.close()
      if (pollRef.current) window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [id])

  const reprocess = async () => {
    if (!detail) return
    setReprocessing(true)
    try {
      const engines = [{
        name: detail.engine.name,
        region: detail.engine.region || 'BR',
        device: detail.engine.device || 'desktop',
        config_json: { ...(detail.engine.config_json || {}), use_search: useSearch },
      }]
      await createRun({
        project_id: detail.project_id,
        prompt_version_id: detail.prompt_version_id,
        engines,
        cycles: 1,
      })
      alert('Nova run criada! Veja em Runs.')
    } catch (e) {
      alert('Erro ao reprocessar: ' + (e as any).message)
    } finally {
      setReprocessing(false)
    }
  }


  const copyAs = (format: 'md'|'html') => {
    const text = streamText || evidences?.[0]?.parsed_json?.parsed?.text || ''
    if (format === 'md') navigator.clipboard.writeText(text)
    else navigator.clipboard.writeText(`<article>\n${text}\n</article>`) // simplificado
    toast.success(format === 'md' ? 'Markdown copiado' : 'HTML copiado')
  }

  // Util
  const getHost = (url?: string) => {
    try { if (!url) return ''; return new URL(url).hostname } catch { return '' }
  }

  // Agrupamento heurístico de eventos por ciclo (melhora detecção de limites entre ciclos)
  const cyclesBuckets: EventItem[][] = useMemo(() => {
    const buckets: EventItem[][] = []
    let current: EventItem[] = []
    const list = [...events]
    
    for (let i = 0; i < list.length; i++) {
      const e = list[i]
      const step = (e.step || '').toLowerCase()
      const status = (e.status || '').toLowerCase()
      const nextEvent = list[i + 1]
      
      // Se é o início de um novo ciclo (fetch após delay), finaliza o ciclo anterior
      if (step === 'fetch' && current.length > 0) {
        const prevEvent = list[i - 1]
        if (prevEvent && (prevEvent.step || '').toLowerCase() === 'delay') {
          buckets.push(current)
          current = []
        }
      }
      
      current.push(e)
      
      // Detecta fim de ciclo por:
      // 1. 'completed' com status 'ok'
      // 2. 'error' 
      // 3. último evento da lista
      const isEndOfCycle = 
        (step === 'completed' && status === 'ok') ||
        step === 'error' ||
        (i === list.length - 1)
      
      if (isEndOfCycle) {
        buckets.push(current)
        current = []
      }
    }
    
    // Ajuste para o número esperado de ciclos, se conhecido
    const total = Math.max(1, detail?.cycles_total || buckets.length || 1)
    if (buckets.length < total) {
      // completa com buckets vazios ao final
      while (buckets.length < total) buckets.push([])
    } else if (buckets.length > total) {
      // se por algum motivo temos mais segmentos que ciclos, mescla excedentes no último
      const head = buckets.slice(0, total - 1)
      const tailMerged = buckets.slice(total - 1).flat()
      return [...head, tailMerged]
    }
    
    console.log(`Cycles detected: ${buckets.length}, expected: ${total}`)
    buckets.forEach((bucket, i) => {
      const chunks = bucket.filter(e => e.step === 'chunk').length
      console.log(`Cycle ${i + 1}: ${bucket.length} events, ${chunks} chunks`)
    })
    
    return buckets
  }, [events, detail?.cycles_total])
  // Garantir que o ciclo selecionado esteja sempre dentro do intervalo válido
  useEffect(() => {
    const total = Math.max(1, detail?.cycles_total || cyclesBuckets.length || 1)
    if (selectedCycle > total) setSelectedCycle(total)
    if (selectedCycle < 1) setSelectedCycle(1)
  }, [detail?.cycles_total, cyclesBuckets.length])
  const eventsForView: EventItem[] = useMemo(() => {
    const totalCycles = detail?.cycles_total || cyclesBuckets.length || 1
    const idx = Math.max(0, Math.min(totalCycles - 1, selectedCycle - 1))
    const cycleEvents = cyclesBuckets[idx] || []
    console.log(`Cycle ${selectedCycle} (idx ${idx}): ${cycleEvents.length} events`)
    return cycleEvents
  }, [cyclesBuckets, selectedCycle, detail?.cycles_total, events.length])

  // Deriva markdown do ciclo selecionado a partir de eventos 'chunk'
  const cycleMd: string = useMemo(() => {
    const chunks = eventsForView.filter(e => (e.step || '').toLowerCase() === 'chunk' && typeof e.message === 'string')
    if (!chunks.length) return ''
    return chunks.map(c => c.message as string).join('\n')
  }, [eventsForView, selectedCycle, events.length])

  const md = cycleMd || streamText || evidences?.[0]?.parsed_json?.parsed?.text || ''

  const meta = (evidences?.[0]?.parsed_json?.parsed?.meta) || {}
  // Para Gemini, o default é usar web search, então se não houver flags, considerar true
  const wsUsed = (() => {
    const fromMeta = meta?.web_search_used
    if (typeof fromMeta === 'boolean') return fromMeta
    const cfg = detail?.engine?.config_json || {}
    const engineName = detail?.engine?.name || ''
    if ((engineName || '').toLowerCase() === 'gemini') {
      if (typeof cfg.use_search === 'boolean') return cfg.use_search
      if (typeof cfg.web_search === 'boolean') return cfg.web_search
      return true
    }
    return Boolean(cfg.web_search)
  })()
  const wsCalls = meta?.web_search_calls
  const ctxSize = meta?.search_context_size ?? detail?.engine?.config_json?.search_context_size

  // Queries executadas pelo web_search (debug/auditoria)
  const output = evidences?.[0]?.parsed_json?.raw?.response?.output || []
  const webQueries: string[] = []
  try {
    for (const item of output || []) {
      if (item?.type === 'web_search_call' && item?.action?.query) {
        webQueries.push(item.action.query as string)
      }
    }
  } catch {}

  const semanticPayload = semantic?.payload || null
  const semanticPerception = semanticPayload?.perception || {}
  const normalizeName = (value?: string | null) =>
    (value || '')
      .normalize('NFD')
      .replace(/\p{Diacritic}/gu, '')
      .replace(/[^\w\s-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase()

  const primaryProjectName = (() => {
    if (!detail?.project_name) return null
    const [left] = detail.project_name.split('–')
    const cleaned = left.replace(/^projeto\s+/i, '').trim()
    return cleaned || detail.project_name
  })()

  const semanticSummaryText = semantic?.semantic_summary || semanticPayload?.summary?.headline || ''
  const semanticPerceptionPrimary = semanticPerception?.primary_category || semantic?.perceived_value_category || null
  const semanticPerceptionSecondary = Array.isArray(semanticPerception?.secondary_categories)
    ? semanticPerception.secondary_categories.filter(Boolean)
    : []
  const semanticSummaryBullets = Array.isArray(semanticPayload?.summary?.bullets)
    ? semanticPayload.summary.bullets.slice(0, 4)
    : []
  const semanticEntities = Array.isArray(semanticPayload?.entities) ? semanticPayload?.entities : []
  const brandNameSet = new Set<string>(
    semanticEntities
      .filter((entity: any) => Array.isArray(entity?.roles) && entity.roles.some((role: string) => role.toLowerCase() === 'brand'))
      .map((entity: any) => normalizeName(entity?.name))
      .filter(Boolean)
  )
  if (primaryProjectName) {
    brandNameSet.add(normalizeName(primaryProjectName))
  }

  const brandAliases = Array.from(brandNameSet).filter(Boolean)
  const isPrimaryBrand = (value?: string | null) => {
    const normalized = normalizeName(value || '')
    if (!normalized) return false
    if (brandNameSet.has(normalized)) return true
    return brandAliases.some((brand) => {
      if (!brand) return false
      return normalized.includes(brand) || brand.includes(normalized)
    })
  }

  const semanticBrandEntities = semanticEntities
    .filter((entity: any) => {
      const roles = Array.isArray(entity?.roles) ? entity.roles.map((r: string) => (r || '').toLowerCase()) : []
      const category = (entity?.category || '').toLowerCase()
      return roles.includes('brand') || roles.includes('competitor') || category === 'brand'
    })
    .slice(0, 6)

  const semanticCompetitorsList = Array.isArray(semanticPayload?.competitors)
    ? semanticPayload.competitors
        .filter((item: any) => !isPrimaryBrand(item?.name))
        .slice(0, 6)
    : []
  const derivedCompetitors = semanticEntities
    .filter((entity: any) => {
      if (!Array.isArray(entity?.roles)) return false
      const rolesLower = entity.roles.map((role: string) => (role || '').toLowerCase())
      if (!rolesLower.includes('competitor')) return false
      return !isPrimaryBrand(entity?.name)
    })
    .slice(0, 6)
  const semanticKeywords = Array.isArray(semanticPayload?.keywords)
    ? semanticPayload.keywords.slice(0, 12)
    : []
  const competitorsToShow = semanticCompetitorsList.length ? semanticCompetitorsList : derivedCompetitors
  const maxKeywordWeight = Math.max(1, ...semanticKeywords.map((kw: any) => (kw?.weight || 0) > 0 ? kw.weight : 0.5))
  const semanticUpdatedAt = semantic?.updated_at ? new Date(semantic.updated_at).toLocaleString() : null

  const statusBadgeLabel = detail?.status === 'post_processing' ? 'post-processing' : (detail?.status || '—')
  const statusBadgeTone = detail?.status === 'completed'
    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300'
    : detail?.status === 'failed'
      ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300'
      : detail?.status === 'running'
        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300'
        : detail?.status === 'post_processing'
          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300 animate-pulse'
          : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300'

  const categoryValue = detail?.prompt_template_category || detail?.prompt_category || detail?.prompt_intent || null
  const headerChips = [
    detail?.project_name ? { label: 'Projeto', value: detail.project_name } : null,
    detail?.subproject_name ? { label: 'Tema', value: detail.subproject_name } : null,
    categoryValue ? { label: 'Categoria', value: categoryValue } : null,
  ].filter(Boolean)

  const quickStats = [
    typeof report?.amr === 'number' ? { label: 'AMR', value: report.amr.toFixed(2) } : null,
    typeof report?.dcr === 'number' ? { label: 'DCR', value: report.dcr.toFixed(2) } : null,
    typeof report?.zcrs === 'number' ? { label: 'ZCRS', value: report.zcrs.toFixed(1) } : null,
    typeof detail?.cost_usd === 'number' ? { label: 'Custo', value: `$${detail.cost_usd.toFixed(4)}` } : null,
    typeof detail?.tokens_total === 'number' ? { label: 'Tokens', value: formatNumberCompact(detail.tokens_total) } : null,
    typeof detail?.cycles_total === 'number' ? { label: 'Ciclos', value: String(detail.cycles_total) } : null,
  ].filter(Boolean)

  const timeline = useMemo(() => {
    const sorted = [...events].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
    const grouped = new Map<string, EventItem[]>()
    for (const ev of sorted) {
      if (!ev.step) continue
      const step = ev.step
      if (step === 'chunk') continue
      if (!grouped.has(step)) grouped.set(step, [])
      grouped.get(step)!.push(ev)
    }
    const items = Array.from(grouped.entries()).map(([step, evs]) => ({
      step,
      first: evs[0],
      last: evs[evs.length - 1],
      events: evs,
    }))
    items.sort((a, b) => {
      const ai = STEP_ORDER.indexOf(a.step)
      const bi = STEP_ORDER.indexOf(b.step)
      if (ai !== -1 && bi !== -1 && ai !== bi) return ai - bi
      return new Date(a.first.created_at).getTime() - new Date(b.first.created_at).getTime()
    })
    return items
  }, [events])

  const statusChip = (status: string) => {
    if (status === 'ok') return 'text-green-600'
    if (status === 'fail' || status === 'error') return 'text-red-600'
    if (status === 'started' || status === 'queued') return 'text-blue-600'
    if (status === 'timeout') return 'text-orange-600'
    return 'text-neutral-500'
  }

  return (
    <div className="space-y-6">
      <Toaster richColors position="top-right" />
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-semibold tracking-tight">{id}</h1>
            {detail?.status && (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusBadgeTone}`}>
                {statusBadgeLabel}
              </span>
            )}
            {detail?.status === 'post_processing' && !detail?.finished_at && (
              <span className="text-xs flex items-center gap-1 text-amber-600 dark:text-amber-300">
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping" aria-hidden />
                Aguardando insights semânticos
              </span>
            )}
          </div>

          {headerChips.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {headerChips.map((chip, idx) => (
                <span
                  key={`${chip.label}-${chip.value}-${idx}`}
                  className="inline-flex flex-col justify-center gap-0.5 px-3 py-1 rounded-md border border-neutral-300 dark:border-neutral-700 bg-neutral-50/80 dark:bg-neutral-900/60 text-xs"
                >
                  <span className="uppercase tracking-wide text-[10px] text-neutral-500">{chip.label}</span>
                  <span className="text-sm font-medium text-neutral-800 dark:text-neutral-100">{chip.value}</span>
                </span>
              ))}
            </div>
          )}

          {quickStats.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {quickStats.map((stat, idx) => (
                <span
                  key={`${stat.label}-${idx}`}
                  className="px-2 py-0.5 rounded-md border border-neutral-200 dark:border-neutral-700 bg-white/80 dark:bg-neutral-900/50 flex items-center gap-1"
                >
                  <span className="uppercase tracking-wide text-[10px] text-neutral-500">{stat.label}</span>
                  <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{stat.value}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          {(detail?.cycles_total || 1) > 1 && (
            <div className="flex items-center gap-2 text-sm">
              <span className="opacity-70">Ciclo:</span>
              <div className="relative">
                <div
                  role="tablist"
                  aria-label="Selecionar ciclo"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'ArrowRight') {
                      setSelectedCycle((c) => Math.min(c + 1, detail?.cycles_total || 1))
                    } else if (e.key === 'ArrowLeft') {
                      setSelectedCycle((c) => Math.max(1, c - 1))
                    }
                  }}
                  className="relative isolate grid h-8 rounded-md overflow-hidden border border-neutral-300 dark:border-neutral-700"
                  style={{ gridTemplateColumns: `repeat(${detail?.cycles_total || 1}, minmax(0, 1fr))` }}
                >
                  <div aria-hidden className="absolute inset-0 bg-neutral-50/60 dark:bg-neutral-900/40" />
                  <div
                    aria-hidden
                    className="absolute inset-y-0 left-0 pointer-events-none rounded-md bg-gradient-to-r from-red-500 to-red-600 dark:from-red-600 dark:to-red-700 shadow-md transition-transform duration-300"
                    style={{ width: `calc(100% / ${(detail?.cycles_total || 1)})`, transform: `translateX(${(selectedCycle - 1) * 100}%)` }}
                  />
                  {Array.from({ length: detail?.cycles_total || 1 }, (_, i) => i + 1).map((n) => {
                    const active = selectedCycle === n
                    return (
                      <button
                        key={n}
                        role="tab"
                        aria-selected={active}
                        className={`relative z-10 text-xs sm:text-sm px-3 text-center font-medium transition-colors duration-200 ${active ? 'text-white' : 'text-neutral-700 dark:text-neutral-200 hover:text-neutral-900 dark:hover:text-neutral-100'}`}
                        onClick={() => setSelectedCycle(n)}
                      >
                        #{n}
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
          {detail?.engine?.name?.startsWith('gemini') && (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={useSearch} onChange={(e) => setUseSearch(e.target.checked)} />
              Usar web search (experimental)
            </label>
          )}
          <Button onClick={reprocess} disabled={reprocessing || !detail} variant="secondary">{reprocessing ? 'Reprocessando…' : 'Reprocessar'}</Button>
        </div>
      </div>

      <section className="border border-neutral-200 dark:border-neutral-800 rounded-lg bg-neutral-50/60 dark:bg-neutral-900/60 p-4 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-600 dark:text-neutral-300">Prompt utilizado</h2>
            {detail?.prompt_name && (
              <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">{detail.prompt_name}</p>
            )}
            {detail?.prompt_category && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Geral: {detail.prompt_category}</p>
            )}
          </div>
          {detail?.prompt_id && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded border border-neutral-300 dark:border-neutral-700 bg-white/70 dark:bg-neutral-900/50">
              {detail.prompt_id}
            </span>
          )}
        </div>
        <pre className="whitespace-pre-wrap text-sm leading-relaxed bg-white/70 dark:bg-neutral-950/60 border border-neutral-200 dark:border-neutral-800 rounded-md p-3">
          {detail?.prompt_text || 'Prompt não disponível.'}
        </pre>
      </section>

      {/* Badges de meta */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="px-2 py-0.5 border rounded-md">Modelo: {detail?.model_name || detail?.engine?.name || '-'}</span>
        <span className={`px-2 py-0.5 rounded-md border ${wsUsed ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' : 'border-neutral-300 dark:border-neutral-700'}`}>Web search: {wsUsed ? 'on' : 'off'}</span>
        {typeof wsCalls === 'number' && <span className="px-2 py-0.5 border rounded-md">calls: {wsCalls}</span>}
        {ctxSize && <span className="px-2 py-0.5 border rounded-md">ctx: {ctxSize}</span>}
        {semantic?.perceived_value_category && (
          <span className="px-2 py-0.5 rounded-md border border-blue-300 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-200">
            Valor: {perceptionLabels[semantic.perceived_value_category] || semantic.perceived_value_category}
          </span>
        )}
        {/* Schedule/Monitor badges */}
        {detail?.monitor_id && (
          <span className="px-2 py-0.5 rounded-md border border-purple-300 dark:border-purple-800 text-purple-700 dark:text-purple-300">Monitor</span>
        )}
        {detail?.schedule_source && (
          <span className="px-2 py-0.5 rounded-md border">fonte: {detail.schedule_source}</span>
        )}
        {(detail?.schedule_date || detail?.schedule_slot) && (
          <span className="px-2 py-0.5 rounded-md border">{detail?.schedule_date ? new Date(detail.schedule_date).toISOString().slice(0,10) : ''}{detail?.schedule_slot ? ` • ${detail.schedule_slot}` : ''}</span>
        )}
        {(typeof detail?.schedule_index_today === 'number' && typeof detail?.schedule_total_today === 'number') && (
          <span className="px-2 py-0.5 rounded-md border">{detail?.schedule_index_today}/{detail?.schedule_total_today}</span>
        )}
      </div>

      <section>
        <div className="flex flex-wrap items-start gap-3 mb-3">
          <div className="flex-1">
            <h2 className="text-lg font-medium">Insights semânticos</h2>
            <p className="text-xs text-muted-foreground">
              Entidades, keywords e percepção extraídos do AI Overview via Gemini.
            </p>
          </div>
          {semanticUpdatedAt && (
            <span className="text-xs text-muted-foreground">Atualizado em {semanticUpdatedAt}</span>
          )}
        </div>
        {semanticPayload ? (
          <div className="grid gap-4 md:grid-cols-3">
            <div className="border rounded-lg p-4 bg-neutral-50/60 dark:bg-neutral-900/60 space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold">Resumo executivo</h3>
                {semanticPerception?.confidence && (
                  <Badge variant="secondary" className="text-xs">
                    confiança {(semanticPerception.confidence * 100).toFixed(0)}%
                  </Badge>
                )}
              </div>
              {semanticSummaryText ? (
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{semanticSummaryText}</p>
              ) : (
                <p className="text-sm opacity-70">Sem resumo disponível.</p>
              )}
              {semanticSummaryBullets.length > 0 && (
                <ul className="list-disc pl-4 text-xs space-y-1">
                  {semanticSummaryBullets.map((bullet, idx) => (
                    <li key={idx}>{bullet}</li>
                  ))}
                </ul>
              )}
            </div>
            <div className="border rounded-lg p-4 bg-neutral-50/60 dark:bg-neutral-900/60 space-y-3">
              <div className="flex items-center gap-2 justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold">Marcas &amp; percepção</h3>
                  {semanticPerceptionPrimary && (
                    <Badge variant="outline" className="capitalize text-xs">
                      {perceptionLabels[semanticPerceptionPrimary] || semanticPerceptionPrimary}
                    </Badge>
                  )}
                </div>
                {semanticPerceptionSecondary.length > 0 && (
                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    +{semanticPerceptionSecondary.length} categorias
                  </span>
                )}
              </div>
              {semanticBrandEntities.length ? (
                <div className="flex flex-wrap gap-2">
                  {semanticBrandEntities.map((entity: any, idx: number) => {
                    const roles = Array.isArray(entity?.roles) ? entity.roles.filter(Boolean).slice(0, 2) : []
                    return (
                      <span
                        key={`${entity.name || idx}`}
                        className="px-2.5 py-1 rounded-full border border-neutral-300 dark:border-neutral-700 text-xs bg-white/80 dark:bg-neutral-900/70 flex items-center gap-1"
                      >
                        <span>{entity.name || '—'}</span>
                        {roles.length > 0 && (
                          <span className="text-[10px] uppercase tracking-wide opacity-60">{roles.join('/')}</span>
                        )}
                      </span>
                    )
                  })}
                </div>
              ) : (
                <div className="text-sm opacity-70">Nenhuma entidade reconhecida como marca ou concorrente.</div>
              )}
              {competitorsToShow.length > 0 && (
                <div>
                  <h4 className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Concorrentes</h4>
                  <ul className="space-y-1 text-xs">
                    {competitorsToShow.map((competitor: any, idx: number) => (
                      <li key={`${competitor.name || idx}`} className="flex items-center justify-between">
                        <span>{competitor.name || '—'}</span>
                        {competitor.mentions && (
                          <span className="text-muted-foreground">{competitor.mentions} menc.</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <div className="border rounded-lg p-4 bg-neutral-50/60 dark:bg-neutral-900/60 space-y-3">
              <h3 className="text-sm font-semibold">Palavras-chave</h3>
              {semanticKeywords.length ? (
                <div className="flex flex-wrap gap-2">
                  {semanticKeywords.map((kw: any) => {
                    const norm = Math.max(0.25, (kw.weight || 0.5) / maxKeywordWeight)
                    const fontSize = 0.85 + norm * 1.2
                    return (
                      <span
                        key={kw.token}
                        className="rounded-full px-2 py-1 bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-50"
                        style={{ fontSize: `${fontSize}rem`, opacity: 0.6 + norm * 0.4 }}
                        title={`Marcas: ${kw.brands?.join(', ') || '—'}${kw.competitors?.length ? ` | Concorrentes: ${kw.competitors.join(', ')}` : ''}`}
                      >
                        {kw.token}
                      </span>
                    )
                  })}
                </div>
              ) : (
                <div className="text-sm opacity-70">Sem palavras-chave relevantes.</div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-sm opacity-70 border rounded-lg p-6 text-center">
            Insights semânticos ainda não disponíveis para esta run.
          </div>
        )}
      </section>

      <section className="grid gap-2">
        <Toolbelt events={eventsForView.length ? eventsForView : events} />
        {/* Opções efetivas (badges) */}
        {(() => {
          const last = events.filter(e => e.step === 'opts').slice(-1)[0]
          if (!last?.message) return null
          let obj: any = null
          try { obj = JSON.parse(last.message) } catch {}
          if (!obj || typeof obj !== 'object') return null
          const entries = Object.entries(obj as Record<string, any>)
          if (!entries.length) return null
          return (
            <div className="text-xs flex flex-wrap items-center gap-1">
              {entries.map(([k, v]) => {
                const str = v === null ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v)
                const tone = (typeof v === 'boolean') ? (v ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' : 'bg-neutral-50 dark:bg-neutral-900/30 border-neutral-300 dark:border-neutral-700') : 'bg-neutral-50 dark:bg-neutral-900/30 border-neutral-300 dark:border-neutral-700'
                return (
                  <span key={k} className={`px-2 py-0.5 rounded-md border ${tone}`}>{k}: <span className="font-medium">{str}</span></span>
                )
              })}
            </div>
          )
        })()}

        {/* Progresso minimalista (colapsável) */}
        <details className="rounded-md border border-neutral-200 dark:border-neutral-800">
          <summary className="text-xs px-2 py-1 cursor-pointer select-none">Progresso ({(eventsForView.length || events.length)})</summary>
          <div className="p-2 grid gap-1 text-xs">
            {(eventsForView.length ? eventsForView : events).slice(-8).map((e, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className={`h-1.5 w-1.5 rounded-full ${e.status==='ok'?'bg-green-500':e.status==='started'?'bg-blue-500':'bg-red-500'}`} />
                <span className="font-mono opacity-70">{new Date(e.created_at).toLocaleTimeString()}</span>
                <span className="px-1.5 py-0.5 rounded border border-neutral-300 dark:border-neutral-700">{e.step}</span>
                {e.message && e.step !== 'chunk' && <span className="opacity-70 truncate">{e.message}</span>}
              </div>
            ))}
            {!!webQueries.length && (
              <div className="mt-1">
                <div className="font-medium mb-1">Web search – queries ({webQueries.length})</div>
                <ul className="list-disc pl-5 space-y-0.5">
                  {webQueries.slice(-6).map((q, i) => (<li key={i} className="truncate">{q}</li>))}
                </ul>
              </div>
            )}
          </div>
        </details>
      </section>

      <section className="border border-neutral-200 dark:border-neutral-800 rounded-md p-3">
        <h2 className="text-sm font-semibold mb-2">Linha do tempo</h2>
        {timeline.length ? (
          <ol className="space-y-2 text-xs">
            {timeline.map(({ step, first, last, events }) => {
              const label = STEP_LABELS[step] || step
              const status = last?.status || first?.status || 'ok'
              const message = last?.message || first?.message || ''
              const time = last ? new Date(last.created_at).toLocaleTimeString() : ''
              return (
                <li key={`${step}-${first?.created_at || ''}`} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-3 border-l-2 border-neutral-200 dark:border-neutral-700 pl-3">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${status === 'ok' ? 'bg-green-500' : status === 'fail' || status === 'error' ? 'bg-red-500' : status === 'post_processing' ? 'bg-amber-500' : 'bg-blue-500'}`} />
                    <div>
                      <div className="font-medium capitalize">{label}</div>
                      {message && <div className="opacity-70 max-w-xs truncate" title={message}>{message}</div>}
                      {events.length > 1 && (
                        <div className="opacity-50">{events.length} eventos</div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {time && <span className="font-mono opacity-70">{time}</span>}
                    <span className={`px-1.5 py-0.5 rounded border border-neutral-300 dark:border-neutral-700 ${statusChip(status)}`}>
                      {status}
                    </span>
                  </div>
                </li>
              )
            })}
          </ol>
        ) : (
          <p className="text-xs opacity-70">Nenhum evento registrado ainda.</p>
        )}
      </section>

      {/* AI Overview / Orgânicos (modo Google) — posicionado logo abaixo do Prompt */}
      <section>
        {(() => {
          const raw = evidences?.[0]?.parsed_json?.raw || {}
          const source = meta?.source as string | undefined
          const ai = (raw?.serpapi_ai || null)
          const organics = (raw?.serpapi?.organic_results || raw?.serpapi_search?.organic_results || [])
          return (
            <AiOverview
              source={source}
              ai={ai}
              organics={organics}
              runId={id}
              projectId={detail?.project_id}
              promptVersionId={detail?.prompt_version_id}
              engineName={detail?.engine?.name}
              subprojectId={detail?.subproject_id}
            />
          )
        })()}
      </section>

      <section>
        <h2 className="text-lg font-medium">Citações</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {(report?.citations || []).map((c, i) => (
            <a key={i} href={c.url} target="_blank" rel="noreferrer" className="group p-3 border rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-900/40 transition-colors">
              <div className="flex items-start gap-2">
                <img src={getFavicon(c.url)} alt="" className="h-4 w-4 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium truncate group-hover:underline">{titles[c.url || ''] || c.url}</div>
                  <div className="text-xs opacity-60 truncate">{getHost(c.url)}</div>
                </div>
                {c.is_ours && <span className="text-[10px] px-2 py-0.5 rounded-full border border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300">nosso</span>}
              </div>
            </a>
          ))}
          {!report?.citations?.length && (
            <div className="text-sm opacity-70 border rounded-lg p-4">Nenhuma citação.</div>
          )}
        </div>
      </section>

      {/* Métricas IM-SEO e IM-SEOIA */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-purple-600" />
            <h2 className="text-lg font-medium">Métricas IM-SEO & IM-SEOIA</h2>
          </div>
          <Zap className="h-4 w-4 text-blue-500" />
        </div>
        {loadingMetrics ? (
          <div className="text-sm opacity-70 border rounded-lg p-8 text-center">
            Carregando métricas...
          </div>
        ) : imMetrics ? (
          <IMMetricsCard metrics={imMetrics} />
        ) : (
          <div className="text-sm opacity-70 border rounded-lg p-8 text-center">
            <p className="mb-2">Métricas IM não disponíveis para esta run.</p>
            <p className="text-xs">As métricas são calculadas automaticamente em novas runs.</p>
          </div>
        )}
      </section>

      <section>
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium flex-1">Resposta (stream)</h2>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="sm" onClick={() => copyAs('md')}>Copiar MD</Button>
            <Button variant="outline" size="sm" onClick={() => copyAs('html')}>Copiar HTML</Button>
          </div>
        </div>
        <article className="prose prose-sm dark:prose-invert max-w-none bg-white dark:bg-neutral-900 p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 overflow-x-auto">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>{md}</ReactMarkdown>
        </article>
      </section>
      {detail && (
        <section>
          <h2 className="text-lg font-medium">Custos e Métricas</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <Card title="Modelo" value={detail.model_name || detail.engine?.name} />
            <Card title="Latência" value={typeof detail.latency_ms === 'number' ? `${detail.latency_ms} ms` : '-'} />
            <Card title="Custo" value={typeof detail.cost_usd === 'number' ? `$${detail.cost_usd.toFixed(4)}` : '-'} />
            <Card title="Tokens (in)" value={typeof detail.tokens_input === 'number' ? formatNumberCompact(detail.tokens_input) : '-'} />
            <Card title="Tokens (out)" value={typeof detail.tokens_output === 'number' ? formatNumberCompact(detail.tokens_output) : '-'} />
            <Card title="Tokens (total)" value={typeof detail.tokens_total === 'number' ? formatNumberCompact(detail.tokens_total) : '-'} />
            <Card title="Ciclos" value={typeof detail.cycles_total === 'number' ? detail.cycles_total : '-'} />
          </div>
        </section>
      )}
      {/* Removido: botões de cópia duplicados no rodapé para reduzir poluição visual */}
    </div>
  )
}

function Card({ title, value }: { title: string; value: React.ReactNode }) {
  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 bg-neutral-50/60 dark:bg-neutral-900/60 shadow-sm backdrop-blur-sm transition-colors">
      <div className="text-xs text-neutral-500">{title}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}
