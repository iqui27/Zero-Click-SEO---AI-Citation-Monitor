import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Toaster, toast } from 'sonner'

const API = '/api'

type Domain = { id: string; domain: string; pattern_regex?: string; is_primary: boolean }

type Engine = { id: string; name: string; region?: string; device?: string; config_json?: any }

export default function SettingsPage() {
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [domains, setDomains] = useState<Domain[]>([])
  const [engines, setEngines] = useState<Engine[]>([])
  const [newDomain, setNewDomain] = useState('')
  const [pattern, setPattern] = useState('')
  const [isPrimary, setIsPrimary] = useState(false)
  // API Keys
  const [keysStatus, setKeysStatus] = useState<{ has_env: boolean; keys: Record<string, boolean>; sandbox: boolean } | null>(null)
  const [keys, setKeys] = useState({ openai: '', gemini: '', perplexity: '', serpapi: '' })
  const [testing, setTesting] = useState(false)
  const [testResults, setTestResults] = useState<any | null>(null)
  // Create Gemini engine form
  const [newGemini, setNewGemini] = useState({
    model: 'gemini-2.5-flash',
    use_search: true,
    max_output_tokens: 2048,
    dynamic_enabled: true,
    dynamic_mode: 'MODE_DYNAMIC',
    dynamic_threshold: 0.7,
    search_context_size: 'low',
  })

  const refresh = async () => {
    try {
      if (!projectId) return
      const [d, e, st] = await Promise.all([
        axios.get(`${API}/projects/${projectId}/domains`).then(r => r.data),
        axios.get(`${API}/projects/${projectId}/engines`).then(r => r.data),
        axios.get(`${API}/setup/status`).then(r => r.data).catch(() => null),
      ])
      setDomains(d)
      setEngines(e)
      if (st) setKeysStatus(st)
    } catch (e: any) {
      toast.error('Falha ao carregar settings: ' + e.message)
    }
  }
  useEffect(() => { refresh() }, [projectId])

  const saveKeys = async () => {
    try {
      const payload: any = {}
      if (keys.openai) payload.openai_key = keys.openai
      if (keys.gemini) payload.gemini_key = keys.gemini
      if (keys.perplexity) payload.perplexity_key = keys.perplexity
      if (keys.serpapi) payload.serpapi_key = keys.serpapi
      if (Object.keys(payload).length === 0) {
        toast.info('Nenhuma chave preenchida')
        return
      }
      await axios.post(`${API}/setup/save-keys`, payload)
      toast.success('Chaves salvas no .env')
      const st = await axios.get(`${API}/setup/status`).then(r => r.data)
      setKeysStatus(st)
    } catch (e: any) {
      toast.error('Falha ao salvar chaves: ' + e.message)
    }
  }

  const testConnections = async () => {
    try {
      setTesting(true)
      const res = await axios.post(`${API}/setup/test-connections`, {
        openai_key: keys.openai || undefined,
        gemini_key: keys.gemini || undefined,
        perplexity_key: keys.perplexity || undefined,
        serpapi_key: keys.serpapi || undefined,
      })
      setTestResults(res.data)
      toast.success('Teste concluído')
    } catch (e: any) {
      toast.error('Falha ao testar conexões: ' + e.message)
    } finally {
      setTesting(false)
    }
  }

  const createGeminiEngine = async () => {
    if (!projectId) { toast.error('Defina o Project ID acima'); return }
    try {
      const cfg: any = { model: newGemini.model, use_search: !!newGemini.use_search }
      if (newGemini.max_output_tokens) cfg.max_output_tokens = Number(newGemini.max_output_tokens)
      if (newGemini.search_context_size) cfg.search_context_size = newGemini.search_context_size
      if (newGemini.dynamic_enabled) {
        cfg.dynamic_retrieval = { mode: newGemini.dynamic_mode, dynamic_threshold: Number(newGemini.dynamic_threshold) }
      }
      const payload = {
        name: 'gemini',
        region: 'BR',
        device: 'desktop',
        config_json: cfg,
      }
      const res = await axios.post(`${API}/projects/${projectId}/engines`, payload)
      toast.success(`Engine Gemini criada: ${res.data.id}`)
      await refresh()
    } catch (e: any) {
      toast.error('Falha ao criar engine: ' + e.message)
    }
  }

  const addDomain = async () => {
    try {
      await axios.post(`${API}/projects/${projectId}/domains`, { domain: newDomain, pattern_regex: pattern || null, is_primary: isPrimary })
      setNewDomain(''); setPattern(''); setIsPrimary(false)
      await refresh()
      toast.success('Domínio adicionado')
    } catch (e: any) {
      toast.error('Falha ao adicionar domínio: ' + e.message)
    }
  }
  const removeDomain = async (id: string) => {
    try {
      await axios.delete(`${API}/domains/${id}`)
      await refresh()
      toast.success('Domínio removido')
    } catch (e: any) {
      toast.error('Falha ao remover domínio: ' + e.message)
    }
  }

  const updateEngine = async (e: Engine, cfg: string) => {
    try {
      await axios.patch(`${API}/engines/${e.id}`, { config_json: JSON.parse(cfg || '{}') })
      await refresh()
      toast.success('Engine atualizada')
    } catch (err: any) {
      toast.error('JSON inválido para config_json')
    }
  }

  return (
    <div className="space-y-4 px-3 sm:px-4 md:px-6 max-w-[1200px] mx-auto">
      <Toaster richColors position="top-right" />
      <h1 className="text-2xl font-semibold">Settings</h1>
      <div className="flex gap-2 items-center">
        <Input placeholder="Project ID" value={projectId} onChange={(e)=>{ setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value) }} />
        <Button variant="secondary" onClick={refresh}>Atualizar</Button>
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Chaves de API</h2>
        <div className="border rounded-md p-3 grid gap-3">
          <div className="grid gap-2 md:grid-cols-2">
            <KeyField label="OpenAI" placeholder="sk-..." value={keys.openai} onChange={(v)=>setKeys(k=>({ ...k, openai: v }))} present={!!keysStatus?.keys?.openai} tested={testResults?.openai} />
            <KeyField label="Gemini (Google)" placeholder="AIza..." value={keys.gemini} onChange={(v)=>setKeys(k=>({ ...k, gemini: v }))} present={!!keysStatus?.keys?.gemini} tested={testResults?.gemini} />
            <KeyField label="Perplexity" placeholder="ppx-..." value={keys.perplexity} onChange={(v)=>setKeys(k=>({ ...k, perplexity: v }))} present={!!keysStatus?.keys?.perplexity} tested={testResults?.perplexity} />
            <KeyField label="SerpAPI" placeholder="api_key" value={keys.serpapi} onChange={(v)=>setKeys(k=>({ ...k, serpapi: v }))} present={!!keysStatus?.keys?.serpapi} tested={testResults?.serpapi} />
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={testConnections} disabled={testing}>{testing ? 'Testando…' : 'Testar conexões'}</Button>
            <Button onClick={saveKeys}>Salvar chaves</Button>
          </div>
          {keysStatus && (
            <div className="text-xs opacity-70">.env: {keysStatus.has_env ? 'detectado' : 'não encontrado'} · Sandbox: {keysStatus.sandbox ? 'on' : 'off'}</div>
          )}
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Domínios alvo</h2>
        <div className="border rounded-md p-3 grid gap-2">
          <div className="grid gap-2 md:grid-cols-4">
            <Input placeholder="domínio (ex.: exemplo.com.br)" value={newDomain} onChange={e=>setNewDomain(e.target.value)} />
            <Input placeholder="regex (opcional)" value={pattern} onChange={e=>setPattern(e.target.value)} />
            <label className="flex items-center gap-2"><input type="checkbox" checked={isPrimary} onChange={e=>setIsPrimary(e.target.checked)} /> Primário</label>
            <div className="flex justify-end"><Button onClick={addDomain}>Adicionar</Button></div>
          </div>
          <div className="grid gap-1">
            {domains.map(d => (
              <div key={d.id} className="flex items-center gap-2 text-sm">
                <span className="flex-1">{d.domain} {d.is_primary ? ' (primário)' : ''}</span>
                <Button variant="outline" size="sm" onClick={()=>removeDomain(d.id)}>Remover</Button>
              </div>
            ))}
            {!domains.length && <div className="text-sm opacity-70">Nenhum domínio cadastrado.</div>}
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Nova Engine Gemini</h2>
        <div className="border rounded-md p-3 grid gap-3 text-sm">
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs opacity-70">Modelo</label>
              <select className="w-full border rounded px-2 py-1 bg-transparent"
                value={newGemini.model}
                onChange={(e)=>setNewGemini(s=>({ ...s, model: e.target.value }))}
              >
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                <option value="gemini-1.5-flash-8b">gemini-1.5-flash-8b</option>
              </select>
            </div>
            <div>
              <label className="text-xs opacity-70">Max output tokens</label>
              <Input type="number" min={128} max={8192} value={newGemini.max_output_tokens}
                onChange={(e)=>setNewGemini(s=>({ ...s, max_output_tokens: Number(e.target.value || 0) }))}
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2"><input type="checkbox" checked={newGemini.use_search} onChange={(e)=>setNewGemini(s=>({ ...s, use_search: e.target.checked }))} /> Usar web search</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={newGemini.dynamic_enabled} onChange={(e)=>setNewGemini(s=>({ ...s, dynamic_enabled: e.target.checked }))} /> Ajuste dinâmico (retrieval)</label>
          </div>
          {newGemini.dynamic_enabled && (
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs opacity-70">Modo de retrieval</label>
                <select className="w-full border rounded px-2 py-1 bg-transparent" value={newGemini.dynamic_mode}
                  onChange={(e)=>setNewGemini(s=>({ ...s, dynamic_mode: e.target.value }))}
                >
                  <option value="MODE_DYNAMIC">MODE_DYNAMIC</option>
                  <option value="MODE_AUTO">MODE_AUTO</option>
                  <option value="MODE_DISABLED">MODE_DISABLED</option>
                </select>
              </div>
              <div>
                <label className="text-xs opacity-70">Limite dinâmico (0–1)</label>
                <Input type="number" min={0} max={1} step={0.05} value={newGemini.dynamic_threshold}
                  onChange={(e)=>setNewGemini(s=>({ ...s, dynamic_threshold: Number(e.target.value || 0) }))}
                />
              </div>
            </div>
          )}
          <div>
            <label className="text-xs opacity-70">Tamanho do contexto de busca</label>
            <select className="w-full border rounded px-2 py-1 bg-transparent" value={newGemini.search_context_size}
              onChange={(e)=>setNewGemini(s=>({ ...s, search_context_size: e.target.value }))}
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
          </div>
          <div className="flex justify-end">
            <Button onClick={createGeminiEngine}>Criar engine</Button>
          </div>
          <div className="text-xs opacity-70">
            Recomendações: para pesquisas rápidas, use <code>gemini-2.5-flash</code> e ative web search. Para respostas mais robustas e melhor grounding, use <code>gemini-2.5-pro</code>.
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Engines</h2>
        <div className="grid gap-2">
          {engines.map(e => (
            <EngineCard key={e.id} engine={e} onSave={updateEngine} />
          ))}
          {!engines.length && <div className="text-sm opacity-70">Nenhuma engine cadastrada ainda (é criada na primeira run).</div>}
        </div>
      </section>
    </div>
  )
}

