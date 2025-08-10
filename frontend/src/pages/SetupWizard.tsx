import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Select } from '../components/ui/select'
import { Toaster, toast } from 'sonner'

const API = '/api'

type Conn = { openai?: boolean; gemini?: boolean; perplexity?: boolean; serpapi?: boolean }

function toHostname(input: string): string {
  try {
    const trimmed = input.trim()
    const withProto = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`
    const u = new URL(withProto)
    return u.hostname
  } catch {
    return input.replace(/^https?:\/\//i, '').split('/')[0]
  }
}

export default function SetupWizard() {
  const [site, setSite] = useState('')
  const [step, setStep] = useState(1)
  const [status, setStatus] = useState<any>(null)
  const [testing, setTesting] = useState(false)
  const [testRes, setTestRes] = useState<any>(null)
  const [projectId, setProjectId] = useState<string>('')
  const [subprojectId, setSubprojectId] = useState<string>('')
  const [queries, setQueries] = useState<{ text: string; intent: string }[]>([])
  const [selected, setSelected] = useState<Record<string, boolean>>({})

  useEffect(() => {
    axios.get(`${API}/setup/status`).then(r => setStatus(r.data))
  }, [])

  const ensureProjectAndSP = async () => {
    try {
      let pid = projectId || localStorage.getItem('project_id') || ''
      if (!pid) {
        const host = site ? toHostname(site) : 'Projeto Demo'
        const p = await axios.post(`${API}/projects`, { name: `${host} – BR pt-BR`, country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
        pid = p.data.id
        setProjectId(pid)
        localStorage.setItem('project_id', pid)
      }
      if (!subprojectId) {
        const sp = await axios.post(`${API}/projects/${pid}/subprojects`, { name: 'Inicial', description: 'Criado pelo wizard' })
        setSubprojectId(sp.data.id)
      }
      return { pid, spid: subprojectId || undefined }
    } catch (e: any) {
      toast.error('Falha ao preparar projeto/subprojeto: ' + (e?.message || ''))
      throw e
    }
  }

  const createProjectAndSP = async () => {
    try {
      const host = toHostname(site)
      const projName = `${host} – BR pt-BR`
      const p = await axios.post(`${API}/projects`, { name: projName, country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
      setProjectId(p.data.id)
      localStorage.setItem('project_id', p.data.id)
      const sp = await axios.post(`${API}/projects/${p.data.id}/subprojects`, { name: 'Inicial', description: 'Subprojeto criado pelo wizard' })
      setSubprojectId(sp.data.id)
      toast.success('Projeto criado')
    } catch (e: any) {
      toast.error('Falha ao criar projeto: ' + e.message)
    }
  }

  const testConnections = async () => {
    setTesting(true)
    try {
      const res = await axios.post(`${API}/setup/test-connections`, {})
      setTestRes(res.data)
      toast.success('Conexões testadas')
    } catch (e: any) {
      toast.error('Falha ao testar conexões: ' + e.message)
    } finally {
      setTesting(false)
    }
  }

  const getSuggestions = async () => {
    const res = await axios.post(`${API}/setup/suggest-queries`, { site })
    setQueries(res.data.queries || [])
    const map: Record<string, boolean> = {}
    ;(res.data.queries || []).forEach((q: any) => { map[q.text] = true })
    setSelected(map)
  }

  const runSmoke = async () => {
    try {
      await ensureProjectAndSP()
      const chosen = queries.filter(q => selected[q.text]).map(q => q.text).slice(0, 5)
      if (chosen.length === 0) return toast.error('Selecione pelo menos 1 consulta')
      const engine = (testRes && Object.values(testRes).some((v: any) => v.ok)) ? 'gemini' : 'sandbox'
      await axios.post(`${API}/setup/smoke-test`, { project_id: projectId || localStorage.getItem('project_id'), subproject_id: subprojectId || null, queries: chosen, engine })
      toast.success('Smoke test iniciado')
      window.location.href = '/runs'
    } catch (e: any) {
      toast.error('Falha ao iniciar smoke test: ' + (e?.response?.data?.detail || e.message || ''))
    }
  }

  return (
    <div className="max-w-2xl mx-auto grid gap-4">
      <Toaster richColors position="top-right" />
      <h1 className="text-2xl font-semibold">First‑Run Wizard</h1>

      {step === 1 && (
        <div className="border rounded-lg p-4 grid gap-3">
          <div className="space-y-1">
            <Label>Domínio do site</Label>
            <Input placeholder="https://www.seudominio.com.br" value={site} onChange={(e) => setSite(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setStep(2)} disabled={!site}>Continuar</Button>
            <Button onClick={async () => { await createProjectAndSP(); setStep(2) }} disabled={!site}>Criar projeto e continuar</Button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="border rounded-lg p-4 grid gap-3">
          <div className="text-sm opacity-70">Testar conexões (opcional). Sem chaves, usamos Sandbox.</div>
          <div className="flex gap-2">
            <Button onClick={testConnections} disabled={testing}>{testing ? 'Testando…' : 'Testar conexões'}</Button>
            <Button variant="secondary" onClick={() => { setStep(3); getSuggestions() }}>Continuar</Button>
          </div>
          {testRes && (
            <div className="text-xs border rounded-md p-2">
              <pre className="whitespace-pre-wrap">{JSON.stringify(testRes, null, 2)}</pre>
            </div>
          )}
          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(1)}>Voltar</Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="border rounded-lg p-4 grid gap-3">
          <div className="text-sm opacity-70">Selecione as consultas para o Smoke Test (até 5)</div>
          <div className="grid gap-1">
            {queries.map((q) => (
              <label key={q.text} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={!!selected[q.text]} onChange={(e) => setSelected({ ...selected, [q.text]: e.target.checked })} />
                <span className="opacity-80">{q.text}</span>
                <span className="ml-auto text-xs opacity-60">{q.intent}</span>
              </label>
            ))}
          </div>
          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setStep(2)}>Voltar</Button>
            <Button onClick={runSmoke}>Rodar Smoke Test</Button>
          </div>
        </div>
      )}
    </div>
  )
}
