import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select } from '../components/ui/select'
import { Toaster, toast } from 'sonner'
import { RefreshCw, Plus } from 'lucide-react'

const API = '/api'

type RunItem = {
  id: string
  engine: string
  status: string
  started_at?: string
  finished_at?: string
  zcrs?: number
  amr_flag?: boolean
  dcr_flag?: boolean
  template_name?: string
  subproject_name?: string
  cost_usd?: number
  tokens_total?: number
}

type Project = { id: string; name: string }

type Subproject = { id: string; name: string }

const TEMPLATES: { label: string; text: string }[] = [
  { label: 'Tarifas conta corrente BB 2025 (fontes)', text: 'Você é um avaliador. Use pesquisa na web quando necessário. Consulta: "tarifas de conta corrente do Banco do Brasil em 2025". Responda brevemente e LISTE AS FONTES com URLs completas (http) no final. Priorize páginas de bb.com.br e banco central.' },
  { label: 'Abrir conta PJ no BB (requisitos + fontes)', text: 'Explique como abrir conta PJ no Banco do Brasil: requisitos, documentos e prazos. Liste 3–5 fontes com URLs completas (bb.com.br, gov.br).' },
  { label: 'Poupança BB hoje (fontes Bacen/BB)', text: 'Qual é o rendimento da poupança no Banco do Brasil hoje? Explique a regra atual e cite fontes (Bacen e BB) com URLs.' },
  { label: 'Cartão Ourocard (taxas/anuidades + fontes)', text: 'Quais as taxas e anuidades dos cartões Ourocard? Liste modelos e forneça fontes oficiais do BB com URLs.' },
  { label: 'Empréstimo consignado BB (taxas atuais + fontes)', text: 'Quais as taxas atuais de empréstimo consignado do Banco do Brasil? Traga 3–5 fontes oficiais (bb.com.br e Bacen) com URLs.' },
  { label: 'Pix no BB (limites e tarifas + fontes)', text: 'Quais os limites e eventuais tarifas do Pix no Banco do Brasil? Liste fontes (bb.com.br, bacen) com URLs.' },
  { label: 'Seguro Auto BB (coberturas + fontes)', text: 'Quais coberturas do Seguro Auto BB Seguros e o que observar? Liste fontes oficiais com URLs (bbseguros.com.br).' },
  { label: 'Conta Universitária BB (benefícios + fontes)', text: 'Quais os benefícios e tarifas da conta universitária do Banco do Brasil? Cite fontes oficiais com URLs.' },
  { label: 'Tesouro Direto via BB (taxas + fontes)', text: 'Quais taxas de custódia/corretagem para investir em Tesouro via Banco do Brasil? Cite fontes (bb.com.br, tesourodireto.com.br) com URLs.' },
  { label: 'Canais e atendimento BB (horários + fontes)', text: 'Quais canais oficiais do Banco do Brasil e horários de atendimento? Liste fontes com URLs de bb.com.br.' },
]

const ENGINE_OPTIONS = [
  { label: 'OpenAI GPT-5 (web search)', name: 'openai', config_json: { model: 'gpt-5', web_search: true } },
  { label: 'OpenAI GPT-4.1 (web search)', name: 'openai', config_json: { model: 'gpt-4.1', web_search: true } },
  { label: 'Gemini 2.5 Pro (web search)', name: 'gemini', config_json: { model: 'gemini-2.5-pro' } },
  { label: 'Gemini 2.5 Flash (web search)', name: 'gemini', config_json: { model: 'gemini-2.5-flash' } },
  { label: 'Perplexity Sonar Pro (web search)', name: 'perplexity', config_json: { model: 'sonar-pro' } },
  { label: 'Google SERP (SerpAPI)', name: 'google_serp', config_json: { use_serpapi: true } },
]