function EngineCard({ engine, onSave }: { engine: Engine; onSave: (e: Engine, cfg: string) => void }) {
  const [cfg, setCfg] = useState(JSON.stringify(engine.config_json || {}, null, 2))
  const example = {
    pricing: {
      input_per_1k_usd: 0.003,
      output_per_1k_usd: 0.006,
      per_call_usd: 0.0,
    },
  }
  const isGemini = (engine.name || '').toLowerCase() === 'gemini'
  return (
    <div className="border rounded-md p-3 grid gap-2 text-sm">
      <div className="flex items-center gap-2">
        <strong className="flex-1">{engine.name}</strong>
        <span className="opacity-70">{engine.id}</span>
      </div>
      {isGemini ? (
        <GeminiConfigEditor initial={engine.config_json || {}} onSave={(obj)=>onSave(engine, JSON.stringify(obj))} />
      ) : (
        <>
          <div className="text-xs opacity-70">Dica: configure <code>pricing</code> para estimar custos. Exemplo:</div>
          <pre className="text-xs bg-neutral-50 dark:bg-neutral-900 p-2 rounded border overflow-auto">{JSON.stringify(example, null, 2)}</pre>
          <textarea value={cfg} onChange={e=>setCfg(e.target.value)} rows={8} className="border rounded-md px-2 py-2 bg-transparent font-mono" />
          <div className="flex justify-end">
            <Button variant="secondary" onClick={()=>onSave(engine, cfg)}>Salvar</Button>
          </div>
        </>
      )}
    </div>
  )
}

