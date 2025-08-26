import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Toaster, toast } from 'sonner'

const API = '/api'

type Domain = { id: string; domain: string; pattern_regex?: string; is_primary: boolean }

type Engine = { id: string; name: string; region?: string; device?: string; config_json?: any }

export default function SettingsPage() {
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([])
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
  // Google SERP — criação rápida
  const [newSerp, setNewSerp] = useState({
    use_serpapi: true,
    serpapi_ai_overview: true,
    serpapi_no_cache: false,
  })
  // System settings
  const [systemSettings, setSystemSettings] = useState({
    default_timeout: 180,
    max_concurrent_runs: 5,
    auto_cleanup_days: 30,
    enable_monitoring: true,
    log_level: 'INFO',
    backup_enabled: true,
    backup_frequency: 'daily'
  })
  const [systemStatus, setSystemStatus] = useState<any>(null)

  const refresh = async () => {
    try {
      if (!projectId) return
      const [d, e, st, sys] = await Promise.all([
        axios.get(`${API}/projects/${projectId}/domains`).then(r => r.data),
        axios.get(`${API}/projects/${projectId}/engines`).then(r => r.data),
        axios.get(`${API}/setup/status`).then(r => r.data).catch(() => null),
        axios.get(`${API}/system/status`).then(r => r.data).catch(() => null),
      ])
      setDomains(d)
      setEngines(e)
      if (st) setKeysStatus(st)
      if (sys) setSystemStatus(sys)
    } catch (e: any) {
      toast.error('Falha ao carregar settings: ' + e.message)
    }
  }
  useEffect(() => { refresh() }, [projectId])

  useEffect(() => {
    axios.get(`${API}/projects`).then(r => {
      setProjects(r.data || [])
      if (!projectId && r.data?.[0]?.id) {
        setProjectId(r.data[0].id)
        localStorage.setItem('project_id', r.data[0].id)
      }
    }).catch(()=>{})
  }, [])

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
        // Engines criadas via Settings são "principais"
        config_json: { _main: true, ...cfg },
      }
      const res = await axios.post(`${API}/projects/${projectId}/engines`, payload)
      toast.success(`Engine Gemini criada: ${res.data.id}`)
      await refresh()
    } catch (e: any) {
      toast.error('Falha ao criar engine: ' + e.message)
    }
  }

  const createSerpEngine = async () => {
    if (!projectId) { toast.error('Defina o Project ID acima'); return }
    try {
      const payload = {
        name: 'google_serp',
        region: 'BR',
        device: 'desktop',
        // Engines criadas via Settings são "principais"
        config_json: {
          _main: true,
          use_serpapi: !!newSerp.use_serpapi,
          serpapi_ai_overview: !!newSerp.serpapi_ai_overview,
          serpapi_no_cache: !!newSerp.serpapi_no_cache,
        },
      }
      const res = await axios.post(`${API}/projects/${projectId}/engines`, payload)
      toast.success(`Engine Google SERP criada: ${res.data.id}`)
      await refresh()
    } catch (e: any) {
      toast.error('Falha ao criar engine: ' + e.message)
    }
  }

  const createOpenAIEngineMini = async () => {
    if (!projectId) { toast.error('Defina o Project ID acima'); return }
    try {
      const payload = {
        name: 'openai',
        region: 'BR',
        device: 'desktop',
        // Engines criadas via Settings são "principais"
        config_json: { _main: true, model: 'gpt-5-mini', web_search: true, search_context_size: 'low', reasoning_effort: 'low' },
      }
      const res = await axios.post(`${API}/projects/${projectId}/engines`, payload)
      toast.success(`Engine OpenAI GPT-5 mini criada: ${res.data.id}`)
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

  const deleteEngine = async (e: Engine) => {
    try {
      const res = await axios.delete(`${API}/engines/${e.id}`)
      if (res.data?.archived) {
        toast.success('Engine arquivada (existem runs associadas)')
      } else {
        toast.success('Engine excluída')
      }
      await refresh()
    } catch (err: any) {
      toast.error('Falha ao remover engine: ' + err.message)
    }
  }

  return (
    <div className="space-y-4">
      <Toaster richColors position="top-right" />
      <h1 className="text-2xl font-semibold">Configurações</h1>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Coluna 1: Integrações (API Keys) */}
        <section className="space-y-2 lg:col-span-2">
          <h2 className="text-lg font-medium">Integrações (API Keys)</h2>
          <div className="border rounded-md p-3 grid gap-3">
            <div className="text-sm opacity-70">Preencha apenas o que for usar. Você pode testar antes de salvar.</div>
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

        {/* Coluna 2: Projeto/Diagnóstico */}
        <aside className="space-y-2">
          <h3 className="text-lg font-medium">Projeto</h3>
          <div className="border rounded-md p-3 grid gap-2">
            <div className="text-sm opacity-70">Projeto ativo</div>
            <Select value={projectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => { setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value); }}>
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.id})</option>
              ))}
            </Select>
            <div className="flex justify-end">
              <Button variant="secondary" onClick={refresh}>Atualizar</Button>
            </div>
          </div>
        </aside>
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Domínios alvo</h2>
        <div className="border rounded-md p-3 grid gap-2">
          <div className="grid gap-2 md:grid-cols-2">
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
        <h2 className="text-lg font-medium">Engines — OpenAI</h2>
        <div className="border rounded-md p-3 grid gap-3 text-sm">
          <div className="text-sm">Criar engine padrão para <code>gpt-5-mini</code> com web search.</div>
          <div className="flex justify-end">
            <Button onClick={createOpenAIEngineMini}>Criar GPT‑5 mini</Button>
          </div>
          <div className="text-xs opacity-70">Observação: alguns modelos não aceitam parâmetro de raciocínio; o backend já contorna automaticamente.</div>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Engines — Gemini</h2>
        <div className="border rounded-md p-3 grid gap-3 text-sm">
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs opacity-70">Modelo</label>
              <Select
                value={newGemini.model}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setNewGemini(s=>({ ...s, model: e.target.value }))}
              >
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                <option value="gemini-1.5-flash-8b">gemini-1.5-flash-8b</option>
              </Select>
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
                <Select value={newGemini.dynamic_mode}
                  onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setNewGemini(s=>({ ...s, dynamic_mode: e.target.value }))}
                >
                  <option value="MODE_DYNAMIC">MODE_DYNAMIC</option>
                  <option value="MODE_AUTO">MODE_AUTO</option>
                  <option value="MODE_DISABLED">MODE_DISABLED</option>
                </Select>
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
            <Select value={newGemini.search_context_size}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setNewGemini(s=>({ ...s, search_context_size: e.target.value }))}
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </Select>
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
        <h2 className="text-lg font-medium">Engines — Google SERP</h2>
        <div className="border rounded-md p-3 grid gap-3 text-sm">
          <div className="grid sm:grid-cols-3 gap-2">
            <label className="flex items-center gap-2"><input type="checkbox" checked={newSerp.use_serpapi} onChange={(e)=>setNewSerp(s=>({ ...s, use_serpapi: e.target.checked }))} /> Usar SerpApi</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={newSerp.serpapi_ai_overview} onChange={(e)=>setNewSerp(s=>({ ...s, serpapi_ai_overview: e.target.checked }))} /> Preferir AI Overview</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={newSerp.serpapi_no_cache} onChange={(e)=>setNewSerp(s=>({ ...s, serpapi_no_cache: e.target.checked }))} /> Ignorar cache (no_cache)</label>
          </div>
          <div className="flex justify-end">
            <Button onClick={createSerpEngine}>Criar engine</Button>
          </div>
          <div className="text-xs opacity-70">
            Requer chave SerpApi salva em Configurações. O adaptador fará busca padrão e, se existir, usará AI Overview embutido ou via page_token com `engine=google_ai_overview`.
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Engines</h2>
        <div className="grid gap-2">
          {engines.map(e => (
            <EngineCard key={e.id} engine={e} onSave={updateEngine} onDelete={deleteEngine} />
          ))}
          {!engines.length && <div className="text-sm opacity-70">Nenhuma engine cadastrada ainda (é criada na primeira run).</div>}
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Sistema & Performance</h2>
        <div className="border rounded-md p-3 grid gap-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="text-xs opacity-70">Timeout padrão por ciclo (segundos)</label>
              <Input type="number" min={60} max={600} value={systemSettings.default_timeout}
                onChange={(e)=>setSystemSettings(s=>({ ...s, default_timeout: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="text-xs opacity-70">Máximo de runs simultâneas</label>
              <Input type="number" min={1} max={20} value={systemSettings.max_concurrent_runs}
                onChange={(e)=>setSystemSettings(s=>({ ...s, max_concurrent_runs: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="text-xs opacity-70">Limpeza automática (dias)</label>
              <Input type="number" min={7} max={365} value={systemSettings.auto_cleanup_days}
                onChange={(e)=>setSystemSettings(s=>({ ...s, auto_cleanup_days: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className="text-xs opacity-70">Nível de log</label>
              <Select value={systemSettings.log_level}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setSystemSettings(s=>({ ...s, log_level: e.target.value }))}
              >
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </Select>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={systemSettings.enable_monitoring}
                onChange={(e)=>setSystemSettings(s=>({ ...s, enable_monitoring: e.target.checked }))}
              /> Monitoramento ativo
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={systemSettings.backup_enabled}
                onChange={(e)=>setSystemSettings(s=>({ ...s, backup_enabled: e.target.checked }))}
              /> Backup automático
            </label>
            {systemSettings.backup_enabled && (
              <Select value={systemSettings.backup_frequency}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setSystemSettings(s=>({ ...s, backup_frequency: e.target.value }))}
              >
                <option value="hourly">A cada hora</option>
                <option value="daily">Diário</option>
                <option value="weekly">Semanal</option>
              </Select>
            )}
          </div>
          <div className="flex justify-end">
            <Button onClick={()=>toast.info('Configurações do sistema salvas (mock)')}>Salvar configurações</Button>
          </div>
        </div>
      </section>

      {systemStatus && (
        <section className="space-y-2">
          <h2 className="text-lg font-medium">Status do Sistema</h2>
          <div className="border rounded-md p-3">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{systemStatus.uptime || '0h'}</div>
                <div className="text-xs opacity-70">Uptime</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{systemStatus.active_runs || 0}</div>
                <div className="text-xs opacity-70">Runs ativas</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{systemStatus.total_runs || 0}</div>
                <div className="text-xs opacity-70">Total de runs</div>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t">
              <div className="grid gap-2 md:grid-cols-2 text-sm">
                <div>CPU: <span className="font-mono">{systemStatus.cpu_usage || '0%'}</span></div>
                <div>Memória: <span className="font-mono">{systemStatus.memory_usage || '0%'}</span></div>
                <div>Disco: <span className="font-mono">{systemStatus.disk_usage || '0%'}</span></div>
                <div>Redis: <span className={`font-mono ${systemStatus.redis_status === 'connected' ? 'text-green-600' : 'text-red-600'}`}>{systemStatus.redis_status || 'unknown'}</span></div>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Manutenção</h2>
        <div className="border rounded-md p-3 grid gap-3">
          <div className="grid gap-2 md:grid-cols-3">
            <Button variant="outline" onClick={()=>toast.info('Limpeza iniciada (mock)')}>
              🧹 Limpar runs antigas
            </Button>
            <Button variant="outline" onClick={()=>toast.info('Backup criado (mock)')}>
              💾 Criar backup
            </Button>
            <Button variant="outline" onClick={()=>toast.info('Cache limpo (mock)')}>
              🗑️ Limpar cache
            </Button>
          </div>
          <div className="text-xs opacity-70">
            Ferramentas de manutenção para otimizar performance e liberar espaço em disco.
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Informações do Sistema</h2>
        <div className="border rounded-md p-3">
          <div className="grid gap-2 text-sm font-mono">
            <div>Versão: <span className="text-blue-600">v1.0.0</span></div>
            <div>Build: <span className="text-gray-600">{new Date().toISOString().slice(0, 10)}</span></div>
            <div>Ambiente: <span className="text-green-600">Production</span></div>
            <div>Database: <span className="text-purple-600">MySQL</span></div>
          </div>
        </div>
      </section>
    </div>
  )
}

function EngineCard({ engine, onSave, onDelete }: { engine: Engine; onSave: (e: Engine, cfg: string) => void; onDelete: (e: Engine) => void }) {
  const [cfg, setCfg] = useState(JSON.stringify(engine.config_json || {}, null, 2))
  const [expanded, setExpanded] = useState<boolean>(false)
  const isGemini = (engine.name || '').toLowerCase() === 'gemini'
  const prettyPairs: Array<{ k: string; v: string }> = Object.entries(engine.config_json || {}).map(([k, v]) => ({
    k: String(k),
    v: typeof v === 'string' ? v : JSON.stringify(v),
  }))
  return (
    <div className="border rounded-md p-3 grid gap-2 text-sm">
      <div className="flex items-center gap-2">
        <div className="flex flex-col flex-1">
          <strong>{engine.name}</strong>
          <span className="text-[11px] opacity-60">{engine.region || '—'} · {engine.device || '—'}</span>
        </div>
        <span className="opacity-50 text-[11px] mr-2">{engine.id}</span>
        <Button variant="outline" size="sm" onClick={()=>onDelete(engine)}>Remover</Button>
      </div>
      {isGemini ? (
        <GeminiConfigEditor initial={engine.config_json || {}} onSave={(obj)=>onSave(engine, JSON.stringify(obj))} />
      ) : (
        <>
          {!expanded && (
            <div className="grid gap-2">
              <div className="text-xs opacity-70">Configuração atual</div>
              <div className="rounded-md border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/40 p-2">
                {prettyPairs.length ? (
                  <div className="grid gap-1">
                    {prettyPairs.map(({ k, v }) => (
                      <div key={k} className="flex items-start gap-2 text-xs">
                        <span className="min-w-[140px] font-medium text-neutral-700 dark:text-neutral-300 break-words">{k}</span>
                        <span className="flex-1 font-mono break-words text-neutral-900 dark:text-neutral-100">{v}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs opacity-70">Sem configuração.</div>
                )}
              </div>
              <div className="flex justify-end">
                <Button variant="outline" size="sm" onClick={() => { setCfg(JSON.stringify(engine.config_json || {}, null, 2)); setExpanded(true) }}>Configurar</Button>
              </div>
            </div>
          )}
          {expanded && (
            <>
              <div className="text-xs opacity-70">Configuração (chave/valor). Valores aceitam JSON (ex.: números, objetos).</div>
              <KeyValueEditor
                initialObject={engine.config_json || {}}
                onChangeObject={(obj)=> setCfg(JSON.stringify(obj, null, 2))}
              />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={() => { setCfg(JSON.stringify(engine.config_json || {}, null, 2)); setExpanded(false) }}>Cancelar</Button>
                <Button variant="secondary" onClick={() => { onSave(engine, cfg); setExpanded(false) }}>Salvar</Button>
              </div>
            </>
          )}
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
          <Select value={model} onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setModel(e.target.value)}>
            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
            <option value="gemini-1.5-pro">gemini-1.5-pro</option>
            <option value="gemini-1.5-flash">gemini-1.5-flash</option>
            <option value="gemini-1.5-flash-8b">gemini-1.5-flash-8b</option>
          </Select>
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
            <Select value={dynMode} onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setDynMode(e.target.value)}>
              <option value="MODE_DYNAMIC">MODE_DYNAMIC</option>
              <option value="MODE_AUTO">MODE_AUTO</option>
              <option value="MODE_DISABLED">MODE_DISABLED</option>
            </Select>
          </div>
          <div>
            <label className="text-xs opacity-70">Limite dinâmico (0–1)</label>
            <Input type="number" min={0} max={1} step={0.05} value={dynThr} onChange={(e)=>setDynThr(Number(e.target.value || 0))} />
          </div>
        </div>
      )}
      <div>
        <label className="text-xs opacity-70">Tamanho do contexto de busca</label>
        <Select value={searchContextSize} onChange={(e: React.ChangeEvent<HTMLSelectElement>)=>setSearchContextSize(e.target.value)}>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </Select>
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

function KeyValueEditor({ initialObject, onChangeObject }: { initialObject: any; onChangeObject: (obj: any) => void }) {
  const toPairs = (obj: any): Array<{ key: string; value: string }> => {
    const entries = Object.entries(obj || {}) as Array<[string, any]>
    return entries.map(([k, v]) => ({ key: String(k), value: typeof v === 'string' ? v : JSON.stringify(v) }))
  }
  const [pairs, setPairs] = useState<Array<{ key: string; value: string }>>(() => toPairs(initialObject))

  useEffect(() => {
    // Emit as object on change
    const obj: any = {}
    for (const { key, value } of pairs) {
      if (!key) continue
      try {
        obj[key] = JSON.parse(value)
      } catch {
        obj[key] = value
      }
    }
    onChangeObject(obj)
  }, [pairs])

  const addPair = () => setPairs(p => [...p, { key: '', value: '' }])
  const removePair = (idx: number) => setPairs(p => p.filter((_, i) => i !== idx))

  return (
    <div className="grid gap-2">
      {pairs.map((p, i) => (
        <div key={i} className="grid grid-cols-1 sm:grid-cols-5 gap-2 items-center">
          <Input placeholder="chave" value={p.key} onChange={(e)=> setPairs(prev => prev.map((it, idx) => idx===i ? { ...it, key: e.target.value } : it))} className="sm:col-span-2" />
          <Input placeholder="valor (string ou JSON)" value={p.value} onChange={(e)=> setPairs(prev => prev.map((it, idx) => idx===i ? { ...it, value: e.target.value } : it))} className="sm:col-span-3" />
          <div className="flex justify-end sm:col-span-5">
            <Button variant="outline" size="sm" onClick={()=>removePair(i)}>Remover</Button>
          </div>
        </div>
      ))}
      <div>
        <Button variant="outline" size="sm" onClick={addPair}>+ Adicionar</Button>
      </div>
    </div>
  )
}