export default function Runs() {
  const [runs, setRuns] = useState<RunItem[]>([])
  const [showModal, setShowModal] = useState(false)
  const [engineFilter, setEngineFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [query, setQuery] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState<string>('')

  const fetchRuns = async () => {
    const params: any = {}
    if (projectId) params.project_id = projectId
    if (subprojectId) params.subproject_id = subprojectId
    if (engineFilter) params.engine = engineFilter
    if (statusFilter) params.status = statusFilter
    const res = await axios.get(`${API}/runs`, { params })
    setRuns(res.data)
  }

  useEffect(() => {
    axios.get(`${API}/projects`).then(r => {
      setProjects(r.data)
      if (!projectId && r.data[0]?.id) {
        setProjectId(r.data[0].id)
        localStorage.setItem('project_id', r.data[0].id)
      }
    })
  }, [])

  useEffect(() => { fetchRuns() }, [engineFilter, statusFilter, subprojectId])
  useEffect(() => { const t = setInterval(fetchRuns, 5000); return () => clearInterval(t) }, [engineFilter, statusFilter, subprojectId])
  useEffect(() => { if (projectId) fetchRuns() }, [projectId])

  useEffect(() => {
    if (!projectId) return
    localStorage.setItem('project_id', projectId)
    axios.get(`${API}/projects/${projectId}/subprojects`).then(r => setSubprojects(r.data))
  }, [projectId])

  const engines = useMemo(() => Array.from(new Set(runs.map((r) => r.engine))), [runs])
  const filtered = useMemo(() => {
    const list = runs.filter((r) => (!query || r.id.includes(query)))
    return list
  }, [runs, query])

  return (
    <div className="space-y-3">
      <Toaster richColors position="top-right" />
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Runs</h1>
        <Button variant="outline" size="sm" onClick={() => { fetchRuns().then(()=>toast.success('Atualizado')) }} className="ml-2"><RefreshCw className="h-4 w-4" /></Button>
        <Button className="ml-auto" onClick={() => setShowModal(true)}><Plus className="h-4 w-4 mr-1" /> Nova Run</Button>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <Select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
        </Select>
        <Select value={subprojectId} onChange={(e) => setSubprojectId(e.target.value)}>
          <option value="">Todos os subprojetos</option>
          {subprojects.map(sp => <option key={sp.id} value={sp.id}>{sp.name}</option>)}
        </Select>
        <Select value={engineFilter} onChange={(e) => setEngineFilter(e.target.value)}>
          <option value="">Todas as engines</option>
          {engines.map((e) => <option key={e} value={e}>{e}</option>)}
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Todos os status</option>
          {['queued','running','completed','failed'].map((s) => <option key={s} value={s}>{s}</option>)}
        </Select>
        <Input placeholder="Buscar por ID" value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-neutral-500 text-xs">
              <Th>ID</Th>
              <Th>Engine</Th>
              <Th>Status</Th>
              <Th>Início</Th>
              <Th>Fim</Th>
              <Th>ZCRS</Th>
              <Th>AMR</Th>
              <Th>DCR</Th>
              <Th>Template</Th>
              <Th>Subprojeto</Th>
              <Th>Custo</Th>
              <Th>Tokens</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id} className="border-t border-neutral-200 dark:border-neutral-800">
                <Td><a className="text-blue-600" href={`/runs/${r.id}`}>{r.id}</a></Td>
                <Td>{r.engine}</Td>
                <Td>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    r.status === 'completed' ? 'bg-green-100 text-green-800' :
                    r.status === 'failed' ? 'bg-red-100 text-red-800' :
                    r.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {r.status}
                  </span>
                </Td>
                <Td>{r.started_at || '-'}</Td>
                <Td>{r.finished_at || '-'}</Td>
                <Td>{r.zcrs?.toFixed(1) ?? '-'}</Td>
                <Td>{r.amr_flag ? '1' : '0'}</Td>
                <Td>{r.dcr_flag ? '1' : '0'}</Td>
                <Td>{r.template_name || '-'}</Td>
                <Td>{r.subproject_name || '-'}</Td>
                <Td>{typeof r.cost_usd === 'number' ? `$${r.cost_usd.toFixed(4)}` : '-'}</Td>
                <Td>{typeof r.tokens_total === 'number' ? r.tokens_total : '-'}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showModal && <NewRunModal onClose={() => { setShowModal(false); fetchRuns() }} />}
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="text-left p-2">{children}</th>
}
function Td({ children }: { children: React.ReactNode }) {
  return <td className="p-2">{children}</td>
}

