import React, { useState } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Select } from '../components/ui/select'
import { sandboxTest, SandboxResponse, listOpenAIModels } from '../lib/api'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs'
import SemanticFlowVisualizer from './Sandbox_flow'

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
  const [maxOutputTokens, setMaxOutputTokens] = useState<number>(12000)
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
  const OPENAI_MODELS = [
    'gpt-5-mini',
    'gpt-5',
    'gpt-5-turbo',
    'o5-mini',
    'gpt-4.1-turbo',
    'gpt-4.1',
    'gpt-4o',
    'gpt-4o-mini'
  ]
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

  React.useEffect(() => {
    const lower = (model || '').toLowerCase()
    const isGpt5Family = lower.startsWith('gpt-5') || lower.startsWith('o5')
    if (isGpt5Family) {
      if (reasoningEffort === 'low') setReasoningEffort('medium')
      if (maxOutputTokens < 12000) setMaxOutputTokens(12000)
    }
  }, [model])

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
        const lowerModel = (model || '').toLowerCase()
        const isGpt5Family = lowerModel.startsWith('gpt-5') || lowerModel.startsWith('o5')
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
        if (toolChoice === 'disabled') {
          config.web_search = false
          config.web_search_tool_choice = 'none'
        }
        if (isGpt5Family && config.reasoning_effort === 'low') {
          config.reasoning_effort = 'medium'
        }
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
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold tracking-tight">Sandbox</h1>
      <Tabs defaultValue="engines" className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-2xl">
          <TabsTrigger value="engines">Engines</TabsTrigger>
          <TabsTrigger value="semantic">Insights Simples</TabsTrigger>
          <TabsTrigger value="flow">Pipeline Completo</TabsTrigger>
        </TabsList>
        <TabsContent value="engines" className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4 p-4 border rounded-xl bg-neutral-50/60 dark:bg-neutral-900/60 shadow-sm backdrop-blur-sm transition-colors">
          <div className="grid gap-2">
            <Label>Engine</Label>
            <Select value={engine} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setEngine(e.target.value as any)}>
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
              <option value="perplexity">Perplexity</option>
              <option value="google_serp">Google SERP</option>
              <option value="sandbox">Sandbox (fixture)</option>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label>Modelo</Label>
            {engine === 'openai' || engine === 'gemini' || engine === 'perplexity' ? (
              <Select value={model} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setModel(e.target.value)}>
                {modelListFor(engine).map(m => (<option key={m} value={m}>{m}</option>))}
              </Select>
            ) : (
              <Input value={model} onChange={e => setModel(e.target.value)} placeholder="(não aplicável)" />
            )}
            {engine === 'openai' && (
              <div className="flex items-center gap-3 text-xs">
                <Button type="button" size="sm" variant="outline" onClick={loadOpenAIModels} disabled={listBusy}>
                  {listBusy ? 'Listando…' : 'Listar modelos (OpenAI)'}
                </Button>
                {openaiModels.length > 0 && <span>{openaiModels.length} modelos encontrados</span>}
                {listErr && <span className="text-red-600">{listErr}</span>}
              </div>
            )}
          </div>
          <div className="grid gap-2">
            <Label>Prompt</Label>
            <textarea className="border border-neutral-300 dark:border-neutral-700 rounded-md p-2 min-h-[120px] bg-white dark:bg-neutral-900 placeholder:text-neutral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 dark:focus-visible:ring-neutral-600 transition-colors" value={prompt} onChange={e => setPrompt(e.target.value)} />
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
                  <Select value={toolChoice} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setToolChoice(e.target.value as any)}>
                    <option value="auto">auto</option>
                    <option value="force_tool">force web_search_preview</option>
                    <option value="disabled">disabled</option>
                  </Select>
                </div>
                <div className="grid gap-1">
                  <Label>Reasoning effort</Label>
                  <Select value={reasoningEffort} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setReasoningEffort(e.target.value as any)}>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="grid gap-1">
                  <Label>Search context size</Label>
                  <Select value={searchContextSize} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSearchContextSize(e.target.value as any)}>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </Select>
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
                  <Select value={pplxMode} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setPplxMode(e.target.value as any)}>
                    <option value="web">web</option>
                    <option value="academic">academic</option>
                  </Select>
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
                  <textarea className="border border-neutral-300 dark:border-neutral-700 rounded-md p-2 min-h-[90px] bg-white dark:bg-neutral-900 placeholder:text-neutral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 dark:focus-visible:ring-neutral-600 transition-colors" value={pplxAllowDomains} onChange={e => setPplxAllowDomains(e.target.value)} />
                </div>
                <div className="grid gap-1">
                  <Label>Denylist domains (comma ou quebra de linha)</Label>
                  <textarea className="border border-neutral-300 dark:border-neutral-700 rounded-md p-2 min-h-[90px] bg-white dark:bg-neutral-900 placeholder:text-neutral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 dark:focus-visible:ring-neutral-600 transition-colors" value={pplxDenyDomains} onChange={e => setPplxDenyDomains(e.target.value)} />
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
        <div className="space-y-4 p-4 border rounded-xl bg-neutral-50/60 dark:bg-neutral-900/60 shadow-sm backdrop-blur-sm transition-colors md:sticky md:top-16 h-fit">
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
                      <Button type="button" size="sm" variant="outline" onClick={() => setShowFull(v => !v)}>
                        {showFull ? 'Mostrar preview' : 'Mostrar texto completo'}
                      </Button>
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
        </TabsContent>
        <TabsContent value="semantic" className="space-y-4">
          <SemanticDebugger />
        </TabsContent>
        <TabsContent value="flow" className="space-y-4">
          <SemanticFlowVisualizer />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function SemanticDebugger() {
  const [question, setQuestion] = useState('Como abrir conta digital no BB?')
  const [responseText, setResponseText] = useState('O Banco do Brasil oferece a conta digital com facilidade. Nubank e Inter também têm opções digitais.')
  const [citationsRaw, setCitationsRaw] = useState(`bb.com.br|https://bb.com.br/conta|true
nubank.com.br|https://nubank.com.br/conta|false
inter.com.br|https://inter.com.br|false`)
  const [projectName, setProjectName] = useState('Banco do Brasil')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const analyze = async () => {
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const citations = citationsRaw.split('\n').map(line => {
        const parts = line.split('|')
        return {
          domain: parts[0]?.trim() || '',
          url: parts[1]?.trim() || '',
          is_ours: parts[2]?.trim().toLowerCase() === 'true'
        }
      }).filter(c => c.domain)

      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/debug/semantic-insights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, response_text: responseText, citations, project_name: projectName })
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Erro ao analisar')
      } else {
        setResult(data)
      }
    } catch (e: any) {
      setError(e?.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4 p-4 border rounded-xl bg-neutral-50/60 dark:bg-neutral-900/60 shadow-sm">
        <h2 className="font-semibold text-lg">Input</h2>
        <div className="grid gap-3">
          <div className="grid gap-2">
            <Label>Pergunta</Label>
            <Input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Pergunta/query do usuário" />
          </div>
          <div className="grid gap-2">
            <Label>Resposta (texto plano)</Label>
            <textarea 
              className="border border-neutral-300 dark:border-neutral-700 rounded-md p-2 min-h-[120px] bg-white dark:bg-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400"
              value={responseText}
              onChange={e => setResponseText(e.target.value)}
              placeholder="Texto da resposta da IA"
            />
          </div>
          <div className="grid gap-2">
            <Label>Citações (domain|url|is_ours, uma por linha)</Label>
            <textarea 
              className="border border-neutral-300 dark:border-neutral-700 rounded-md p-2 min-h-[100px] bg-white dark:bg-neutral-900 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400"
              value={citationsRaw}
              onChange={e => setCitationsRaw(e.target.value)}
              placeholder="bb.com.br|https://bb.com.br|true"
            />
          </div>
          <div className="grid gap-2">
            <Label>Nome do Projeto (marca principal)</Label>
            <Input value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="Banco do Brasil" />
          </div>
        </div>
        <Button onClick={analyze} disabled={busy}>{busy ? 'Analisando...' : 'Analisar'}</Button>
      </div>
      <div className="space-y-4 p-4 border rounded-xl bg-neutral-50/60 dark:bg-neutral-900/60 shadow-sm md:sticky md:top-16 h-fit max-h-[calc(100vh-120px)] overflow-auto">
        <h2 className="font-semibold text-lg">Resultado</h2>
        {error && <div className="text-sm text-red-600 whitespace-pre-wrap">{error}</div>}
        {result && (
          <div className="space-y-3">
            <JsonViewer data={result} />
          </div>
        )}
        {!result && !error && (
          <p className="text-sm opacity-70">Preencha os campos e clique em "Analisar" para ver o JSON estruturado.</p>
        )}
      </div>
    </div>
  )
}

