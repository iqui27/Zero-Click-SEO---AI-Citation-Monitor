// @ts-nocheck
import * as React from 'react'
import { Sparkles, Loader2, CheckCircle2, XCircle } from 'lucide-react'

type RefItem = { title?: string; link?: string; url?: string; snippet?: string }
type Organic = { title?: string; link?: string; displayed_link?: string; snippet?: string }

export function AiOverview({
  source,
  ai,
  organics,
  runId,
  projectId,
  promptVersionId,
  engineName,
  subprojectId,
}: {
  source?: string
  ai?: { text_blocks?: any[]; references?: RefItem[] } | null
  organics?: Organic[] | null
  runId?: string
  projectId?: string
  promptVersionId?: string
  engineName?: string
  subprojectId?: string
}) {
  const initialHasAi = !!(source && source.startsWith('serpapi_ai'))
  const API = '/api'
  const [creating, setCreating] = React.useState(false)
  const [linkedRunId, setLinkedRunId] = React.useState<string | null>(null)
  const [linkedStatus, setLinkedStatus] = React.useState<'queued'|'running'|'completed'|'failed'|null>(null)
  const [aiState, setAiState] = React.useState<any | null>(ai || null)
  const [organicsState, setOrganicsState] = React.useState<any[] | null>(organics || null)
  const [hasAi, setHasAi] = React.useState<boolean>(initialHasAi)
  const [blocks, setBlocks] = React.useState<any[]>(ai?.text_blocks || [])
  const [refs, setRefs] = React.useState<RefItem[]>(ai?.references || [])

  const loadFromLinked = React.useCallback(async (rid: string) => {
    try {
      // status
      const d = await fetch(`${API}/runs/${rid}`).then(r => r.json())
      setLinkedStatus(d.status as any)
      // evidences
      const evs = await fetch(`${API}/runs/${rid}/evidences`).then(r => r.json())
      const raw = evs?.[0]?.parsed_json?.raw || {}
      const src = 'serpapi_ai_linked'
      const aiData = raw?.serpapi_ai || null
      const organicsData = raw?.serpapi?.organic_results || raw?.serpapi_search?.organic_results || []
      setAiState(aiData)
      setOrganicsState(organicsData)
      setHasAi(!!aiData)
      setBlocks(aiData?.text_blocks || [])
      setRefs(aiData?.references || [])
    } catch {}
  }, [])

  const runAiOverview = async () => {
    if (!projectId || !promptVersionId || !runId) return
    setCreating(true)
    try {
      const region = 'BR'
      const device = 'desktop'
      const res = await fetch(`${API}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          prompt_version_id: promptVersionId,
          subproject_id: subprojectId || null,
          engines: [{ name: 'google_serp', region, device, config_json: { use_serpapi: true, serpapi_ai_overview: true, serpapi_no_cache: false } }],
          cycles: 1,
        }),
      })
      const created = await res.json()
      const targetId = created?.[0]?.id
      if (targetId) {
        await fetch(`${API}/runs/${runId}/link-ai-overview`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_run_id: targetId }),
        })
        setLinkedRunId(targetId)
        setLinkedStatus('queued')
        // Poll status until completed/failed
        const poll = async () => {
          try {
            const d = await fetch(`${API}/runs/${targetId}`).then(r => r.json())
            setLinkedStatus(d.status as any)
            if (d.status === 'completed' || d.status === 'failed') {
              await loadFromLinked(targetId)
              return
            }
          } catch {}
          setTimeout(poll, 1200)
        }
        poll()
      }
    } finally {
      setCreating(false)
    }
  }

  // On mount: if not google_serp, try to discover linked run and load
  React.useEffect(() => {
    let cancelled = false
    const init = async () => {
      try {
        if (engineName === 'google_serp') return
        if (!runId) return
        const res = await fetch(`${API}/runs/${runId}/ai-overview-source`).then(r => r.json())
        const rid = res?.run_id
        if (rid && !cancelled) {
          setLinkedRunId(rid)
          await loadFromLinked(rid)
        }
      } catch {}
    }
    init()
    return () => { cancelled = true }
  }, [runId, engineName, loadFromLinked])

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-medium flex-1">AI Overview</h2>
        {engineName !== 'google_serp' && (
          linkedRunId ? (
            <div className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm border ${linkedStatus==='failed' ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200' : linkedStatus==='completed' ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-200' : 'border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-200'}`}>
              {linkedStatus==='failed' ? <XCircle className="h-4 w-4" /> : linkedStatus==='completed' ? <CheckCircle2 className="h-4 w-4" /> : <Loader2 className="h-4 w-4 animate-spin" />}
              <a href={`/runs/${linkedRunId}`} className="underline">{linkedStatus==='completed' ? 'AI Overview pronto' : linkedStatus==='failed' ? 'Falhou' : 'Rodando AI Overview…'}</a>
            </div>
          ) : (
            <button
              onClick={runAiOverview}
              disabled={creating}
              className="relative inline-flex items-center rounded-full p-[2px] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 disabled:opacity-60 disabled:cursor-not-allowed group"
            >
              <span className="absolute inset-0 rounded-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-fuchsia-500 opacity-90 transition-opacity group-hover:opacity-100" aria-hidden />
              <span className="relative inline-flex items-center gap-2 rounded-full bg-white dark:bg-neutral-950 px-4 py-2 text-sm font-medium shadow-sm">
                <Sparkles className="h-4 w-4 text-cyan-500" />
                <span className="bg-gradient-to-r from-cyan-700 to-fuchsia-700 bg-clip-text text-transparent">
                  {creating ? 'Criando…' : 'Rodar AI Overview'}
                </span>
              </span>
            </button>
          )
        )}
      </div>
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
        {!hasAi && (
          <div className="px-3 py-2 text-xs border-b border-neutral-200 dark:border-neutral-800 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300">
            AI Overview não está disponível para esta consulta. Exibindo resultados orgânicos.
          </div>
        )}

        <div className="p-3 grid gap-3">
          {hasAi ? (
            <div className="grid gap-2">
              {renderBlocks(blocks)}
              {!!refs.length && (
                <div className="pt-2 border-t border-neutral-200 dark:border-neutral-800">
                  <div className="text-xs font-medium opacity-70 mb-1">Referências</div>
                  <ul className="grid gap-1">
                    {refs.slice(0, 20).map((r, i) => (
                      <li key={i} className="text-sm truncate">
                        <a className="text-blue-600 hover:underline" href={r.link || r.url} target="_blank" rel="noreferrer">
                          {r.title || r.link || r.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="grid gap-2">
              <div className="text-sm opacity-70">Resultados orgânicos</div>
              <ul className="grid gap-1">
                {(organicsState || organics || []).slice(0, 10).map((o: any, i: number) => (
                  <li key={i} className="text-sm">
                    <a className="text-blue-600 hover:underline" href={o.link} target="_blank" rel="noreferrer">
                      {o.title || o.link}
                    </a>
                    {o.displayed_link && (
                      <span className="ml-2 text-xs opacity-60">{o.displayed_link}</span>
                    )}
                    {o.snippet && (
                      <div className="text-xs opacity-70 truncate">{o.snippet}</div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function renderBlocks(list: any[]): React.ReactNode {
  if (!Array.isArray(list) || !list.length) return null
  return list.map((b, idx) => (
    <div key={idx} className="grid gap-1">
      {b.type === 'heading' && (
        <h3 className="text-base font-semibold leading-snug">{b.snippet}</h3>
      )}
      {b.type === 'paragraph' && (
        <p className="text-sm leading-relaxed opacity-90">{b.snippet}</p>
      )}
      {b.type === 'list' && (
        <div className="grid gap-1">
          {Array.isArray(b.list) && (
            <ul className="list-disc ml-5 space-y-1">
              {b.list.map((li: any, i: number) => (
                <li key={i} className="text-sm">
                  <span className="font-medium">{li.title}</span>
                  {li.snippet && <span className="opacity-90"> {li.snippet}</span>}
                  {Array.isArray(li.list) && (
                    <ul className="list-[circle] ml-5 space-y-1 mt-1">
                      {li.list.map((sub: any, j: number) => (
                        <li key={j} className="text-sm opacity-90">{sub.snippet}</li>
                      ))}
                    </ul>
                  )}
                  {Array.isArray(li.text_blocks) && (
                    <div className="ml-2 mt-1 grid gap-1">{renderBlocks(li.text_blocks)}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {b.type === 'expandable' && (
        <details className="rounded-md border border-neutral-200 dark:border-neutral-800">
          <summary className="px-2 py-1 cursor-pointer text-sm font-medium">{b.title || 'Detalhes'}</summary>
          <div className="p-2 grid gap-1">{renderBlocks(b.text_blocks || [])}</div>
        </details>
      )}
      {b.type === 'comparison' && Array.isArray(b.comparison) && (
        <div className="overflow-auto">
          <table className="min-w-full sm:min-w-[480px] text-sm border border-neutral-200 dark:border-neutral-800 rounded-md">
            <thead>
              <tr>
                <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-800">Recurso</th>
                {(b.product_labels || []).map((pl: string, i: number) => (
                  <th key={i} className="text-left p-2 border-b border-neutral-200 dark:border-neutral-800">{pl}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {b.comparison.map((row: any, i: number) => (
                <tr key={i} className="border-t border-neutral-200 dark:border-neutral-800">
                  <td className="p-2 font-medium">{row.feature}</td>
                  {(row.values || []).map((v: any, j: number) => (
                    <td key={j} className="p-2">{String(v)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {Array.isArray(b.text_blocks) && b.type !== 'expandable' && (
        <div className="grid gap-1">{renderBlocks(b.text_blocks)}</div>
      )}
    </div>
  ))
}


