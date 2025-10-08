import React, { useState } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2, Clock, Database, Sparkles, FileJson, Code, Eye } from 'lucide-react'

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

export default function SemanticFlowVisualizer() {
  const [question, setQuestion] = useState('Como abrir conta digital no BB?')
  const [projectName, setProjectName] = useState('Banco do Brasil')
  const [engine, setEngine] = useState('google_serp')
  const [language, setLanguage] = useState('pt-BR')
  const [region, setRegion] = useState('BR')
  const [device, setDevice] = useState('mobile')
  const [busy, setBusy] = useState(false)
  const [flow, setFlow] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set(['input']))

  const STAGE_META: Record<string, { label: string; icon: any; color: string }> = {
    input: { label: '1. Input & Validação', icon: FileJson, color: 'text-blue-600 dark:text-blue-400' },
    engine_call: { label: '2. Chamada SERP/Engine', icon: Database, color: 'text-purple-600 dark:text-purple-400' },
    extract_citations: { label: '3. Extração de Citações', icon: Code, color: 'text-indigo-600 dark:text-indigo-400' },
    service_init: { label: '4. Inicialização Gemini', icon: Sparkles, color: 'text-pink-600 dark:text-pink-400' },
    prepare_citations: { label: '5. Normalização de Citações', icon: Code, color: 'text-violet-600 dark:text-violet-400' },
    build_prompt: { label: '6. Construção do Prompt', icon: Sparkles, color: 'text-amber-600 dark:text-amber-400' },
    gemini_call: { label: '7. Análise Semântica (Gemini)', icon: Sparkles, color: 'text-green-600 dark:text-green-400' },
    parse_json: { label: '8. Parse do JSON', icon: FileJson, color: 'text-cyan-600 dark:text-cyan-400' },
    normalize_payload: { label: '9. Normalização Final', icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400' },
    error: { label: 'Erro', icon: XCircle, color: 'text-red-600 dark:text-red-400' },
  }

  const toggleStage = (stage: string) => {
    setExpandedStages(prev => {
      const next = new Set(prev)
      if (next.has(stage)) {
        next.delete(stage)
      } else {
        next.add(stage)
      }
      return next
    })
  }

  const runFlow = async () => {
    setBusy(true)
    setError(null)
    setFlow([])
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/debug/full-pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question, 
          project_name: projectName,
          engine,
          language,
          region,
          device,
        })
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || data.error || 'Erro ao executar pipeline')
      } else {
        setFlow(data.flow || [])
        // Auto-expand engine_call e normalize_payload
        if (data.flow && data.flow.length) {
          const toExpand = new Set<string>(['input', 'engine_call', 'normalize_payload'])
          data.flow.forEach((stage: any) => {
            if (stage.status === 'error') toExpand.add(stage.stage)
          })
          setExpandedStages(toExpand)
        }
      }
    } catch (e: any) {
      setError(e?.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6">
      {/* Control panel */}
      <div className="p-4 border rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 shadow-sm space-y-4">
        <div className="flex items-center gap-3">
          <Eye className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          <h2 className="font-semibold text-lg">Pipeline Completo de Análise Semântica</h2>
        </div>
        <p className="text-sm opacity-80">Visualize cada etapa do processamento: desde o input inicial até o payload normalizado final.</p>
        
        <div className="grid gap-2">
          <Label className="text-xs font-semibold uppercase tracking-wide">Pergunta / Query</Label>
          <Input 
            value={question} 
            onChange={e => setQuestion(e.target.value)} 
            placeholder="Como abrir conta digital no BB?"
            className="text-base font-medium"
          />
        </div>
        
        <div className="grid md:grid-cols-2 gap-3">
          <div className="grid gap-2">
            <Label className="text-xs font-semibold uppercase tracking-wide">Projeto (marca)</Label>
            <Input value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="Banco do Brasil" />
          </div>
          <div className="grid gap-2">
            <Label className="text-xs font-semibold uppercase tracking-wide">Engine</Label>
            <select 
              value={engine} 
              onChange={e => setEngine(e.target.value)}
              className="border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 bg-white dark:bg-neutral-900 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
            >
              <option value="google_serp">Google SERP (SerpAPI)</option>
              <option value="gemini">Gemini (direto)</option>
              <option value="openai">OpenAI</option>
              <option value="perplexity">Perplexity</option>
            </select>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-3">
          <div className="grid gap-2">
            <Label className="text-xs font-semibold uppercase tracking-wide">Language</Label>
            <Input value={language} onChange={e => setLanguage(e.target.value)} placeholder="pt-BR" />
          </div>
          <div className="grid gap-2">
            <Label className="text-xs font-semibold uppercase tracking-wide">Region</Label>
            <Input value={region} onChange={e => setRegion(e.target.value)} placeholder="BR" />
          </div>
          <div className="grid gap-2">
            <Label className="text-xs font-semibold uppercase tracking-wide">Device</Label>
            <select 
              value={device} 
              onChange={e => setDevice(e.target.value)}
              className="border border-neutral-300 dark:border-neutral-700 rounded-md px-3 py-2 bg-white dark:bg-neutral-900 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
            >
              <option value="mobile">Mobile</option>
              <option value="desktop">Desktop</option>
              <option value="tablet">Tablet</option>
            </select>
          </div>
        </div>
        
        <Button onClick={runFlow} disabled={busy} className="w-full" size="lg">
          {busy ? (
            <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Executando pipeline...</>
          ) : (
            <>Executar Pipeline Completo</>
          )}
        </Button>
      </div>

      {/* Error display */}
      {error && (
        <div className="p-4 border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-950/20 rounded-lg text-red-700 dark:text-red-300 text-sm">
          <strong>Erro:</strong> {error}
        </div>
      )}

      {/* Flow stages */}
      {flow.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
            <h3 className="font-semibold text-lg">Pipeline de Execução ({flow.length} etapas)</h3>
          </div>
          
          <div className="space-y-2">
            {flow.map((stage, idx) => {
              const meta = STAGE_META[stage.stage] || { label: stage.stage, icon: FileJson, color: 'text-neutral-600' }
              const Icon = meta.icon
              const isExpanded = expandedStages.has(stage.stage)
              
              return (
                <div key={`${stage.stage}-${idx}`} className="border rounded-lg overflow-hidden bg-white dark:bg-neutral-900 shadow-sm">
                  {/* Header */}
                  <button
                    onClick={() => toggleStage(stage.stage)}
                    className="w-full p-4 flex items-center gap-3 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                  >
                    {isExpanded ? <ChevronDown className="h-5 w-5 text-neutral-500" /> : <ChevronRight className="h-5 w-5 text-neutral-500" />}
                    <Icon className={`h-5 w-5 ${meta.color}`} />
                    <span className="font-medium flex-1 text-left">{meta.label}</span>
                    {stage.status === 'completed' && <CheckCircle2 className="h-5 w-5 text-green-600" />}
                    {stage.status === 'error' && <XCircle className="h-5 w-5 text-red-600" />}
                    {stage.duration_ms && (
                      <span className="text-xs px-2 py-1 rounded-full bg-neutral-100 dark:bg-neutral-800 font-mono">
                        {stage.duration_ms}ms
                      </span>
                    )}
                  </button>
                  
                  {/* Expanded content */}
                  {isExpanded && stage.data && (
                    <div className="border-t border-neutral-200 dark:border-neutral-800 p-4 bg-neutral-50/50 dark:bg-neutral-950/50 space-y-3">
                      {stage.stage === 'build_prompt' && stage.data.full_prompt && (
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-600 dark:text-neutral-400 mb-2">Prompt Completo Injetado no Gemini</h4>
                          <pre className="text-xs bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-md p-3 max-h-[400px] overflow-auto whitespace-pre-wrap leading-relaxed">
                            {stage.data.full_prompt}
                          </pre>
                        </div>
                      )}
                      
                      {stage.stage === 'gemini_call' && stage.data.raw_response && (
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-600 dark:text-neutral-400 mb-2">Resposta Bruta do Gemini</h4>
                          <div className="text-xs bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-md p-3 max-h-[400px] overflow-auto">
                            <pre className="whitespace-pre-wrap leading-relaxed">{stage.data.raw_response}</pre>
                          </div>
                          {stage.data.finish_reason !== undefined && (
                            <div className="text-xs mt-2 opacity-70">
                              <strong>Finish reason:</strong> {stage.data.finish_reason}
                            </div>
                          )}
                        </div>
                      )}
                      
                      {stage.stage === 'engine_call' && stage.data.full_text && (
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-600 dark:text-neutral-400 mb-2">Resposta da SERP/Engine</h4>
                          <div className="grid gap-3">
                            <div className="text-xs bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-md p-3 max-h-[300px] overflow-auto">
                              <pre className="whitespace-pre-wrap leading-relaxed">{stage.data.full_text}</pre>
                            </div>
                            {stage.data.links && stage.data.links.length > 0 && (
                              <div>
                                <h5 className="text-xs font-semibold mb-2">Links Detectados ({stage.data.links_count})</h5>
                                <div className="space-y-1 max-h-[200px] overflow-auto">
                                  {stage.data.links.slice(0, 10).map((link: any, i: number) => (
                                    <div key={i} className="text-xs p-2 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded">
                                      <a href={link.url} target="_blank" rel="noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline block truncate">
                                        {link.title || link.url}
                                      </a>
                                      <div className="text-neutral-500 truncate">{link.url}</div>
                                    </div>
                                  ))}
                                  {stage.data.links_count > 10 && (
                                    <div className="text-xs opacity-60 p-2">... e mais {stage.data.links_count - 10} links</div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {stage.stage === 'extract_citations' && stage.data.citations && (
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-600 dark:text-neutral-400 mb-2">
                            Citações Extraídas ({stage.data.citations_count})
                          </h4>
                          <div className="space-y-2">
                            <div className="flex gap-4 text-xs">
                              <span className="font-semibold">Total: {stage.data.citations_count}</span>
                              <span className="text-green-600 dark:text-green-400 font-semibold">Nossas: {stage.data.our_citations}</span>
                              <span className="text-neutral-600 dark:text-neutral-400 font-semibold">Terceiros: {stage.data.citations_count - stage.data.our_citations}</span>
                            </div>
                            <div className="grid gap-1 max-h-[200px] overflow-auto">
                              {stage.data.citations.map((cite: any, i: number) => (
                                <div key={i} className={`text-xs p-2 border rounded flex items-start gap-2 ${cite.is_ours ? 'bg-green-50 dark:bg-green-950/20 border-green-300 dark:border-green-800' : 'bg-white dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800'}`}>
                                  <div className="flex-1 min-w-0">
                                    <div className="font-semibold truncate">{cite.domain}</div>
                                    <a href={cite.url} target="_blank" rel="noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline truncate block text-[10px]">
                                      {cite.url}
                                    </a>
                                  </div>
                                  {cite.is_ours && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-600 text-white font-semibold">NOSSA</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {(stage.stage === 'normalize_payload' || stage.stage === 'parse_json') && (stage.data.normalized || stage.data.parsed) && (
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-600 dark:text-neutral-400 mb-2">
                            {stage.stage === 'normalize_payload' ? 'Payload Normalizado Final' : 'JSON Parseado'}
                          </h4>
                          <JsonViewer data={stage.data.normalized || stage.data.parsed} />
                        </div>
                      )}
                      
                      {/* Generic data display */}
                      {!['build_prompt', 'gemini_call', 'normalize_payload', 'parse_json', 'engine_call', 'extract_citations'].includes(stage.stage) && (
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-neutral-600 dark:text-neutral-400 mb-2">Dados</h4>
                          <JsonViewer data={stage.data} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
      
      {!busy && flow.length === 0 && !error && (
        <div className="p-8 border border-dashed border-neutral-300 dark:border-neutral-700 rounded-lg text-center opacity-60">
          <p className="text-sm">Configure os parâmetros acima e clique em "Executar Pipeline Completo" para visualizar o fluxo.</p>
        </div>
      )}
    </div>
  )
}
