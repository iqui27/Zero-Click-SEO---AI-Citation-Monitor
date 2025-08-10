import React, { useEffect, useState } from 'react'
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

  const refresh = async () => {
    try {
      if (!projectId) return
      const [d, e] = await Promise.all([
        axios.get(`${API}/projects/${projectId}/domains`).then(r => r.data),
        axios.get(`${API}/projects/${projectId}/engines`).then(r => r.data),
      ])
      setDomains(d)
      setEngines(e)
    } catch (e: any) {
      toast.error('Falha ao carregar settings: ' + e.message)
    }
  }
  useEffect(() => { refresh() }, [projectId])

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
    <div className="space-y-4">
      <Toaster richColors position="top-right" />
      <h1 className="text-2xl font-semibold">Settings</h1>
      <div className="flex gap-2 items-center">
        <Input placeholder="Project ID" value={projectId} onChange={(e)=>{ setProjectId(e.target.value); localStorage.setItem('project_id', e.target.value) }} />
        <Button variant="secondary" onClick={refresh}>Atualizar</Button>
      </div>

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
  return (
    <div className="border rounded-md p-3 grid gap-2 text-sm">
      <div className="flex items-center gap-2">
        <strong className="flex-1">{engine.name}</strong>
        <span className="opacity-70">{engine.id}</span>
      </div>
      <div className="text-xs opacity-70">Dica: configure <code>pricing</code> para estimar custos. Exemplo:</div>
      <pre className="text-xs bg-neutral-50 dark:bg-neutral-900 p-2 rounded border overflow-auto">{JSON.stringify(example, null, 2)}</pre>
      <textarea value={cfg} onChange={e=>setCfg(e.target.value)} rows={8} className="border rounded-md px-2 py-2 bg-transparent font-mono" />
      <div className="flex justify-end">
        <Button variant="secondary" onClick={()=>onSave(engine, cfg)}>Salvar</Button>
      </div>
    </div>
  )
}
