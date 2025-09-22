import React, { useState } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Select } from '../components/ui/select'
import { sandboxTest, SandboxResponse, listOpenAIModels } from '../lib/api'

export default function SandboxPage() {
  const [engine, setEngine] = useState<'openai'|'gemini'|'perplexity'|'google_serp'|'sandbox'>('openai')
  const [model, setModel] = useState<string>('gpt-5-mini')
  const [prompt, setPrompt] = useState<string>('Diga apenas: TESTE OK. Liste 2 fontes (http) no final.')
  const [language, setLanguage] = useState<string>('pt-BR')
  const [region, setRegion] = useState<string>('BR')
  const [device, setDevice] = useState<string>('desktop')
  const [timeout, setTimeout] = useState<number>(30)
  const [org, setOrg] = useState<string>('')
  const [project, setProject] = useState<string>('')
  const [useWebSearch, setUseWebSearch] = useState<boolean>(true)
  const [reasoningEffort, setReasoningEffort] = useState<'low'|'medium'|'high'>('low')
  // OpenAI Web Search specific
  const [toolChoice, setToolChoice] = useState<'auto'|'force_tool'|'disabled'>('auto')
  const [searchContextSize, setSearchContextSize] = useState<'low'|'medium'|'high'>('low')
  const [locCountry, setLocCountry] = useState<string>('')
  const [locRegion, setLocRegion] = useState<string>('')
  const [locCity, setLocCity] = useState<string>('')
  const [maxOutputTokens, setMaxOutputTokens] = useState<number>(8192)
  // Gemini grounding options
  const [gemDynThreshold, setGemDynThreshold] = useState<number>(0.7)
  const [gemMaxOutputTokens, setGemMaxOutputTokens] = useState<number>(9000)
  const [gemForceSearch, setGemForceSearch] = useState<boolean>(false)
  // Perplexity tuning
  const [pplxTemp, setPplxTemp] = useState<number>(0.2)
  const [pplxTopP, setPplxTopP] = useState<number>(0.9)
  const [pplxMaxTokens, setPplxMaxTokens] = useState<number>(1024)
  const [pplxMode, setPplxMode] = useState<'web'|'academic'>('web')
  const [pplxRecency, setPplxRecency] = useState<string>('')
  const [pplxAllowDomains, setPplxAllowDomains] = useState<string>('')
  const [pplxDenyDomains, setPplxDenyDomains] = useState<string>('')
  const [pplxReturnImages, setPplxReturnImages] = useState<boolean>(false)
  const [pplxReturnRelated, setPplxReturnRelated] = useState<boolean>(false)
  // Google SERP options
  const [serpUseApi, setSerpUseApi] = useState<boolean>(true)
  const [serpPreferAIO, setSerpPreferAIO] = useState<boolean>(true)
  const [serpNoCache, setSerpNoCache] = useState<boolean>(false)
  const [serpAiMode, setSerpAiMode] = useState<boolean>(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<SandboxResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showFull, setShowFull] = useState<boolean>(false)
  // OpenAI models listing
  const [openaiModels, setOpenaiModels] = useState<string[]>([])
  const [listBusy, setListBusy] = useState<boolean>(false)
  const [listErr, setListErr] = useState<string | null>(null)

  // Popular models per engine
  const OPENAI_MODELS = ['gpt-5-mini','gpt-5','gpt-4o-mini','gpt-4o','gpt-4.1','gpt-4.1-mini']
  const GEMINI_MODELS = ['gemini-2.5-pro','gemini-2.5-flash','gemini-1.5-pro','gemini-1.5-flash','gemini-1.5-flash-8b']
  const PPLX_MODELS = ['sonar-pro','sonar','sonar-reasoning','sonar-small']

  function defaultModelFor(e: typeof engine): string {
    switch (e) {
      case 'openai': return 'gpt-5-mini'
      case 'gemini': return 'gemini-2.5-pro'
      case 'perplexity': return 'sonar-pro'
      case 'google_serp': return ''
      case 'sandbox': return ''
      default: return ''
    }
  }

  function modelListFor(e: typeof engine): string[] {
    switch (e) {
      case 'openai': return openaiModels.length ? openaiModels : OPENAI_MODELS
      case 'gemini': return GEMINI_MODELS
      case 'perplexity': return PPLX_MODELS
      default: return []
    }
  }

  // Switch default model when engine changes
  React.useEffect(() => {
    const list = modelListFor(engine)
    const def = defaultModelFor(engine)
    if (!list.length) {
      setModel('')
    } else if (!list.includes(model)) {
      setModel(def)
    }
  }, [engine])

  React.useEffect(() => {
    if (engine === 'openai' && openaiModels.length) {
      if (!openaiModels.includes(model)) setModel(openaiModels[0])
    }
  }, [openaiModels, engine])

  async function loadOpenAIModels() {
    setListBusy(true); setListErr(null)
    try {
      const data = await listOpenAIModels({ org: org || undefined, project: project || undefined })
      if (!data.ok) {
        setListErr(data.error || 'Falha ao listar modelos')
        setOpenaiModels([])
        return
      }
      const ids = (data.ids || []).filter(Boolean)
      setOpenaiModels(ids)
      // Ajustar modelo atual se não estiver na lista retornada
      if (ids.length && !ids.includes(model)) setModel(ids[0])
    } catch (e: any) {
      setListErr(e?.message || String(e))
      setOpenaiModels([])
    } finally {
      setListBusy(false)
    }
  }

  const run = async () => {
    setBusy(true); setError(null); setResult(null)
    try {
      let config: Record<string, any> = {}
      if (engine === 'openai') {
        const user_location = (locCountry || locRegion || locCity)
          ? { type: 'approximate', country: locCountry || undefined, region: locRegion || undefined, city: locCity || undefined }
          : undefined
        config = {
          organization: org || undefined,
          project: project || undefined,
          web_search: useWebSearch,
          reasoning_effort: reasoningEffort,
          search_context_size: searchContextSize,
          user_location,
          max_output_tokens: maxOutputTokens,
        }
        if (toolChoice === 'force_tool') config.web_search_force = true
        if (toolChoice === 'auto') config.web_search_tool_choice = 'auto'
        if (toolChoice === 'disabled') config.web_search = false
      } else if (engine === 'gemini') {
        config = {
          use_search: useWebSearch,
          max_output_tokens: gemMaxOutputTokens,
          dynamic_retrieval: { mode: 'MODE_DYNAMIC', dynamic_threshold: gemDynThreshold },
          force_search: gemForceSearch,
        }
      } else if (engine === 'perplexity') {
        config = {
          temperature: pplxTemp,
          top_p: pplxTopP,
          max_tokens: pplxMaxTokens,
          search_mode: pplxMode,
        }
        if (pplxRecency) config.search_recency_filter = pplxRecency
        const includes = pplxAllowDomains.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
        const excludes = pplxDenyDomains.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
        if (includes.length || excludes.length) {
          config.search_domain_filter = { include: includes.length ? includes : undefined, exclude: excludes.length ? excludes : undefined }
        }
        if (pplxReturnImages) config.return_images = true
        if (pplxReturnRelated) config.return_related_questions = true
      } else if (engine === 'google_serp') {
        config = {
          use_serpapi: serpUseApi,
          serpapi_ai_overview: serpPreferAIO,
          serpapi_ai_mode: serpAiMode,
          serpapi_no_cache: serpNoCache,
        }
      }
      const data = await sandboxTest({ engine, prompt, model, language, region, device, timeout_seconds: timeout, config })
      setResult(data)
      if (!data.ok && data.error) setError(data.error)
    } catch (e: any) {
      setError(e?.message || String(e))
    } finally {
      setBusy(false)
      setShowFull(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Sandbox de Engines</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-3 p-3 border rounded-md">
          <div className="grid gap-2">
            <Label>Engine</Label>
            <select className="border rounded-md px-2 py-1" value={engine} onChange={e => setEngine(e.target.value as any)}>
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
              <option value="perplexity">Perplexity</option>
              <option value="google_serp">Google SERP</option>
              <option value="sandbox">Sandbox (fixture)</option>
            </select>
          </div>
          <div className="grid gap-2">
            <Label>Modelo</Label>
            {engine === 'openai' || engine === 'gemini' || engine === 'perplexity' ? (
              <select className="border rounded-md px-2 py-1" value={model} onChange={e => setModel(e.target.value)}>
                {modelListFor(engine).map(m => (<option key={m} value={m}>{m}</option>))}
              </select>
            ) : (
              <Input value={model} onChange={e => setModel(e.target.value)} placeholder="(não aplicável)" />
            )}
            {engine === 'openai' && (
              <div className="flex items-center gap-3 text-xs">
                <button type="button" className="px-2 py-1 border rounded-md" onClick={loadOpenAIModels} disabled={listBusy}>
                  {listBusy ? 'Listando…' : 'Listar modelos (OpenAI)'}
                </button>
                {openaiModels.length > 0 && <span>{openaiModels.length} modelos encontrados</span>}
                {listErr && <span className="text-red-600">{listErr}</span>}
              </div>
            )}
          </div>
          <div className="grid gap-2">
            <Label>Prompt</Label>
            <textarea className="border rounded-md p-2 min-h-[120px]" value={prompt} onChange={e => setPrompt(e.target.value)} />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="grid gap-2">
              <Label>Idioma</Label>
              <Input value={language} onChange={e => setLanguage(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label>Região</Label>
              <Input value={region} onChange={e => setRegion(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label>Dispositivo</Label>
              <Input value={device} onChange={e => setDevice(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-2">
              <Label>Organization (OpenAI)</Label>
              <Input placeholder="org_xxx (opcional)" value={org} onChange={e => setOrg(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label>Project (OpenAI)</Label>
              <Input placeholder="proj_xxx (opcional)" value={project} onChange={e => setProject(e.target.value)} />
            </div>
          </div>
          {/* Engine-specific advanced controls */}
          {engine === 'openai' && (
            <>
              <div className="grid grid-cols-3 gap-2">
                <div className="flex items-center gap-2">
                  <input id="ws" type="checkbox" checked={useWebSearch} onChange={e => setUseWebSearch(e.target.checked)} />
                  <Label htmlFor="ws">Web Search (web_search_preview)</Label>
                </div>
                <div className="grid gap-1">
                  <Label>Tool choice</Label>
                  <select className="border rounded-md px-2 py-1" value={toolChoice} onChange={e => setToolChoice(e.target.value as any)}>
                    <option value="auto">auto</option>
                    <option value="force_tool">force web_search_preview</option>
                    <option value="disabled">disabled</option>
                  </select>
                </div>
                <div className="grid gap-1">
                  <Label>Reasoning effort</Label>
                  <select className="border rounded-md px-2 py-1" value={reasoningEffort} onChange={e => setReasoningEffort(e.target.value as any)}>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="grid gap-1">
                  <Label>Search context size</Label>
                  <select className="border rounded-md px-2 py-1" value={searchContextSize} onChange={e => setSearchContextSize(e.target.value as any)}>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </div>
                <div className="grid gap-1">
                  <Label>Max output tokens</Label>
                  <Input type="number" min={256} max={32000} value={maxOutputTokens} onChange={e => setMaxOutputTokens(parseInt(e.target.value||'8192', 10))} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="grid gap-1">
                  <Label>País</Label>
                  <Input placeholder="BR" value={locCountry} onChange={e => setLocCountry(e.target.value)} />
                </div>
                <div className="grid gap-1">
                  <Label>Estado/Região</Label>
                  <Input placeholder="SP" value={locRegion} onChange={e => setLocRegion(e.target.value)} />
                </div>
                <div className="grid gap-1">
                  <Label>Cidade</Label>
                  <Input placeholder="São Paulo" value={locCity} onChange={e => setLocCity(e.target.value)} />
                </div>
              </div>
            </>
          )}

          {engine === 'gemini' && (
            <>
              <div className="grid grid-cols-3 gap-2">
                <div className="flex items-center gap-2">
                  <input id="gws" type="checkbox" checked={useWebSearch} onChange={e => setUseWebSearch(e.target.checked)} />
                  <Label htmlFor="gws">Usar Google Search grounding</Label>
                </div>
                <div className="grid gap-1">
                  <Label>Dynamic threshold</Label>
                  <Input type="number" step="0.05" min={0} max={1} value={gemDynThreshold} onChange={e => setGemDynThreshold(parseFloat(e.target.value||'0.7'))} />
                </div>
                <div className="grid gap-1">
                  <Label>Max output tokens</Label>
                  <Input type="number" min={256} max={32000} value={gemMaxOutputTokens} onChange={e => setGemMaxOutputTokens(parseInt(e.target.value||'9000', 10))} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="flex items-center gap-2">
                  <input id="gforce" type="checkbox" checked={gemForceSearch} onChange={e => setGemForceSearch(e.target.checked)} />
                  <Label htmlFor="gforce">Force search (usar retrieval se necessário)</Label>
                </div>
              </div>
            </>
          )}

          {engine === 'perplexity' && (
            <>
              <div className="grid grid-cols-3 gap-2">
                <div className="grid gap-1">
                  <Label>Temperature</Label>
                  <Input type="number" step="0.05" min={0} max={2} value={pplxTemp} onChange={e => setPplxTemp(parseFloat(e.target.value||'0.2'))} />
                </div>
                <div className="grid gap-1">
                  <Label>Top P</Label>
                  <Input type="number" step="0.05" min={0} max={1} value={pplxTopP} onChange={e => setPplxTopP(parseFloat(e.target.value||'0.9'))} />
                </div>
                <div className="grid gap-1">
                  <Label>Max tokens</Label>
                  <Input type="number" min={128} max={8000} value={pplxMaxTokens} onChange={e => setPplxMaxTokens(parseInt(e.target.value||'1024', 10))} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="grid gap-1">
                  <Label>Search mode</Label>
                  <select className="border rounded-md px-2 py-1" value={pplxMode} onChange={e => setPplxMode(e.target.value as any)}>
                    <option value="web">web</option>
                    <option value="academic">academic</option>
                  </select>
                </div>
                <div className="grid gap-1">
                  <Label>Recency filter</Label>
                  <Input placeholder="e.g. week, month, year" value={pplxRecency} onChange={e => setPplxRecency(e.target.value)} />
                </div>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={pplxReturnImages} onChange={e => setPplxReturnImages(e.target.checked)} /> return_images</label>
                  <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={pplxReturnRelated} onChange={e => setPplxReturnRelated(e.target.checked)} /> return_related_questions</label>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="grid gap-1">
                  <Label>Allowlist domains (comma ou quebra de linha)</Label>
                  <textarea className="border rounded-md p-2 min-h-[90px]" value={pplxAllowDomains} onChange={e => setPplxAllowDomains(e.target.value)} />
                </div>
                <div className="grid gap-1">
                  <Label>Denylist domains (comma ou quebra de linha)</Label>
                  <textarea className="border rounded-md p-2 min-h-[90px]" value={pplxDenyDomains} onChange={e => setPplxDenyDomains(e.target.value)} />
                </div>
              </div>
              <div className="text-xs opacity-70">Perplexity já realiza web-search e retorna citations/search_results quando disponíveis.</div>
            </>
          )}

          {engine === 'google_serp' && (
            <>
              <div className="grid grid-cols-3 gap-2">
                <div className="flex items-center gap-2">
                  <input id="serpapi" type="checkbox" checked={serpUseApi} onChange={e => setSerpUseApi(e.target.checked)} />
                  <Label htmlFor="serpapi">Usar SerpApi</Label>
                </div>
                <div className="flex items-center gap-2">
                  <input id="aio" type="checkbox" checked={serpPreferAIO} onChange={e => setSerpPreferAIO(e.target.checked)} />
                  <Label htmlFor="aio">Preferir AI Overview</Label>
                </div>
                <div className="flex items-center gap-2">
                  <input id="nc" type="checkbox" checked={serpNoCache} onChange={e => setSerpNoCache(e.target.checked)} />
                  <Label htmlFor="nc">SerpApi no_cache</Label>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="flex items-center gap-2">
                  <input id="aimode" type="checkbox" checked={serpAiMode} onChange={e => setSerpAiMode(e.target.checked)} />
                  <Label htmlFor="aimode">Google AI Mode (engine=google_ai_mode)</Label>
                </div>
              </div>
              <div className="text-xs opacity-70">Com AI Overview, as citações vêm de references[]. Sem AI Overview, usamos organic_results como fallback.</div>
            </>
          )}
          <div className="grid gap-2">
            <Label>Timeout (s)</Label>
            <Input type="number" min={5} max={120} value={timeout} onChange={e => setTimeout(parseInt(e.target.value||'30',10))} />
          </div>
          <Button onClick={run} disabled={busy}>{busy ? 'Executando...' : 'Executar teste'}</Button>
        </div>
        <div className="space-y-3 p-3 border rounded-md">
          <h2 className="font-semibold">Resultado</h2>
          {error && <div className="text-sm text-red-600 whitespace-pre-wrap">{error}</div>}
          {result && (
            <div className="space-y-2 text-sm">
              <div><b>Status:</b> {String(result.ok)}</div>
              <div><b>Engine:</b> {result.engine} | <b>Modelo:</b> {result.model || '(n/d)'} | <b>Tempo:</b> {result.timing_ms} ms</div>
              <div>
                <div className="flex items-center justify-between">
                  <b>Texto:</b>
                  {result.truncated && (
                    <div className="text-xs flex items-center gap-3">
                      <span className="opacity-70">Preview truncado</span>
                      <button type="button" className="px-2 py-1 border rounded-md" onClick={() => setShowFull(v => !v)}>
                        {showFull ? 'Mostrar preview' : 'Mostrar texto completo'}
                      </button>
                    </div>
                  )}
                </div>
                <pre className="whitespace-pre-wrap text-xs bg-neutral-50 dark:bg-neutral-900 p-2 rounded-md border max-h-[260px] overflow-auto">{showFull ? (result.text || '') : (result.text_preview || '')}</pre>
              </div>
              <div>
                <b>Links ({(result.links||[]).length}):</b>
                <ul className="list-disc pl-4">
                  {(result.links||[]).map((l, i) => (
                    <li key={i}><a className="text-blue-600" href={l.url} target="_blank" rel="noreferrer">{l.url}</a>{l.title ? ` — ${l.title}` : ''}</li>
                  ))}
                </ul>
              </div>
              <div><b>Web search:</b> used={String(result.web_search_used)} calls={result.web_search_calls}</div>
              <div>
                <b>Usage:</b> input={result as any && (result as any).usage ? (result as any).usage.input_tokens : '—'} | output={(result as any && (result as any).usage ? (result as any).usage.output_tokens : '—')} | total={(result as any && (result as any).usage ? (result as any).usage.total_tokens : '—')}
              </div>
              <div>
                <b>Max output tokens (cfg):</b> {(result as any).config_max_output_tokens ?? '—'}
              </div>
              <div><b>Raw keys:</b> {(result.raw_keys||[]).join(', ')}</div>
              <div><b>Output types:</b> {(result.output_types||[]).join(', ')}</div>
              {!!result.request && (
                <div>
                  <b>Request (diag):</b>
                  <pre className="whitespace-pre-wrap text-xs bg-neutral-50 dark:bg-neutral-900 p-2 rounded-md border max-h-[220px] overflow-auto">{JSON.stringify(result.request, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