function JsonViewer({ data }: { data: any }) {
  const renderValue = (value: any, depth: number = 0): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-neutral-400">null</span>
    }
    if (typeof value === 'boolean') {
      return <span className="text-purple-600 dark:text-purple-400">{String(value)}</span>
    }
    if (typeof value === 'number') {
      return <span className="text-blue-600 dark:text-blue-400">{value}</span>
    }
    if (typeof value === 'string') {
      return <span className="text-green-700 dark:text-green-400">"{value}"</span>
    }
    if (Array.isArray(value)) {
      if (!value.length) return <span className="text-neutral-400">[]</span>
      return (
        <div className="ml-4 space-y-1">
          {value.slice(0, 10).map((item, idx) => (
            <div key={idx} className="flex gap-2">
              <span className="text-neutral-500">{idx}:</span>
              {renderValue(item, depth + 1)}
            </div>
          ))}
          {value.length > 10 && <div className="text-xs opacity-60">... e mais {value.length - 10} itens</div>}
        </div>
      )
    }
    if (typeof value === 'object') {
      const entries = Object.entries(value).slice(0, 50)
      if (!entries.length) return <span className="text-neutral-400">{'{}'}</span>
      return (
        <div className="ml-4 space-y-1 border-l-2 border-neutral-200 dark:border-neutral-700 pl-3">
          {entries.map(([key, val]) => (
            <div key={key} className="flex flex-col gap-0.5">
              <div className="flex items-start gap-2">
                <span className="text-xs font-mono font-semibold text-neutral-600 dark:text-neutral-300 min-w-[120px]">{key}:</span>
                <div className="flex-1">{renderValue(val, depth + 1)}</div>
              </div>
            </div>
          ))}
          {Object.keys(value).length > 50 && <div className="text-xs opacity-60">... e mais {Object.keys(value).length - 50} campos</div>}
        </div>
      )
    }
    return <span>{String(value)}</span>
  }

  return (
    <div className="text-xs font-mono bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-md p-3 overflow-x-auto">
      {renderValue(data)}
    </div>
  )
}
