// @ts-nocheck
import React, { useEffect, useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { getGeoDashboard, type GeoDashboard, getSubprojects, getProjects, type Project, getMonitors, getTemplates, type Template } from '../lib/api'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'
import { AlertTriangle, TrendingUp, AlertCircle, CheckCircle2, Filter, Calendar, Building2, Info, Sparkles, Target, Layers, XCircle } from 'lucide-react'
import { formatNumberCompact } from '../lib/utils'

export default function GeoDashboardPOC() {
  const { projectId: routeProjectId } = useParams<{ projectId?: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string>(routeProjectId || searchParams.get('project_id') || '')
  const [dashboard, setDashboard] = useState<GeoDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters state
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') || '')
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') || '')
  const [subprojectId, setSubprojectId] = useState(searchParams.get('subproject_id') || '')
  const [category, setCategory] = useState(searchParams.get('category') || '')
  const [monitorId, setMonitorId] = useState(searchParams.get('monitor_id') || '')

  const [subprojects, setSubprojects] = useState<any[]>([])
  const [monitors, setMonitors] = useState<any[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [showMethodology, setShowMethodology] = useState<boolean>(false)
  
  // Filtro de categoria para Entidades Detectadas
  const [selectedEntityCategory, setSelectedEntityCategory] = useState<string>('all')
  
  // Flag de expansão da checklist
  const [showAllChecklist, setShowAllChecklist] = useState<boolean>(false)
  const [metadataModal, setMetadataModal] = useState<{open: boolean; domain: string; column: string; details: any}>({open: false, domain: '', column: '', details: null})
  const [isCrawling, setIsCrawling] = useState<boolean>(false)

  useEffect(() => {
    getProjects().then(setProjects).catch(console.error)
  }, [])

  useEffect(() => {
    if (!selectedProjectId) return

    getSubprojects(selectedProjectId).then(setSubprojects).catch(console.error)
    getMonitors(selectedProjectId).then(setMonitors).catch(console.error)
    getTemplates(selectedProjectId)
      .then((templates: Template[]) => {
        const unique = Array.from(new Set((templates || []).map((tpl) => tpl.category).filter(Boolean))) as string[]
        setCategories(unique)
      })
      .catch(console.error)
  }, [selectedProjectId])

  const loadDashboard = async () => {
    if (!selectedProjectId) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const filters: any = {}
      if (dateFrom) filters.date_from = dateFrom
      if (dateTo) filters.date_to = dateTo
      if (subprojectId) filters.subproject_id = subprojectId
      if (category) filters.category = category
      if (monitorId) filters.monitor_id = monitorId

      const data = await getGeoDashboard(selectedProjectId, filters)
      setDashboard(data)
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dashboard')
      console.error('Error loading GEO dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedProjectId) {
      loadDashboard()
    }
  }, [selectedProjectId])

  const applyFilters = () => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (subprojectId) params.set('subproject_id', subprojectId)
    if (category) params.set('category', category)
    if (monitorId) params.set('monitor_id', monitorId)
    setSearchParams(params)
    loadDashboard()
  }

  // Show project selector if no project selected
  if (!selectedProjectId) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>Selecione um Projeto</CardTitle>
            <CardDescription>
              Escolha um projeto para visualizar o Dashboard POC
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {projects.map((project) => (
                <Card
                  key={project.id}
                  className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  onClick={() => {
                    setSelectedProjectId(project.id)
                    navigate(`/geo-poc/${project.id}`)
                  }}
                >
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-3">
                      <Building2 className="w-8 h-8 text-blue-600" />
                      <div>
                        <h3 className="font-semibold">{project.name}</h3>
                        <p className="text-xs text-gray-500">{project.id}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">{error}</p>
          <Button onClick={loadDashboard} className="mt-4">Tentar novamente</Button>
        </div>
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="container mx-auto p-6">
        <p className="text-gray-500">Nenhum dado disponível</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <div className="container mx-auto px-6 py-10 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-blue-500 uppercase text-xs tracking-[0.35em] font-semibold">
              <Sparkles className="w-4 h-4" /> SERP Radar POC
            </div>
            <h1 className="text-3xl md:text-4xl font-semibold mt-2 text-slate-900">Visão Multidimensional de SERP</h1>
            <p className="text-sm text-slate-500 mt-3">
              Monitoramento agregador das experiências SERP e Zero-Click em {dashboard.total_runs} runs.
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="ghost" onClick={loadDashboard} className="border border-slate-300 text-slate-600 hover:bg-slate-100">
              Atualizar dados
            </Button>
            <Button onClick={loadDashboard} className="bg-blue-500 hover:bg-blue-600 text-white">
              Reprocessar SERP
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="bg-white/90 border border-slate-200 shadow-lg shadow-slate-900/10 dark:bg-slate-900/60 dark:border-slate-800 dark:shadow-slate-900/40 transition-colors">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-slate-700 dark:text-slate-200">
                  <Filter className="w-5 h-5 text-blue-500 dark:text-blue-300" />
                  Painel de Filtros
                </CardTitle>
                <CardDescription className="text-slate-500 dark:text-slate-400 mt-1">
                  Ajuste o contexto por período, produto (tema), categoria do prompt e monitor.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
              <div className="rounded-xl px-4 py-3 bg-slate-100 border border-slate-200 text-slate-700 dark:bg-slate-900/40 dark:border-slate-800 dark:text-slate-300">
                <label className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  <Calendar className="w-3.5 h-3.5" /> Data inicial
                </label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/40 text-slate-900 dark:bg-slate-950/60 dark:border-slate-800 dark:text-slate-100"
                />
              </div>
              <div className="rounded-xl px-4 py-3 bg-slate-100 border border-slate-200 text-slate-700 dark:bg-slate-900/40 dark:border-slate-800 dark:text-slate-300">
                <label className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  <Calendar className="w-3.5 h-3.5" /> Data final
                </label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/40 text-slate-900 dark:bg-slate-950/60 dark:border-slate-800 dark:text-slate-100"
                />
              </div>
              <div className="rounded-xl px-4 py-3 bg-slate-100 border border-slate-200 text-slate-700 dark:bg-slate-900/40 dark:border-slate-800 dark:text-slate-300">
                <label className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  <Layers className="w-3.5 h-3.5" /> Produto / Tema
                </label>
                <select
                  value={subprojectId}
                  onChange={(e) => setSubprojectId(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/40 text-slate-900 dark:bg-slate-950/60 dark:border-slate-800 dark:text-slate-100"
                >
                  <option value="">Todos</option>
                  {subprojects.map((sp) => (
                    <option key={sp.id} value={sp.id}>
                      {sp.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="rounded-xl px-4 py-3 bg-slate-100 border border-slate-200 text-slate-700 dark:bg-slate-900/40 dark:border-slate-800 dark:text-slate-300">
                <label className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  <Target className="w-3.5 h-3.5" /> Categoria (Prompt)
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/40 text-slate-900 dark:bg-slate-950/60 dark:border-slate-800 dark:text-slate-100"
                >
                  <option value="">Todas</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>
              <div className="rounded-xl px-4 py-3 bg-slate-100 border border-slate-200 text-slate-700 dark:bg-slate-900/40 dark:border-slate-800 dark:text-slate-300">
                <label className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  <Building2 className="w-3.5 h-3.5" /> Monitor
                </label>
                <select
                  value={monitorId}
                  onChange={(e) => setMonitorId(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400/40 text-slate-900 dark:bg-slate-950/60 dark:border-slate-800 dark:text-slate-100"
                >
                  <option value="">Todos</option>
                  {monitors.map((monitor) => (
                    <option key={monitor.id} value={monitor.id}>
                      {monitor.name || monitor.id}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div className="text-xs text-slate-500 dark:text-slate-400">
                Última atualização capturada: {new Date().toLocaleString()}
              </div>
              <div className="flex gap-3">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setDateFrom('')
                    setDateTo('')
                    setSubprojectId('')
                    setCategory('')
                    setMonitorId('')
                    setSearchParams(new URLSearchParams())
                    loadDashboard()
                  }}
                  className="border border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Limpar
                </Button>
                <Button onClick={applyFilters} className="bg-blue-500 hover:bg-blue-600 text-white px-6">
                  Aplicar filtros
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>


      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {dashboard.kpis.map((kpi, i) => (
          <Card key={i} className="hover:shadow-lg transition-shadow">
            <CardContent className="pt-6">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-3 uppercase tracking-wide">
                {kpi.label}
              </div>
              <div className="flex items-baseline gap-2">
                <div className="text-3xl font-bold text-gray-900 dark:text-white">
                  {typeof kpi.value === 'number' && kpi.unit === 'score'
                    ? kpi.value.toFixed(1)
                    : kpi.value}
                </div>
                {kpi.total !== undefined && kpi.unit === 'runs' && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    / {kpi.total}
                  </div>
                )}
              </div>
              {kpi.total !== undefined && kpi.unit === 'runs' && (
                <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full"
                    style={{ width: `${(Number(kpi.value) / kpi.total) * 100}%` }}
                  />
                </div>
              )}
              {kpi.delta !== undefined && kpi.delta !== null && typeof kpi.delta === 'number' && (
                <div className={`text-xs mt-2 font-medium ${kpi.delta > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {kpi.delta > 0 ? '↑' : '↓'} {Math.abs(kpi.delta).toFixed(1)}%
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.35fr_1fr] gap-6 items-start">
        {/* Radar Chart */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Radar - Comparação Multidimensional</CardTitle>
            <CardDescription>
              Comparação de métricas IM-SEO, IA Ready, E-E-A-T e mais
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {dashboard.radar.length > 0 ? (() => {
              const radarData = dashboard.radar[0]
              const dimensions = radarData.dimensions || []
              const dimensionDescriptions: Record<string, string> = {
                'IM-SEO': 'Índice de Maturidade em SEO. Combina fatores técnicos (indexabilidade, sitemaps, robots), autoridade e performance orgânica em escala 0-100.',
                'IM-SEO/IA': 'Variação do IM-SEO focada em prompts e respostas de IA. Avalia presença em resultados assistidos (AI Overviews), snippets enriquecidos e adaptabilidade para assistentes.',
                'IRZC': 'Índice de Relevância para Zero-Click (0-100). Mede o quanto a marca aparece em experiências que respondem o usuário sem clique (featured snippets, painéis de conhecimento, respostas IA).',
                'E-E-A-T': 'Pontuação de Experience, Expertise, Authority e Trust. Analisa sinais de autoria, credibilidade, backlinks e menções qualificadas.',
                'Core Web Vitals': 'Média ponderada de LCP, FID/INP e CLS. Representa a experiência de carregamento, interatividade e estabilidade visual.',
                'IA Ready': 'Score de preparação para IA. Considera presença de listas, FAQs, schema.org, dados estruturados e blocos que alimentam modelos.',
              }
              const totals = dimensions.reduce((sum, dim) => sum + dim.value, 0)
              const average = dimensions.length ? totals / dimensions.length : 0
              const strongest = dimensions.reduce((acc, dim) => (dim.value > acc.value ? dim : acc), dimensions[0])
              const weakest = dimensions.reduce((acc, dim) => (dim.value < acc.value ? dim : acc), dimensions[0])
              const strengths = dimensions.filter((dim) => dim.value >= 65).map((dim) => dim.name)
              const improvement = dimensions.filter((dim) => dim.value < 45).map((dim) => dim.name)

              return (
                <>
                  <div className="flex flex-col md:flex-row gap-8">
                    <div className="flex-1">
                      <ResponsiveContainer width="100%" height={360}>
                        <RadarChart data={dimensions}>
                          <PolarGrid stroke="#e5e7eb" />
                          <PolarAngleAxis
                            dataKey="name"
                            tick={{ fill: '#6b7280', fontSize: 12 }}
                          />
                          <PolarRadiusAxis
                            angle={90}
                            domain={[0, 100]}
                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                            tickCount={6}
                          />
                          <Radar
                            name={radarData.bank}
                            dataKey="value"
                            stroke="#3b82f6"
                            fill="#3b82f6"
                            fillOpacity={0.45}
                            strokeWidth={2}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: 'rgba(255,255,255,0.95)',
                              border: '1px solid #e5e7eb',
                              borderRadius: '6px',
                              padding: '8px 12px'
                            }}
                            formatter={(value: number) => [`${value.toFixed(1)}`, 'Score']}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="md:w-60 space-y-2">
                      <h4 className="font-semibold text-sm mb-2 text-gray-700 dark:text-gray-300">Dimensões</h4>
                      {dimensions.map((dim, idx) => (
                        <div key={idx} className="flex justify-between items-center gap-3 text-sm">
                          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                            <span>{dim.name}</span>
                            <div className="relative group">
                              <Info className="w-3.5 h-3.5 text-blue-500 cursor-help" />
                              <div className="absolute z-40 hidden group-hover:block top-1/2 left-full ml-2 -translate-y-1/2 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg">
                                <div className="font-semibold text-blue-200 mb-1">{dim.name}</div>
                                <p className="text-gray-200 leading-relaxed">{dimensionDescriptions[dim.name] || 'Indicador composto. Consulte a metodologia para detalhes completos.'}</p>
                                <div className="absolute top-1/2 left-0 -ml-2 transform -translate-y-1/2 border-8 border-transparent border-r-gray-900"></div>
                              </div>
                            </div>
                          </div>
                          <span className="font-semibold text-gray-900 dark:text-white">{dim.value.toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="rounded-xl border border-gray-200/70 dark:border-gray-800 bg-white/80 dark:bg-gray-900/30 p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 font-semibold mb-1">Pontuação média</p>
                      <p className="text-2xl font-semibold text-gray-900 dark:text-white">{average.toFixed(1)}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Média das {dimensions.length} dimensões avaliadas</p>
                    </div>
                    <div className="rounded-xl border border-emerald-200/70 dark:border-emerald-900/40 bg-emerald-50/70 dark:bg-emerald-900/10 p-4">
                      <p className="text-xs uppercase tracking-wide text-emerald-700 dark:text-emerald-300 font-semibold mb-1">Principal destaque</p>
                      <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-100">{strongest?.name || '—'}</p>
                      <p className="text-2xl font-semibold text-emerald-700 dark:text-emerald-200">{strongest?.value?.toFixed(1)}</p>
                      <p className="text-xs text-emerald-700/80 dark:text-emerald-200/80 mt-2">
                        {strengths.length > 0 ? `Também fortes em ${strengths.join(', ')}` : 'Nenhum outro destaque acima de 65'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-orange-200/70 dark:border-orange-900/40 bg-orange-50/70 dark:bg-orange-900/10 p-4">
                      <p className="text-xs uppercase tracking-wide text-orange-700 dark:text-orange-300 font-semibold mb-1">Oportunidade</p>
                      <p className="text-sm font-semibold text-orange-900 dark:text-orange-100">{weakest?.name || '—'}</p>
                      <p className="text-2xl font-semibold text-orange-700 dark:text-orange-200">{weakest?.value?.toFixed(1)}</p>
                      <p className="text-xs text-orange-700/80 dark:text-orange-200/80 mt-2">
                        {improvement.length > 0 ? `Foco recomendado em ${improvement.join(', ')}` : 'Nenhuma dimensão abaixo de 45 pontos'}
                      </p>
                    </div>
                  </div>
                </>
              )
            })() : (
              <div className="text-center text-gray-500 py-8">Sem dados disponíveis</div>
            )}
          </CardContent>
        </Card>

        {/* Brand Positioning & Rankings */}
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Posicionamento de Marca</CardTitle>
            <CardDescription>
              Top 10 domínios mais citados nas respostas analisadas
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 sm:px-6">
            {(() => {
              const allBrands = dashboard.positioning.brand_ranking || []
              const brands = allBrands.slice(0, 10)
              const totalMentionsTop = brands.reduce((acc, item) => acc + (item.mentions ?? 0), 0)
              const totalMentionsOverall = allBrands.reduce((acc, item) => acc + (item.mentions ?? 0), 0)
              const maxMentions = Math.max(...brands.map(item => item.mentions ?? 0), 1)

              return (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400">
                    <span>
                      {totalMentionsTop} menções dentro do Top {brands.length}{' '}
                      <span className="text-gray-400">• {totalMentionsOverall} no total analisado</span>
                    </span>
                    <span className="hidden sm:inline">Barras mostram participação relativa dentro do Top {brands.length}</span>
                  </div>
                  <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                    {brands.map((brand) => {
                      const share = totalMentionsTop > 0 ? ((brand.mentions ?? 0) / totalMentionsTop) * 100 : 0
                      const dominance = Math.max(((brand.mentions ?? 0) / maxMentions) * 100, 6)
                      const isTop3 = brand.rank <= 3
                      return (
                        <div
                          key={brand.rank}
                          className={`rounded-2xl border bg-white/90 dark:bg-gray-900/40 backdrop-blur-sm transition-all hover:shadow-sm ${
                            isTop3 ? 'border-blue-200/70 dark:border-blue-900/50' : 'border-gray-200/70 dark:border-gray-800'
                          }`}
                        >
                          <div className="px-4 py-3 md:px-5">
                            <div className="flex items-center gap-3">
                              <div className={`flex-shrink-0 w-9 h-9 md:w-10 md:h-10 rounded-full flex items-center justify-center text-xs font-semibold ${
                                isTop3 ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'
                              }`}>
                                #{brand.rank}
                              </div>
                              <div className="min-w-0 flex-1 space-y-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="text-sm font-semibold text-gray-900 dark:text-white">
                                    {brand.brand}
                                  </span>
                                  {isTop3 && (
                                    <Badge variant="secondary" className="text-[11px] bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200">
                                      Top {brand.rank}
                                    </Badge>
                                  )}
                                  <Badge variant="outline" className="text-[11px] border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-300">
                                    {share.toFixed(1)}% share
                                  </Badge>
                                </div>
                                {brand.sample_url && (
                                  <a
                                    href={brand.sample_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block truncate text-xs text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-300"
                                  >
                                    {brand.sample_url.length > 80 ? brand.sample_url.substring(0, 80) + '…' : brand.sample_url}
                                  </a>
                                )}
                              </div>
                              <div className="text-right">
                                <div className="text-sm font-semibold text-gray-900 dark:text-white">{brand.mentions}</div>
                                <div className="text-[11px] text-gray-500 dark:text-gray-400">menções</div>
                              </div>
                            </div>
                            <div className="mt-2">
                              <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${isTop3 ? 'bg-blue-500' : 'bg-gray-500/70 dark:bg-gray-400/70'}`}
                                  style={{ width: `${dominance}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })()}
          </CardContent>
        </Card>

      </div>

      {/* Keywords & Entities */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Palavra-Chave Cloud</CardTitle>
            <CardDescription>Termos mais frequentes nas citações</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg min-h-[200px] items-center justify-center">
              {(() => {
                const words = dashboard.keywords_entities.word_cloud.slice(0, 30)
                // Encontrar min e max para escala
                const frequencies = words.map(w => w.frequency)
                const maxFreq = Math.max(...frequencies, 1)
                const minFreq = Math.min(...frequencies, 1)
                const range = maxFreq - minFreq || 1

                return words.map((word, i) => {
                  // Escala proporcional: 14px (menor) a 40px (maior)
                  const normalized = (word.frequency - minFreq) / range
                  const fontSize = 14 + (normalized * 26) // 14 + 0-26 = 14-40px

                  // Opacidade baseada em posição relativa
                  const opacity = 0.6 + (normalized * 0.4) // 0.6-1.0

                  return (
                    <span
                      key={i}
                      className="cursor-default hover:text-blue-600 dark:hover:text-blue-400 transition-colors font-medium"
                      style={{
                        fontSize: `${fontSize}px`,
                        fontWeight: normalized > 0.7 ? 'bold' : normalized > 0.4 ? '600' : '500',
                        opacity: opacity,
                        color: normalized > 0.7 ? '#3b82f6' : normalized > 0.4 ? '#6366f1' : undefined
                      }}
                      title={`${word.frequency} menções`}
                    >
                      {word.text}
                    </span>
                  )
                })
              })()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Entidades Detectadas</CardTitle>
                <CardDescription>Top 10 domínios por tipo de citação</CardDescription>
              </div>
              {/* Filtro compacto */}
              {(() => {
                const allEntities = dashboard.keywords_entities.entities
                const categories = ['all', ...Array.from(new Set(allEntities.map(e => e.type)))]
                
                return (
                  <select
                    value={selectedEntityCategory}
                    onChange={(e) => setSelectedEntityCategory(e.target.value)}
                    className="px-3 py-1.5 text-sm border rounded-md bg-white dark:bg-gray-800 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">Todas as categorias</option>
                    {categories.filter(c => c !== 'all').map((cat) => (
                      <option key={cat} value={cat}>
                        {cat} ({allEntities.filter(e => e.type === cat).length})
                      </option>
                    ))}
                  </select>
                )
              })()}
            </div>
          </CardHeader>
          <CardContent>
            {(() => {
              const allEntities = dashboard.keywords_entities.entities
              
              const filteredEntities = selectedEntityCategory === 'all' 
                ? allEntities 
                : allEntities.filter(e => e.type === selectedEntityCategory)
              
              const entities = filteredEntities.slice(0, 10)
              const maxMentions = Math.max(...entities.map(e => e.mentions), 1)
              
              return (
                <>
                  
                  <div className="space-y-3 max-h-[400px] overflow-y-auto">
                    {entities.map((entity, i) => {
                      const percentage = (entity.mentions / maxMentions) * 100
                      
                      return (
                        <div
                          key={i}
                          className="space-y-2 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="font-semibold text-sm truncate">{entity.entity}</div>
                              <div className="text-xs text-gray-500">{entity.type}</div>
                            </div>
                            <Badge variant="secondary" className="ml-2 font-bold">{entity.mentions}</Badge>
                          </div>
                          
                          {/* Barra de progresso visual */}
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                            <div
                              className="h-2.5 rounded-full transition-all duration-500"
                              style={{
                                width: `${percentage}%`,
                                background: i === 0 ? 'linear-gradient(to right, #3b82f6, #1d4ed8)' :
                                           i === 1 ? 'linear-gradient(to right, #6366f1, #4f46e5)' :
                                           i === 2 ? 'linear-gradient(to right, #8b5cf6, #7c3aed)' :
                                           'linear-gradient(to right, #94a3b8, #64748b)'
                              }}
                            />
                          </div>
                          
                          {/* Percentual relativo */}
                          <div className="flex justify-between items-center text-xs text-gray-500">
                            <span>{percentage.toFixed(0)}% do máximo</span>
                            {i < 3 && <span className="text-blue-600 dark:text-blue-400 font-semibold">Top {i + 1}</span>}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </>
              )
            })()}
          </CardContent>
        </Card>
      </div>

      {/* Panorama */}
      <Card>
        <CardHeader>
          <CardTitle>Panorama - Visão Geral</CardTitle>
          <CardDescription>
            Métricas agregadas e comparações entre AI Overview, PAA e Knowledge Panel
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="rounded-xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/60 dark:bg-blue-900/10 p-4">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-blue-500/10 text-blue-600 dark:text-blue-300 rounded-full">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-blue-900 dark:text-blue-200">Como interpretar este painel</p>
                  <p className="text-xs text-blue-700/80 dark:text-blue-200/80">
                    Uma visão rápida da presença das features da SERP nos seus runs. Clique abaixo para ver a metodologia detalhada.
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="border-blue-200 dark:border-blue-900/40 text-blue-700 dark:text-blue-200"
                onClick={() => setShowMethodology((prev) => !prev)}
              >
                {showMethodology ? 'Ocultar metodologia' : 'Ver metodologia'}
              </Button>
            </div>
            {showMethodology && (
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-blue-800 dark:text-blue-200">
                <div className="space-y-1">
                  <p className="font-semibold">IM-SEO/IA vs IM-SEO</p>
                  <p>Diferença entre o score IM-SEO tradicional e o score otimizado para IA. Valores positivos indicam melhor performance em buscas por IA.</p>
                </div>
                <div className="space-y-1">
                  <p className="font-semibold">Total Runs</p>
                  <p>Número total de execuções de análise no período filtrado.</p>
                </div>
                <div className="space-y-1">
                  <p className="font-semibold">AI Overview</p>
                  <p>Quantidade de runs onde o Google exibiu resposta gerada por IA no topo da SERP.</p>
                </div>
                <div className="space-y-1">
                  <p className="font-semibold">PAA (People Also Ask)</p>
                  <p>Runs com presença da seção "As pessoas também perguntam" nos resultados.</p>
                </div>
                <div className="space-y-1 md:col-span-2">
                  <p className="font-semibold">Knowledge Panel</p>
                  <p>Painel lateral do Google com informações estruturadas sobre entidades (empresas, pessoas, lugares). Aparece apenas para queries sobre entidades conhecidas; perguntas informativas geralmente não geram Knowledge Panel.</p>
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {dashboard.panorama.cards.map((card, i) => (
              <div
                key={i}
                className="rounded-xl border border-gray-200/70 dark:border-gray-700/60 bg-white/70 dark:bg-gray-900/30 backdrop-blur-sm p-4 shadow-sm"
              >
                <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                  {card.label}
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                  {typeof card.value === 'number' ? card.value.toFixed(1) : card.value}
                </div>
                {card.delta !== undefined && card.delta !== null && typeof card.delta === 'number' && (
                  <div className={`text-xs font-medium ${card.delta > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                    {card.delta > 0 ? '↑' : '↓'} {Math.abs(card.delta).toFixed(2)}
                  </div>
                )}
                {card.supporting && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">
                    {card.supporting}
                  </div>
                )}
              </div>
            ))}
          </div>

          {dashboard.panorama.chart.length > 0 && (
            <div className="mt-2">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold">Distribuição de Features SERP</h4>
                {dashboard.panorama.cards.find(c => c.label === 'Knowledge Panel')?.value === 0 && (
                  <div className="text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-3 py-1 rounded-md border border-orange-200 dark:border-orange-800">
                    Knowledge Panel não detectado — comum para queries informativas
                  </div>
                )}
              </div>
              <div className="h-[340px] md:h-[380px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={dashboard.panorama.chart}
                    barCategoryGap="58%"
                    barGap={12}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="bank"
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                    />
                    <YAxis
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'rgba(255,255,255,0.95)',
                        border: '1px solid #e5e7eb',
                        borderRadius: '6px'
                      }}
                    />
                    <Legend wrapperStyle={{ paddingTop: '12px' }} />
                    <Bar dataKey="ai_overview_count" name="AI Overview" fill="#3b82f6" radius={[6, 6, 0, 0]} maxBarSize={28} />
                    <Bar dataKey="paa_count" name="PAA" fill="#10b981" radius={[6, 6, 0, 0]} maxBarSize={28} />
                    <Bar dataKey="kp_count" name="Knowledge Panel" fill="#f59e0b" radius={[6, 6, 0, 0]} maxBarSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Web Structure Checklist */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Estrutura Web - Checklist de Metadados</CardTitle>
              <CardDescription>
                Sinalização dos principais metadados nas páginas oficiais dos bancos citados pela IA
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={isCrawling}
              onClick={async () => {
                if (!selectedProjectId) {
                  alert('Selecione um projeto primeiro')
                  return
                }
                
                setIsCrawling(true)
                try {
                  console.log('Iniciando crawling para projeto:', selectedProjectId)
                  const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/projects/${selectedProjectId}/crawl-citations?max_urls=50`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                  })
                  
                  if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
                  }
                  
                  const result = await response.json()
                  console.log('Resultado do crawling:', result)
                  alert(`Crawling concluído!\n✅ Sucesso: ${result.success}\n❌ Erro: ${result.error}\n\nRecarregando dashboard...`)
                  await loadDashboard()
                } catch (error) {
                  console.error('Erro no crawling:', error)
                  alert(`Erro ao fazer crawling das URLs:\n${error}`)
                } finally {
                  setIsCrawling(false)
                }
              }}
            >
              {isCrawling ? '⏳ Crawling...' : 'Atualizar Metadados'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {(() => {
            const allChecklist = dashboard.web_structure || []
            const checklist = showAllChecklist ? allChecklist : allChecklist.slice(0, 6)

            if (checklist.length === 0) {
              return (
                <div className="text-center py-8 text-gray-500">
                  <p>Nenhuma URL oficial disponível nas citações.</p>
                  <p className="text-sm mt-2">Assim que houver crawling das SERPs dos bancos, os metadados aparecerão aqui.</p>
                </div>
              )
            }

            const totalItems = dashboard.web_structure.length
            const metadataColumns = [
              {
                key: 'title',
                label: 'Título',
                getDetail: (details: any) => details?.title_text || '',
              },
              {
                key: 'meta_description',
                label: 'Meta Description',
                getDetail: (details: any) => details?.meta_desc_text || '',
              },
              {
                key: 'keywords',
                label: 'Keywords',
                getDetail: (details: any) => {
                  const keywords = details?.keywords || []
                  if (keywords.length === 0) return ''
                  // Show all keywords, one per line
                  return keywords.map((kw: string, idx: number) => `${idx + 1}. ${kw}`).join('\n')
                },
              },
              {
                key: 'robots',
                label: 'Robots',
                getDetail: (details: any) => {
                  const robots = details?.robots || ''
                  if (!robots) return ''
                  // Format as list if comma-separated
                  const directives = robots.split(',').map((d: string) => d.trim()).filter((d: string) => d)
                  return directives.join('\n')
                },
              },
              {
                key: 'open_graph',
                label: 'Open Graph',
                getDetail: (details: any) => {
                  const ogPairs = details?.open_graph_pairs || []
                  if (ogPairs.length === 0) return ''
                  // Show all OG tags, one per line with truncated values
                  return ogPairs.map((pair: any) => {
                    const value = pair.value.length > 100 ? `${pair.value.slice(0, 97)}...` : pair.value
                    return `${pair.property}:\n  ${value}`
                  }).join('\n\n')
                },
              },
              {
                key: 'ai_ready_blocks',
                label: 'AI Ready blocks',
                getDetail: (details: any) => (details?.ai_ready_types || []).join(', '),
              },
            ]

            const normalizeDetail = (value: string) => {
              if (!value) return ''
              return value.length > 160 ? `${value.slice(0, 157)}…` : value
            }

            return (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{totalItems} domínios oficiais detectados • exibindo {checklist.length} principais</span>
                  <span>Ícones verdes indicam metadado presente; laranja indica ausência</span>
                </div>

                <div className="rounded-2xl border border-gray-200 dark:border-gray-800 overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-48">Domínio</TableHead>
                        {metadataColumns.map((column) => (
                          <TableHead key={column.key} className="text-center text-xs uppercase tracking-wide">
                            {column.label}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {checklist.map((item, idx) => {
                        const details = item.details || {}
                        const sampleUrls: string[] = details.sample_urls || (item.primary_url ? [item.primary_url] : [])
                        const secondaryUrls = sampleUrls.slice(1, 3)

                        return (
                          <TableRow key={`${item.domain}-${idx}`} className="align-top">
                            <TableCell className="text-sm">
                              <div className="space-y-1">
                                <div className="font-semibold text-gray-900 dark:text-white">{item.domain}</div>
                                {item.primary_url && (
                                  <a
                                    href={item.primary_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline truncate block"
                                    title={item.primary_url}
                                  >
                                    {item.primary_url}
                                  </a>
                                )}
                                {secondaryUrls.length > 0 && (
                                  <div className="text-[11px] text-gray-500 dark:text-gray-400">
                                    +{secondaryUrls.length} variações
                                  </div>
                                )}
                              </div>
                            </TableCell>

                            {metadataColumns.map((column) => {
                              const hasMetadata = Boolean(item[column.key as keyof typeof item])
                              const detailText = normalizeDetail(column.getDetail(details))

                              return (
                                <TableCell key={column.key} className="text-center">
                                  <div className="flex items-center justify-center gap-1">
                                    {hasMetadata ? (
                                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                                    ) : (
                                      <XCircle className="w-4 h-4 text-orange-400" />
                                    )}
                                    {hasMetadata && detailText && (
                                      <div className="relative group">
                                        <Info
                                          className="w-4 h-4 text-blue-500 cursor-pointer hover:text-blue-600"
                                          onClick={() => setMetadataModal({
                                            open: true,
                                            domain: item.domain,
                                            column: column.label,
                                            details: details
                                          })}
                                        />
                                        <div className="absolute z-50 hidden group-hover:block bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap pointer-events-none">
                                          Clique para ver detalhes
                                          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900"></div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </TableCell>
                              )
                            })}
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>

                {totalItems > 6 && (
                  <div className="flex justify-center mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAllChecklist(!showAllChecklist)}
                    >
                      {showAllChecklist ? `Mostrar menos (Top 6)` : `Ver todos (${totalItems} domínios)`}
                    </Button>
                  </div>
                )}
              </div>
            )
          })()}
        </CardContent>
      </Card>

      {/* Alerts */}
      <Card>
        <CardHeader>
          <CardTitle>Alertas & Insights</CardTitle>
          <CardDescription>Itens prioritários categorizados por severidade</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Descrições das categorias */}
          <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-2">
            <h4 className="font-semibold text-sm text-gray-700 dark:text-gray-300 mb-3">Categorias de Alertas:</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-red-700 dark:text-red-400">CRÍTICO:</span>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    Problemas urgentes que impactam diretamente a visibilidade. Requerem ação imediata.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-yellow-700 dark:text-yellow-400">ATENÇÃO:</span>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    Áreas que necessitam monitoramento e podem se tornar críticas sem intervenção.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <TrendingUp className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-green-700 dark:text-green-400">OPORTUNIDADE:</span>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    Pontos fortes identificados que podem ser explorados para ganhos estratégicos.
                  </p>
                </div>
              </div>
            </div>
          </div>
          {dashboard.alerts.length > 0 ? (
            <div className="space-y-3">
              {dashboard.alerts.map((alert, i) => {
                const severityConfig = {
                  critico: {
                    bg: 'bg-red-50 dark:bg-red-900/20',
                    border: 'border-l-4 border-red-500',
                    icon: AlertTriangle,
                    iconColor: 'text-red-600 dark:text-red-400',
                    badge: 'CRÍTICO',
                    badgeBg: 'bg-red-600 text-white'
                  },
                  atencao: {
                    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
                    border: 'border-l-4 border-yellow-500',
                    icon: AlertCircle,
                    iconColor: 'text-yellow-600 dark:text-yellow-400',
                    badge: 'ATENÇÃO',
                    badgeBg: 'bg-yellow-600 text-white'
                  },
                  oportunidade: {
                    bg: 'bg-green-50 dark:bg-green-900/20',
                    border: 'border-l-4 border-green-500',
                    icon: TrendingUp,
                    iconColor: 'text-green-600 dark:text-green-400',
                    badge: 'OPORTUNIDADE',
                    badgeBg: 'bg-green-600 text-white'
                  },
                }
                const config = severityConfig[alert.severity] || severityConfig.atencao
                const Icon = config.icon

                return (
                  <div
                    key={i}
                    className={`${config.bg} ${config.border} rounded-lg p-4 shadow-sm`}
                  >
                    <div className="flex items-start gap-3">
                      <Icon className={`w-6 h-6 ${config.iconColor} flex-shrink-0`} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-semibold text-gray-900 dark:text-white">{alert.title}</h4>
                          <Badge className={`${config.badgeBg} text-xs`}>{config.badge}</Badge>
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          {alert.description}
                        </p>
                        {alert.supporting_runs.length > 0 && (
                          <div className="mt-3 text-xs text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 rounded p-2">
                            <span className="font-medium">Runs afetadas: </span>
                            {alert.supporting_runs.slice(0, 3).join(', ')}
                            {alert.supporting_runs.length > 3 && (
                              <span className="ml-1 font-medium">+{alert.supporting_runs.length - 3} mais</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-500" />
              <p>Nenhum alerta detectado</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SWOT */}
      <Card className="border border-slate-200">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl font-semibold text-slate-900">Análise SWOT</CardTitle>
          <CardDescription className="text-slate-500">
            Métricas de performance e posicionamento
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
            {[
              {
                label: 'Forças',
                count: dashboard.swot.strengths.length,
                color: 'text-emerald-600',
                border: 'border-l-4 border-emerald-500',
                description: 'Vantagens competitivas'
              },
              {
                label: 'Fraquezas',
                count: dashboard.swot.weaknesses.length,
                color: 'text-rose-600',
                border: 'border-l-4 border-rose-500',
                description: 'Pontos de melhoria'
              },
              {
                label: 'Oportunidades',
                count: dashboard.swot.opportunities.length,
                color: 'text-blue-600',
                border: 'border-l-4 border-blue-500',
                description: 'Potenciais de crescimento'
              },
              {
                label: 'Ameaças',
                count: dashboard.swot.threats.length,
                color: 'text-amber-600',
                border: 'border-l-4 border-amber-500',
                description: 'Riscos a mitigar'
              },
            ].map((item, idx) => (
              <div key={idx} className={`rounded-lg bg-white shadow-sm px-4 py-5 ${item.border}`}>
                <div className="text-sm uppercase tracking-wide text-slate-500">{item.label}</div>
                <div className={`text-2xl font-semibold mt-1 ${item.color}`}>{item.count}</div>
                <div className="text-xs text-slate-500 mt-2">{item.description}</div>
              </div>
            ))}
          </div>

          <div className="border-t border-slate-200 pt-4">
            <div className="flex items-center justify-between text-sm">
              <div>
                <div className="font-semibold text-slate-700">Score de Equilíbrio SWOT</div>
                <div className="text-xs text-slate-500">(Forças + Oportunidades) - (Fraquezas + Ameaças)</div>
              </div>
              <div className="text-right">
                {(() => {
                  const score = (dashboard.swot.strengths.length + dashboard.swot.opportunities.length) - (dashboard.swot.weaknesses.length + dashboard.swot.threats.length)
                  const label = score > 0 ? 'Positivo' : score < 0 ? 'Requer Atenção' : 'Neutro'
                  const color = score > 0 ? 'text-emerald-600' : score < 0 ? 'text-rose-600' : 'text-slate-500'
                  return (
                    <>
                      <div className={`text-2xl font-bold ${color}`}>{score > 0 ? `+${score}` : score}</div>
                      <div className={`text-xs font-medium ${color}`}>{label}</div>
                    </>
                  )
                })()}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              {
                title: 'Forças',
                items: dashboard.swot.strengths,
                icon: CheckCircle2,
                iconColor: 'text-emerald-500'
              },
              {
                title: 'Fraquezas',
                items: dashboard.swot.weaknesses,
                icon: AlertCircle,
                iconColor: 'text-rose-500'
              },
              {
                title: 'Oportunidades',
                items: dashboard.swot.opportunities,
                icon: TrendingUp,
                iconColor: 'text-blue-500'
              },
              {
                title: 'Ameaças',
                items: dashboard.swot.threats,
                icon: AlertTriangle,
                iconColor: 'text-amber-500'
              },
            ].map((section, idx) => {
              const Icon = section.icon
              return (
                <div key={idx} className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                  <div className="flex items-center gap-2 mb-3">
                    <Icon className={`w-4 h-4 ${section.iconColor}`} />
                    <h4 className="font-semibold text-slate-700">{section.title}</h4>
                  </div>
                  <ul className="space-y-2">
                    {section.items.length > 0 ? (
                      section.items.map((item, i) => (
                        <li key={i} className="text-sm text-slate-600">
                          {item}
                        </li>
                      ))
                    ) : (
                      <li className="text-sm text-slate-400 italic">Nenhum item identificado</li>
                    )}
                  </ul>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Raw Samples (Evidence Drawer) */}
      <Card>
        <CardHeader>
          <CardTitle>Amostras Brutas</CardTitle>
          <CardDescription>
            Snippets de análise para transparência e auditoria
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {dashboard.raw_samples.map((sample) => (
              <div
                key={sample.run_id}
                className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-800/50 text-sm"
              >
                <div className="flex items-center justify-between mb-2">
                  <code className="text-xs font-mono text-blue-600 dark:text-blue-400">
                    {sample.run_id}
                  </code>
                  <Badge variant="secondary">{sample.status}</Badge>
                </div>
                <div className="grid grid-cols-3 gap-4 mb-2 text-xs text-gray-600 dark:text-gray-400">
                  <div>
                    <span className="font-medium">IM-SEO:</span> {sample.im_seo_score?.toFixed(1) || 'N/A'}
                  </div>
                  <div>
                    <span className="font-medium">E-E-A-T:</span> {sample.eeat_score?.toFixed(1) || 'N/A'}
                  </div>
                  <div>
                    <span className="font-medium">Citações:</span> {sample.citations_count || 0}
                  </div>
                </div>
                {sample.response_snippet && (
                  <p className="text-xs text-gray-700 dark:text-gray-300 italic">
                    "{sample.response_snippet}..."
                  </p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Metadata Detail Modal */}
      {metadataModal.open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setMetadataModal({...metadataModal, open: false})}>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{metadataModal.column}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{metadataModal.domain}</p>
                </div>
                <button
                  onClick={() => setMetadataModal({...metadataModal, open: false})}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-120px)]">
              {(() => {
                const details = metadataModal.details
                const column = metadataModal.column

                if (column === 'Título') {
                  return (
                    <div className="space-y-2">
                      <p className="text-gray-900 dark:text-white font-medium">{details?.title_text}</p>
                    </div>
                  )
                }

                if (column === 'Meta Description') {
                  return (
                    <div className="space-y-2">
                      <p className="text-gray-700 dark:text-gray-300">{details?.meta_desc_text}</p>
                    </div>
                  )
                }

                if (column === 'Keywords') {
                  const keywords = details?.keywords || []
                  return (
                    <div className="space-y-2">
                      {keywords.length === 0 ? (
                        <p className="text-gray-500">Nenhuma keyword encontrada</p>
                      ) : (
                        <ul className="list-decimal list-inside space-y-1">
                          {keywords.map((kw: string, idx: number) => (
                            <li key={idx} className="text-gray-700 dark:text-gray-300">{kw}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )
                }

                if (column === 'Robots') {
                  const robots = details?.robots || ''
                  const directives = robots.split(',').map((d: string) => d.trim()).filter((d: string) => d)
                  const robotsTxtFull = details?.robots_txt_full
                  const llmsTxt = details?.llms_txt
                  const aiTxt = details?.ai_txt
                  
                  return (
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-semibold text-sm mb-2 text-gray-700 dark:text-gray-300">Meta Robots Tag</h4>
                        <div className="bg-gray-100 dark:bg-gray-900 rounded p-4 font-mono text-sm">
                          {directives.map((directive: string, idx: number) => (
                            <div key={idx} className="text-gray-800 dark:text-gray-200">
                              {directive}
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      {robotsTxtFull && (
                        <div>
                          <h4 className="font-semibold text-sm mb-2 text-gray-700 dark:text-gray-300">📄 robots.txt</h4>
                          <div className="bg-gray-100 dark:bg-gray-900 rounded p-4 font-mono text-xs max-h-60 overflow-y-auto">
                            <pre className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{robotsTxtFull}</pre>
                          </div>
                        </div>
                      )}
                      
                      {llmsTxt && (
                        <div>
                          <h4 className="font-semibold text-sm mb-2 text-gray-700 dark:text-gray-300">🤖 llms.txt</h4>
                          <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-4 font-mono text-xs max-h-60 overflow-y-auto border-l-4 border-blue-500">
                            <pre className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{llmsTxt}</pre>
                          </div>
                        </div>
                      )}
                      
                      {aiTxt && (
                        <div>
                          <h4 className="font-semibold text-sm mb-2 text-gray-700 dark:text-gray-300">🧠 ai.txt</h4>
                          <div className="bg-purple-50 dark:bg-purple-900/20 rounded p-4 font-mono text-xs max-h-60 overflow-y-auto border-l-4 border-purple-500">
                            <pre className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{aiTxt}</pre>
                          </div>
                        </div>
                      )}
                      
                      {!robotsTxtFull && !llmsTxt && !aiTxt && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                          💡 Nenhum arquivo especial detectado (robots.txt, llms.txt, ai.txt)
                        </div>
                      )}
                    </div>
                  )
                }

                if (column === 'Open Graph') {
                  const ogPairs = details?.open_graph_pairs || []
                  return (
                    <div className="space-y-3">
                      {ogPairs.length === 0 ? (
                        <p className="text-gray-500">Nenhuma tag Open Graph encontrada</p>
                      ) : (
                        ogPairs.map((pair: any, idx: number) => (
                          <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                            <div className="font-mono text-xs text-blue-600 dark:text-blue-400 mb-1">
                              {pair.property}
                            </div>
                            <div className="text-sm text-gray-700 dark:text-gray-300 break-words">
                              {pair.value}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )
                }

                if (column === 'AI Ready blocks') {
                  const aiReadyTypes = details?.ai_ready_types || []
                  return (
                    <div className="space-y-2">
                      {aiReadyTypes.length === 0 ? (
                        <p className="text-gray-500">Nenhum bloco AI Ready detectado</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {aiReadyTypes.map((type: string, idx: number) => (
                            <Badge key={idx} variant="secondary" className="text-sm">
                              {type}
                            </Badge>
                          ))}
                        </div>
                      )}
                      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                        <p className="font-semibold mb-2">Tipos detectados:</p>
                        <ul className="list-disc list-inside space-y-1">
                          <li><strong>Lista:</strong> Listas ordenadas ou não ordenadas (ul/ol)</li>
                          <li><strong>FAQ:</strong> Schema.org FAQPage detectado</li>
                          <li><strong>Tabela:</strong> Tabelas HTML com dados estruturados</li>
                          <li><strong>Schema.org:</strong> Dados estruturados JSON-LD</li>
                        </ul>
                      </div>
                    </div>
                  )
                }

                return <p className="text-gray-500">Sem dados disponíveis</p>
              })()}
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}
