// @ts-nocheck
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getRun, getRunReport, getRunEvidences, getRunEvents, createRun, getUrlTitle, openRunStream } from '../lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import { Button } from '../components/ui/button'
import { formatNumberCompact } from '../lib/utils'
import { AiOverview } from '../components/AiOverview'
import { Toaster, toast } from 'sonner'
import { Search, Bot, Camera, Globe } from 'lucide-react'

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
}

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
  const [useSearch, setUseSearch] = useState<boolean>(true)
  const [reprocessing, setReprocessing] = useState(false)
  const [streamText, setStreamText] = useState<string>('')
  const [selectedCycle, setSelectedCycle] = useState<number>(1)
  const esRef = useRef<EventSource | null>(null)
  const pollRef = useRef<number | null>(null)
  const lastTsRef = useRef<string | null>(null)
  const [hasLiveEvents, setHasLiveEvents] = useState(false)
  const [titles, setTitles] = useState<Record<string, string>>({})

  const fetchAllData = async () => {
    if (!id) return
    try {
      const [r1, r2, r4] = await Promise.allSettled([
        getRunReport(id),
        getRunEvidences(id),
        getRun(id),
      ])
      if (r1.status === 'fulfilled' && r1.value) setReport(r1.value)
      if (r2.status === 'fulfilled' && r2.value) setEvidences(r2.value)
      if (r4.status === 'fulfilled' && r4.value) {
        setDetail(r4.value)
        const cfg = r4.value.engine?.config_json || {}
        setUseSearch(cfg.use_search !== false)
      }
    } catch {}
  }

  useEffect(() => {
    fetchAllData()
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
      current.push(e)
      
      const step = (e.step || '').toLowerCase()
      const status = (e.status || '').toLowerCase()
      const nextEvent = list[i + 1]
      
      // Detecta fim de ciclo por:
      // 1. 'completed' com status 'ok'
      // 2. 'error' 
      // 3. 'delay' seguido de 'fetch' (início do próximo ciclo)
      const isEndOfCycle = 
        (step === 'completed' && status === 'ok') ||
        step === 'error' ||
        (step === 'delay' && status === 'ok' && nextEvent && nextEvent.step === 'fetch')
      
      if (isEndOfCycle) {
        buckets.push(current)
        current = []
      }
    }
    
    if (current.length) buckets.push(current)
    
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
    return cyclesBuckets[idx] || []
  }, [cyclesBuckets, selectedCycle, detail?.cycles_total])

  // Deriva markdown do ciclo selecionado a partir de eventos 'chunk'
  const cycleMd: string = useMemo(() => {
    const chunks = eventsForView.filter(e => (e.step || '').toLowerCase() === 'chunk' && typeof e.message === 'string')
    if (!chunks.length) return ''
    return chunks.map(c => c.message as string).join('\n')
  }, [eventsForView])

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

  return (
    <div className="space-y-4">
      <Toaster richColors position="top-right" />
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Run {id}</h1>
        {(detail?.cycles_total || 1) > 1 && (
          <div className="ml-4 flex items-center gap-2 text-sm">
            <span className="opacity-70">Ciclo:</span>
            {/* Segmented control moderno com highlight deslizante */}
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
                {/* Fundo leve */}
                <div aria-hidden className="absolute inset-0 bg-neutral-50/60 dark:bg-neutral-900/40" />
                {/* Destaque móvel */}
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
          <label className="flex items-center gap-2 text-sm ml-auto">
            <input type="checkbox" checked={useSearch} onChange={(e) => setUseSearch(e.target.checked)} />
            Usar web search (experimental)
          </label>
        )}
        <Button onClick={reprocess} disabled={reprocessing || !detail} variant="secondary">{reprocessing ? 'Reprocessando…' : 'Reprocessar'}</Button>
      </div>

      {(report || detail) && (
        <div className="grid lg:grid-cols-5 gap-3">
          {report && <Card title="AMR" value={report.amr.toFixed(2)} />}
          {report && <Card title="DCR" value={report.dcr.toFixed(2)} />}
          {report && <Card title="ZCRS" value={report.zcrs.toFixed(1)} />}
          {typeof detail?.cost_usd === 'number' && <Card title="Custo" value={`$${detail.cost_usd.toFixed(4)}`} />}
          {typeof detail?.tokens_total === 'number' && <Card title="Tokens" value={formatNumberCompact(detail.tokens_total)} />}        
          {typeof detail?.cycles_total === 'number' && <Card title="Ciclos" value={detail.cycles_total} />}
        </div>
      )}

      {/* Badges de meta */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="px-2 py-0.5 border rounded-md">Modelo: {detail?.model_name || detail?.engine?.name || '-'}</span>
        <span className={`px-2 py-0.5 rounded-md border ${wsUsed ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' : 'border-neutral-300 dark:border-neutral-700'}`}>Web search: {wsUsed ? 'on' : 'off'}</span>
        {typeof wsCalls === 'number' && <span className="px-2 py-0.5 border rounded-md">calls: {wsCalls}</span>}
        {ctxSize && <span className="px-2 py-0.5 border rounded-md">ctx: {ctxSize}</span>}
      </div>

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

      {/* Progresso detalhado removido (mantido apenas o bloco minimalista colapsável acima) */}

      {detail?.prompt_text && (
        <section>
          <h2 className="text-lg font-medium">Prompt usado</h2>
          <pre className="whitespace-pre-wrap text-sm p-3 rounded-md border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900">
            {detail.prompt_text}
          </pre>
        </section>
      )}

      {/* AI Overview / Orgânicos (modo Google) — posicionado logo abaixo do Prompt usado */}
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

      <section>
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium flex-1">Resposta (stream)</h2>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="sm" onClick={() => copyAs('md')}>Copiar MD</Button>
            <Button variant="outline" size="sm" onClick={() => copyAs('html')}>Copiar HTML</Button>
          </div>
        </div>
        <article className="prose prose-sm dark:prose-invert max-w-none bg-white dark:bg-neutral-900 p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 overflow-x-hidden">
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
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4">
      <div className="text-xs text-neutral-500">{title}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}