function NewRunModal({ onClose }: { onClose: () => void }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<string>(() => localStorage.getItem('project_id') || '')
  const [subprojects, setSubprojects] = useState<Subproject[]>([])
  const [subprojectId, setSubprojectId] = useState<string>('')
  const [templateIdx, setTemplateIdx] = useState(0)
  const [engineIdx, setEngineIdx] = useState(0)
  const [cycles, setCycles] = useState(1)
  const [creating, setCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState('Projeto Banco – BR pt-BR')
  const [templates, setTemplates] = useState<{ id: string; name: string; text: string; category: string }[]>([])
  const [category, setCategory] = useState<string>('')

  useEffect(() => {
    axios.get(`${API}/projects`).then((r) => {
      setProjects(r.data)
      if (!projectId && r.data[0]?.id) setProjectId(r.data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!projectId) return
    axios.get(`${API}/projects/${projectId}/subprojects`).then(r => setSubprojects(r.data))
    const params = category ? { params: { category } } : undefined
    axios.get(`${API}/projects/${projectId}/templates`, params).then(r => setTemplates(r.data))
  }, [projectId, category])

  const createQuickProject = async () => {
    const res = await axios.post(`${API}/projects`, { name: newProjectName, country: 'BR', language: 'pt-BR', timezone: 'America/Sao_Paulo' })
    const id = res.data.id as string
    setProjects((prev) => [{ id, name: newProjectName }, ...prev])
    setProjectId(id)
    localStorage.setItem('project_id', id)
  }

  const submit = async () => {
    try {
      if (!projectId) throw new Error('Selecione ou crie um projeto')
      localStorage.setItem('project_id', projectId)
      setCreating(true)

      // se escolheu template, usar direto; senão, fallback para TEMPLATES local
      if (templates.length) {
        const t = templates[templateIdx]
        const promptRes = await axios.post(`${API}/projects/${projectId}/prompts`, {
          name: `Template: ${t.name}`,
          text: t.text,
          intent: 'Informacional',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.data.id
        const pvRes = await axios.get(`${API}/prompts/${promptId}/versions`)
        const versions = pvRes.data as any[]
        const pvId = versions[versions.length - 1].id
        const engine = ENGINE_OPTIONS[engineIdx]
        await axios.post(`${API}/runs`, {
          project_id: projectId,
          prompt_version_id: pvId,
          engines: [{ name: engine.name, region: 'BR', device: 'desktop', config_json: engine.config_json }],
          cycles,
          subproject_id: subprojectId || null,
        })
      } else {
        const promptRes = await axios.post(`${API}/projects/${projectId}/prompts`, {
          name: `Template: ${TEMPLATES[templateIdx].label}`,
          text: TEMPLATES[templateIdx].text,
          intent: 'Informacional',
          persona: 'Analista',
          variables: {},
        })
        const promptId = promptRes.data.id
        const pvRes = await axios.get(`${API}/prompts/${promptId}/versions`)
        const versions = pvRes.data as any[]
        const pvId = versions[versions.length - 1].id
        const engine = ENGINE_OPTIONS[engineIdx]
        await axios.post(`${API}/runs`, {
          project_id: projectId,
          prompt_version_id: pvId,
          engines: [{ name: engine.name, region: 'BR', device: 'desktop', config_json: engine.config_json }],
          cycles,
          subproject_id: subprojectId || null,
        })
      }

      toast.success('Nova run criada')
      onClose()
      window.location.href = '/runs'
    } catch (e: any) {
      toast.error('Erro ao criar run: ' + e.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 grid place-items-center p-4">
      <div className="bg-white dark:bg-neutral-900 rounded-lg p-4 w-[min(820px,100%)] space-y-3 border border-neutral-200 dark:border-neutral-800">
        <h2 className="text-lg font-semibold">Nova Run</h2>
        <div className="grid gap-3">
          <div className="grid gap-1">
            <div className="text-sm text-neutral-500">Projeto</div>
            <div className="flex gap-2 items-center">
              <Select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="min-w-[280px]">
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name} ({p.id})</option>
                ))}
              </Select>
              <Button variant="secondary" onClick={createQuickProject}>Criar rápido</Button>
            </div>
          </div>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Subprojeto (opcional)</div>
            <Select value={subprojectId} onChange={(e) => setSubprojectId(e.target.value)}>
              <option value="">—</option>
              {subprojects.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
          </label>
          <div className="grid gap-1">
            <div className="text-sm text-neutral-500">Categoria de Template</div>
            <Input placeholder="(opcional) Filtrar categoria" value={category} onChange={(e) => setCategory(e.target.value)} />
          </div>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Template</div>
            <Select value={String(templateIdx)} onChange={(e) => setTemplateIdx(parseInt(e.target.value))}>
              {templates.length ? templates.map((t, i) => (<option key={t.id} value={i}>{t.category} • {t.name}</option>)) : TEMPLATES.map((t, i) => (<option key={i} value={i}>{t.label}</option>))}
            </Select>
          </label>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Engine</div>
            <Select value={String(engineIdx)} onChange={(e) => setEngineIdx(parseInt(e.target.value))}>
              {ENGINE_OPTIONS.map((e, i) => (
                <option key={i} value={i}>{e.label}</option>
              ))}
            </Select>
          </label>
          <label className="grid gap-1">
            <div className="text-sm text-neutral-500">Cycles</div>
            <Input type="number" min={1} value={String(cycles)} onChange={(e) => setCycles(parseInt(e.target.value || '1'))} className="w-24" />
          </label>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button onClick={submit} disabled={creating}>{creating ? 'Criando…' : 'Criar'}</Button>
        </div>
      </div>
    </div>
  )
}