function GeminiConfigEditor({ initial, onSave }: { initial: any; onSave: (cfg: any) => void }) {
  const [model, setModel] = useState<string>(initial?.model || 'gemini-2.5-flash')
  const [useSearch, setUseSearch] = useState<boolean>(initial?.use_search !== false)
  const [maxOutputTokens, setMaxOutputTokens] = useState<number>(Number(initial?.max_output_tokens || 2048))
  const [searchContextSize, setSearchContextSize] = useState<string>(initial?.search_context_size || 'low')
  const [dynEnabled, setDynEnabled] = useState<boolean>(initial?.dynamic_retrieval ? true : true)
  const [dynMode, setDynMode] = useState<string>(initial?.dynamic_retrieval?.mode || 'MODE_DYNAMIC')
  const [dynThr, setDynThr] = useState<number>(Number(initial?.dynamic_retrieval?.dynamic_threshold ?? 0.7))

  const cfg = useMemo(() => {
    const c: any = { model, use_search: useSearch, max_output_tokens: maxOutputTokens, search_context_size: searchContextSize }
    if (dynEnabled) c.dynamic_retrieval = { mode: dynMode, dynamic_threshold: dynThr }
    return c
  }, [model, useSearch, maxOutputTokens, searchContextSize, dynEnabled, dynMode, dynThr])

  return (
    <div className="grid gap-3">
      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="text-xs opacity-70">Modelo</label>
          <select className="w-full border rounded px-2 py-1 bg-transparent" value={model} onChange={(e)=>setModel(e.target.value)}>
            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
            <option value="gemini-1.5-pro">gemini-1.5-pro</option>
            <option value="gemini-1.5-flash">gemini-1.5-flash</option>
            <option value="gemini-1.5-flash-8b">gemini-1.5-flash-8b</option>
          </select>
        </div>
        <div>
          <label className="text-xs opacity-70">Max output tokens</label>
          <Input type="number" min={128} max={8192} value={maxOutputTokens} onChange={(e)=>setMaxOutputTokens(Number(e.target.value || 0))} />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2"><input type="checkbox" checked={useSearch} onChange={(e)=>setUseSearch(e.target.checked)} /> Usar web search</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={dynEnabled} onChange={(e)=>setDynEnabled(e.target.checked)} /> Ajuste dinâmico (retrieval)</label>
      </div>
      {dynEnabled && (
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <label className="text-xs opacity-70">Modo de retrieval</label>
            <select className="w-full border rounded px-2 py-1 bg-transparent" value={dynMode} onChange={(e)=>setDynMode(e.target.value)}>
              <option value="MODE_DYNAMIC">MODE_DYNAMIC</option>
              <option value="MODE_AUTO">MODE_AUTO</option>
              <option value="MODE_DISABLED">MODE_DISABLED</option>
            </select>
          </div>
          <div>
            <label className="text-xs opacity-70">Limite dinâmico (0–1)</label>
            <Input type="number" min={0} max={1} step={0.05} value={dynThr} onChange={(e)=>setDynThr(Number(e.target.value || 0))} />
          </div>
        </div>
      )}
      <div>
        <label className="text-xs opacity-70">Tamanho do contexto de busca</label>
        <select className="w-full border rounded px-2 py-1 bg-transparent" value={searchContextSize} onChange={(e)=>setSearchContextSize(e.target.value)}>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </select>
      </div>
      <div className="flex justify-between items-center">
        <div className="text-xs opacity-70">Dica: incentive a listagem de fontes com URLs completas no final da resposta.</div>
        <Button variant="secondary" onClick={()=>onSave(cfg)}>Salvar</Button>
      </div>
    </div>
  )
}

function KeyField({ label, placeholder, value, onChange, present, tested }: { label: string; placeholder: string; value: string; onChange: (v: string)=>void; present?: boolean; tested?: any }) {
  const ok = tested?.ok === true
  const err = tested && tested.ok === false
  return (
    <div className="grid gap-1">
      <div className="flex items-center gap-2 text-xs">
        <span className="font-medium">{label}</span>
        {present !== undefined && (<span className={`px-1.5 py-0.5 rounded border ${present ? 'bg-green-50 dark:bg-green-900/20' : ''}`}>{present ? 'detectada' : 'ausente'}</span>)}
        {tested && (
          <span className={`px-1.5 py-0.5 rounded border ${ok ? 'bg-green-50 dark:bg-green-900/20' : err ? 'bg-red-50 dark:bg-red-900/20' : ''}`}>{ok ? 'ok' : err ? (tested.error ? 'erro' : 'fail') : '—'}</span>
        )}
      </div>
      <Input placeholder={placeholder} value={value} onChange={(e)=>onChange(e.target.value)} />
    </div>
  )
}
