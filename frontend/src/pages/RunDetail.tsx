import React, { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import { Button } from '../components/ui/button'
import { Toaster, toast } from 'sonner'
import { Search, Bot, Camera, Globe } from 'lucide-react'

const API = '/api'

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
  model_name?: string
  tokens_input?: number
  tokens_output?: number
  tokens_total?: number
  cost_usd?: number
  latency_ms?: number
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
  const esRef = useRef<EventSource | null>(null)
  const pollRef = useRef<number | null>(null)
  const lastTsRef = useRef<string | null>(null)
  const [hasLiveEvents, setHasLiveEvents] = useState(false)
  const [titles, setTitles] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!id) return
    const fetchAll = async () => {
      try {
        const [r1, r2, r4] = await Promise.all([
          axios.get(`${API}/runs/${id}/report`).catch(() => null),
          axios.get(`${API}/runs/${id}/evidences`).catch(() => null),
          axios.get(`${API}/runs/${id}`).catch(() => null),
        ])
        if (r1?.data) setReport(r1.data)
        if (r2?.data) setEvidences(r2.data)
        if (r4?.data) {
          setDetail(r4.data)
          const cfg = r4.data.engine?.config_json || {}
          setUseSearch(cfg.use_search !== false)
        }
      } catch {}
    }
    fetchAll()
  }, [id])

  useEffect(() => {
    const loadTitles = async () => {
      if (!report?.citations) return
      const urls = Array.from(new Set(report.citations.map(c => c.url).filter(Boolean))) as string[]
      const entries = await Promise.all(urls.map(async (u) => {
        try { const r = await axios.get(`/api/utils/url-title`, { params: { url: u } }); return [u, r.data.title] as const } catch { return [u, u] as const }
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
    const es = new EventSource(`${API}/runs/${id}/stream`)
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        setHasLiveEvents(true)
        setEvents((prev) => [...prev, data])
        lastTsRef.current = data.created_at
        if (data.step === 'chunk' && typeof data.message === 'string') {
          setStreamText((t) => (t ? t + '\n' : '') + data.message)
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
          const res = await axios.get(`${API}/runs/${id}/events`)
          const list = (res.data as EventItem[])
          // se temos lastTs, só anexar novos
          const news = lastTsRef.current ? list.filter(ev => ev.created_at > (lastTsRef.current as string)) : list
          if (news.length) {
            setEvents((prev) => [...prev, ...news])
            lastTsRef.current = news[news.length - 1].created_at
            const chunk = news.find(n => n.step === 'chunk' && typeof n.message === 'string')
            if (chunk?.message) setStreamText((t) => (t ? t + '\n' : '') + chunk.message)
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
      await axios.post(`${API}/runs`, {
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

  const md = streamText || evidences?.[0]?.parsed_json?.parsed?.text || ''

  return (
    <div className="space-y-4">
      <Toaster richColors position="top-right" />
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Run {id}</h1>
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
          {typeof detail?.tokens_total === 'number' && <Card title="Tokens" value={detail.tokens_total} />}        
        </div>
      )}

      <div>
        <Toolbelt events={events} />
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Progresso</h2>
        <div className="flex flex-col gap-1">
          {events.length === 0 && !hasLiveEvents && <div className="text-sm opacity-70">Aguardando eventos…</div>}
          {events.map((e, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className={`h-2 w-2 rounded-full ${e.status==='ok'?'bg-green-500':e.status==='started'?'bg-blue-500':'bg-red-500'}`} />
              <span className="font-mono opacity-70">{new Date(e.created_at).toLocaleTimeString()}</span>
              <span className="px-2 py-0.5 rounded-md border border-neutral-600">{e.step}</span>
              {e.message && <span className="opacity-80 truncate">{e.message}</span>}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-medium">Citações</h2>
        <div className="grid gap-2">
          {report?.citations.map((c, i) => (
            <a key={i} href={c.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 p-2 border rounded-md">
              <img src={getFavicon(c.url)} alt="" className="h-4 w-4" />
              <span className="truncate flex-1">{titles[c.url || ''] || c.url}</span>
              {c.is_ours && <span className="text-xs px-2 py-0.5 border rounded-md">nosso</span>}
            </a>
          )) || <div>Nenhuma citação</div>}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-medium">Resposta (stream)</h2>
        <article className="prose prose-invert max-w-none bg-neutral-50 dark:bg-neutral-900 p-3 rounded-md border border-neutral-200 dark:border-neutral-800">
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
            <Card title="Tokens (in)" value={typeof detail.tokens_input === 'number' ? detail.tokens_input : '-'} />
            <Card title="Tokens (out)" value={typeof detail.tokens_output === 'number' ? detail.tokens_output : '-'} />
            <Card title="Tokens (total)" value={typeof detail.tokens_total === 'number' ? detail.tokens_total : '-'} />
          </div>
        </section>
      )}
      <div className="flex gap-2 justify-end">
        <Button onClick={() => copyAs('md')} className="px-2 py-1 border rounded-md text-xs">Copiar Markdown</Button>
        <Button onClick={() => copyAs('html')} className="px-2 py-1 border rounded-md text-xs">Copiar HTML</Button>
      </div>
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
