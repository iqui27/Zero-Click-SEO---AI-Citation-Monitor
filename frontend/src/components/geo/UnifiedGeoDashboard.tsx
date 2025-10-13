import { useMemo, useState, type ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { Select } from '../ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  RadarChart,
  Radar,
  RadialBarChart,
  RadialBar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Label,
  LabelList,
  Cell,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts'
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '../ui/chart'
import { TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react'
import { useGeoDashboard, useGeoAggregations, type GeoDashboardFilters } from '../../lib/geo'
import type { GeoDashboard } from '../../lib/api'

export type UnifiedGeoDashboardProps = {
  projectId: string
}

function ExamplesSection({ data }: { data: GeoDashboard | null }) {
  const samples = useMemo(() => {
    if (!data?.raw_samples) return []
    return data.raw_samples.slice(0, 5)
  }, [data])

  return (
    <section>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-slate-900">Exemplos de Respostas</h2>
        <p className="text-sm text-slate-500 mt-1">
          Amostras de respostas mais recentes
        </p>
      </div>

      <div className="space-y-4">
        {samples.length ? (
          samples.map((sample) => (
            <Card key={sample.run_id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-sm font-medium">Run {sample.run_id}</CardTitle>
                    <CardDescription className="text-xs">
                      {sample.started_at ? new Date(sample.started_at).toLocaleString('pt-BR') : '–'}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {sample.citations_count != null && sample.citations_count > 0 && (
                      <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-600">
                        {sample.citations_count} citações
                      </Badge>
                    )}
                    {sample.im_seo_score != null && (
                      <Badge variant="outline">IM-SEO: {sample.im_seo_score.toFixed(0)}</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {sample.response_snippet || 'Sem trecho disponível'}
                  {sample.response_snippet && '...'}
                </p>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card className="border-dashed">
            <CardContent className="p-6 text-center text-sm text-slate-500">
              Nenhum exemplo disponível para o filtro selecionado.
            </CardContent>
          </Card>
        )}
      </div>
    </section>
  )
}

const COLORS = ['#2563eb', '#f97316', '#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#6366f1']

export function UnifiedGeoDashboard({ projectId }: UnifiedGeoDashboardProps) {
  const [filters, setFilters] = useState<GeoDashboardFilters>({
    llm_model: undefined,
    subproject_id: undefined,
    prompt_category: undefined,
    date_from: undefined,
    date_to: undefined,
  })

  const { loading, error, data, overview } = useGeoDashboard(projectId, filters)
  const aggregations = useGeoAggregations(projectId, { days: 30 })

  if (loading) {
    return (
      <div className="space-y-6">
        <Card><CardContent className="h-32 animate-pulse bg-slate-100" /></Card>
        <Card><CardContent className="h-64 animate-pulse bg-slate-100" /></Card>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="p-6">
          <p className="text-sm text-red-600">{error}</p>
        </CardContent>
      </Card>
    )
  }

  if (!data) {
    return (
      <Card className="border-dashed">
        <CardContent className="p-6 text-sm text-slate-500">
          Nenhum dado disponível para este projeto.
        </CardContent>
      </Card>
    )
  }

  const handleFilterChange = (key: keyof GeoDashboardFilters, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value === 'all' || !value ? undefined : value }))
  }

  const filterConfigs = [
    {
      key: 'llm_model' as keyof GeoDashboardFilters,
      label: 'LLM',
      options: [
        { value: 'all', label: 'Todos os modelos' },
        { value: 'gpt', label: 'OpenAI GPT' },
        { value: 'claude', label: 'Anthropic Claude' },
        { value: 'gemini', label: 'Gemini' },
        { value: 'perplexity', label: 'Perplexity' },
      ],
    },
    {
      key: 'subproject_id' as keyof GeoDashboardFilters,
      label: 'Tema (Subprojeto)',
      options: [
        { value: 'all', label: 'Todos os temas' },
        // TODO: Carregar subprojects dinamicamente
      ],
    },
    {
      key: 'prompt_category' as keyof GeoDashboardFilters,
      label: 'Categoria',
      options: [
        { value: 'all', label: 'Todas as categorias' },
        // TODO: Carregar categorias dinamicamente
      ],
    },
  ]

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Dashboard GEO</h1>
            <p className="text-sm text-slate-500 mt-1">Análise de presença em motores de busca generativos</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filterConfigs.map((filter) => (
            <div key={filter.key} className="space-y-1">
              <label className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
                {filter.label}
              </label>
              <Select
                value={filters[filter.key] || 'all'}
                onChange={(e) => handleFilterChange(filter.key, e.target.value)}
                className="w-full"
              >
                {filter.options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>
          ))}
        </div>
      </div>

      {/* Big Numbers */}
      <BigNumbersSection data={data} overview={overview} />

      {/* Presença da Marca + Análise Competitiva */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BrandPresenceSection data={data} overview={overview} />
        <CompetitiveAnalysisSection data={data} aggregations={aggregations.data} />
      </div>

      {/* Engajamento & Potencial de Conversão */}
      <EngagementConversionSection overview={overview} />

      {/* Monitoramento de Citações */}
      <CitationMonitoringSection data={data} aggregations={aggregations.data} />

      {/* Citações (URLs, domínios, qualidade) */}
      <CitationsSection data={data} />

      {/* Acompanhamento de Domínio */}
      <DomainTrackingSection data={data} />

      {/* Exemplos */}
      <ExamplesSection data={data} />
    </div>
  )
}

type BigNumberMetric = {
  title: string
  value: string
  subtitle: ReactNode
  delta: number | null
  trend: 'up' | 'down' | 'neutral' | null
}

function BigNumbersSection({ data, overview }: { data: GeoDashboard; overview: any }) {
  const totalRuns = data.total_runs || 0
  const citationRateKpi = overview?.kpis?.find((k: any) => k.label === 'Taxa de Citação')
  const brandMentionsKpi = overview?.kpis?.find((k: any) => k.label === 'Menções de Marca')
  const zeroClickKpi = overview?.kpis?.find((k: any) => k.label === 'Presença Zero-Click')

  const avgCitationPosition = useMemo(() => {
    if (!overview?.metrics?.brandFirstMentionPositionAvg) return null
    return overview.metrics.brandFirstMentionPositionAvg
  }, [overview])

  const avgCitationPositionNormalized = useMemo(() => {
    if (avgCitationPosition == null) return null
    const normalized = avgCitationPosition >= 10 ? avgCitationPosition / 10 : avgCitationPosition
    return Number.isFinite(normalized) ? normalized : null
  }, [avgCitationPosition])

  const formatNumber = (value: number) =>
    value.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

  const bigNumbers: BigNumberMetric[] = [
    {
      title: 'Total de Respostas',
      value: String(totalRuns).replace(/\B(?=(\d{3})+(?!\d))/g, '.'),
      subtitle: <span className="text-xs text-slate-500">analisadas</span>,
      delta: null,
      trend: null,
    },
    {
      title: 'Taxa de Citação',
      value: citationRateKpi?.value != null ? `${citationRateKpi.value.toFixed(1)}%` : '–',
      subtitle: (
        <span className="text-xs text-slate-500">
          <span className="font-semibold text-slate-900">{brandMentionsKpi?.value ?? 0}</span> menções de marca
        </span>
      ),
      delta: citationRateKpi?.delta,
      trend: citationRateKpi?.trendDirection,
    },
    {
      title: 'Posição Média da Citação',
      value: avgCitationPositionNormalized != null ? formatNumber(avgCitationPositionNormalized) : '–',
      subtitle: <span className="text-xs text-slate-500">% da resposta</span>,
      delta: null,
      trend: null,
    },
    {
      title: 'PRZC (Presença Zero-Click)',
      value: zeroClickKpi?.value != null ? `${zeroClickKpi.value.toFixed(1)}%` : '–',
      subtitle: <span className="text-xs text-slate-500">respostas com recursos IA</span>,
      delta: zeroClickKpi?.delta,
      trend: zeroClickKpi?.trendDirection,
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {bigNumbers.map((metric) => (
        <Card key={metric.title}>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs font-medium text-slate-500">{metric.title}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline justify-between">
              <p className="text-2xl font-bold text-slate-900">{metric.value}</p>
              {metric.delta != null && (
                <span className={`text-xs font-medium ${metric.trend === 'up' ? 'text-emerald-600' : metric.trend === 'down' ? 'text-rose-600' : 'text-slate-500'}`}>
                  {metric.trend === 'up' ? '↑' : metric.trend === 'down' ? '↓' : '→'} {metric.delta > 0 ? '+' : ''}{metric.delta.toFixed(1)}%
                </span>
              )}
            </div>
            <div className="mt-1">{metric.subtitle}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function BrandPresenceSection({ data, overview }: { data: GeoDashboard; overview: any }) {
  const timeline = overview?.brandTimeline || []
  
  const densityMetric = overview?.metrics?.brandMentionDensityAvg
  const firstMentionMetric = overview?.metrics?.brandFirstMentionPositionAvg

  const firstMentionNormalized = useMemo(() => {
    if (firstMentionMetric == null) return null
    const normalized = firstMentionMetric >= 10 ? firstMentionMetric / 10 : firstMentionMetric
    return Number.isFinite(normalized) ? normalized : null
  }, [firstMentionMetric])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Presença da Marca</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 pb-4">
        <div className="h-[20rem]">
          {timeline.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeline} margin={{ top: 16, right: 48, bottom: 40, left: 48 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis yAxisId="left" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 100]} tickLine={false} axisLine={false} />
                <RechartsTooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar yAxisId="left" dataKey="mentions" name="Menções" fill="#2563eb" radius={[4, 4, 0, 0]} />
                <Bar yAxisId="right" dataKey="firstMentionAvg" name="Posição Primeira Menção" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500">
              Sem dados de timeline para o período selecionado.
            </div>
          )}
        </div>

        <div className="text-xs text-slate-500 flex justify-between">
          <span>Menções totais registradas no período</span>
          <span>Posição média da primeira menção (%)</span>
        </div>

        <div className="grid gap-3 pt-2 sm:grid-cols-2 xl:grid-cols-2">
          <MetricPanel
            title="Densidade de Menções"
            primary={densityMetric != null ? densityMetric.toFixed(1) : '–'}
            secondary="por 1000 caracteres"
          />
          <MetricPanel
            title="Posição Média Primeira Menção"
            primary={firstMentionNormalized != null ? firstMentionNormalized.toFixed(1) : '–'}
          />
        </div>
      </CardContent>
    </Card>
  )
}

type MetricPanelProps = {
  title: string
  primary: string
  secondary?: string
}

function MetricPanel({ title, primary, secondary }: MetricPanelProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:shadow-md">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900">{primary}</p>
      {secondary ? <p className="text-xs text-slate-500 mt-1">{secondary}</p> : null}
    </div>
  )
}

function CompetitiveAnalysisSection({ data, aggregations }: { data: GeoDashboard; aggregations: any }) {
  const shareOfVoice = data.positioning?.share_of_voice || {}
  const pieData = useMemo(() => {
    return Object.entries(shareOfVoice).map(([name, value]) => ({
      name,
      value: Number(value),
    }))
  }, [shareOfVoice])

  const cocitationPercentage = data.geo_summary?.cocitation_percentage || 0
  const competitiveRatio = useMemo(() => {
    const totalMentions = (data.positioning as any)?.total_mentions || 0
    const ourBrand = Object.keys(shareOfVoice)[0] || ''
    const ourMentions = shareOfVoice[ourBrand] || 0
    if (totalMentions === 0) return 0
    return ourMentions / 100
  }, [data, shareOfVoice])

  // Derive cocitation data from brand_ranking
  const cocitationByCompetitor = useMemo(() => {
    const ranking = data.positioning?.brand_ranking || []
    const totalMentions = (data.positioning as any)?.total_mentions || 1

    // Skip first item (our brand) and take competitors
    return ranking
      .slice(1, 11)
      .map((item, index) => ({
        name: item.brand,
        value: (item.mentions / totalMentions) * 100,
        color: COLORS[index % COLORS.length],
      }))
      .filter(item => item.value > 0)
  }, [data])

  // Derive context data from aggregations
  const contextData = useMemo(() => {
    const byProduct = (aggregations?.byProduct || []) as Array<{
      product_category: string | null
      avg_brand_mentions: number | null
      avg_engagement_score: number | null
    }>

    return byProduct
      .filter((item) => item.product_category)
      .map((item) => ({
        category: item.product_category as string,
        brandMentions: item.avg_brand_mentions ?? 0,
        engagement: item.avg_engagement_score ?? 0,
      }))
      .slice(0, 8)
  }, [aggregations])

  const productPresence = useMemo(() => {
    const items = (aggregations?.byProduct || []) as Array<{
      product_category: string | null
      avg_citation_rate?: number | null
      avg_brand_mentions?: number | null
      runs_count?: number | null
    }>
    
    const result = items
      .filter((item) => {
        const hasCategory = !!item.product_category
        const hasRate = item.avg_citation_rate != null && item.avg_citation_rate > 0
        return hasCategory && hasRate
      })
      .map((item) => ({
        product: item.product_category as string,
        presence: item.avg_citation_rate ?? 0,
      }))
      .slice(0, 8)
    
    return result
  }, [aggregations])

  const funnelPresence = useMemo(() => {
    const items = (aggregations?.byFunnel || []) as Array<{
      funnel_stage: string | null
      avg_citation_rate?: number | null
      avg_brand_mentions?: number | null
      runs_count?: number | null
    }>
    
    const result = items
      .filter((item) => {
        const hasStage = !!item.funnel_stage
        const hasRate = item.avg_citation_rate != null && item.avg_citation_rate > 0
        return hasStage && hasRate
      })
      .map((item) => ({
        stage: item.funnel_stage as string,
        presence: item.avg_citation_rate ?? 0,
      }))
    
    return result
  }, [aggregations])

  return (
    <Tabs defaultValue="sov" className="w-full">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Análise Competitiva</CardTitle>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="sov">Share of Voice</TabsTrigger>
            <TabsTrigger value="cocitation">Co-citação</TabsTrigger>
            <TabsTrigger value="context">Contexto</TabsTrigger>
          </TabsList>
        </CardHeader>
        <CardContent>
          <TabsContent value="sov">
            <div className="space-y-4">
              <p className="text-sm text-slate-600">Distribuição de menções por marca no período analisado</p>
              {pieData.length ? (
                <Card className="flex flex-col">
                  <CardHeader className="items-center pb-0">
                    <CardTitle className="text-base">Share of Voice</CardTitle>
                    <CardDescription className="text-xs text-slate-500">Participação por marca</CardDescription>
                  </CardHeader>
                  <CardContent className="flex-1 pb-0">
                    <ChartContainer
                      config={useMemo<ChartConfig>(
                        () =>
                          pieData.reduce((acc, item, index) => {
                            acc[item.name] = {
                              label: item.name,
                              color: COLORS[index % COLORS.length],
                            }
                            return acc
                          }, {} as ChartConfig),
                        [pieData]
                      )}
                      className="mx-auto h-[320px] w-full max-w-[420px] pb-0 [&_.recharts-pie-label-text]:fill-slate-700 [&_.recharts-pie-label-text]:text-sm [&_.recharts-pie-label-text]:font-medium"
                    >
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <ChartTooltip content={<ChartTooltipContent hideLabel />} />
                          <Pie
                            data={pieData}
                            dataKey="value"
                            nameKey="name"
                            labelLine={false}
                            label={({ name, value }) =>
                              `${name ?? ''} ${typeof value === 'number' ? value.toFixed(1) : value}%`
                            }
                          >
                            {pieData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                    </ChartContainer>
                  </CardContent>
                  <CardFooter className="flex-col gap-1.5 text-xs text-slate-500">
                    <span>Legenda atualizada com cores padronizadas</span>
                    <span>Valores representam % de menções no período</span>
                  </CardFooter>
                </Card>
              ) : (
                <p className="text-sm text-slate-500">Sem dados disponíveis.</p>
              )}

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs text-slate-500">Ratio de Menção Competitiva</p>
                  <p className="text-2xl font-bold text-slate-900">{competitiveRatio.toFixed(2)}</p>
                  <p className="text-xs text-slate-500">nossa / total</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs text-slate-500">Co-Citações</p>
                  <p className="text-2xl font-bold text-slate-900">{cocitationPercentage.toFixed(0)}%</p>
                  <p className="text-xs text-slate-500">das respostas incluem concorrentes</p>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="cocitation">
            <div className="space-y-6">
              {cocitationByCompetitor.length ? (
                <>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={cocitationByCompetitor}
                        layout="vertical"
                        margin={{ top: 12, right: 20, bottom: 12, left: 120 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis type="number" stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 'dataMax']} />
                        <YAxis dataKey="name" type="category" stroke="#94a3b8" tick={{ fontSize: 12 }} width={110} />
                        <RechartsTooltip formatter={(value: any) => `${value.toFixed(1)}%`} />
                        <Bar dataKey="value" name="% de Menções" radius={[0, 6, 6, 0]}>
                          {cocitationByCompetitor.map((entry, index) => (
                            <Cell key={`cocitation-${entry.name}-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-4">
                    <h4 className="text-sm font-semibold text-slate-900 mb-3">Top Concorrentes Mencionados</h4>
                    <ul className="space-y-2 text-sm text-slate-700">
                      {cocitationByCompetitor.slice(0, 5).map((item, index) => (
                        <li key={`cocitation-list-${item.name}-${index}`} className="flex items-start gap-2">
                          <span style={{ color: item.color }}>•</span>
                          <span><strong>{item.name}</strong> representa <strong>{item.value.toFixed(1)}%</strong> das menções</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              ) : (
                <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500">
                  Sem dados de concorrentes disponíveis para o período selecionado.
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="context">
            <div className="space-y-6">
              {contextData.length ? (
                <>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={contextData} margin={{ top: 12, right: 20, bottom: 60, left: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="category" stroke="#94a3b8" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" />
                        <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
                        <RechartsTooltip />
                        <Legend />
                        <Bar dataKey="brandMentions" name="Menções de Marca" fill="#2563eb" radius={[6, 6, 0, 0]} />
                        <Bar dataKey="engagement" name="Engajamento Médio" fill="#10b981" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-4">
                    <h4 className="text-sm font-semibold text-slate-900 mb-3">Performance por Categoria de Produto</h4>
                    <div className="space-y-2">
                      {contextData.slice(0, 5).map((item, index) => (
                        <div key={index} className="flex items-center justify-between text-sm">
                          <span className="text-slate-700">{item.category}</span>
                          <div className="flex gap-4">
                            <span className="text-blue-600 font-medium">{item.brandMentions.toFixed(1)} menções</span>
                            <span className="text-emerald-600 font-medium">{item.engagement.toFixed(0)} eng.</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500">
                  Sem dados de contexto disponíveis para o período selecionado.
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold text-slate-900">Presença Competitiva por Produto</CardTitle>
                    <CardDescription>% de respostas com concorrentes por categoria</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {productPresence.length ? (
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={productPresence} layout="vertical" margin={{ top: 12, right: 24, bottom: 12, left: 100 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis type="number" stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 100]} />
                            <YAxis dataKey="product" type="category" stroke="#94a3b8" tick={{ fontSize: 12 }} width={90} />
                            <RechartsTooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                            <Bar dataKey="presence" name="Citation Rate" radius={[0, 6, 6, 0]}>
                              {productPresence.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={`hsl(${(index * 360) / productPresence.length}, 70%, 50%)`} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">Sem dados competitivos por produto.</p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold text-slate-900">Presença por Etapa do Funil</CardTitle>
                    <CardDescription>% de respostas com concorrentes por estágio</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {funnelPresence.length ? (
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={funnelPresence} layout="vertical" margin={{ top: 12, right: 24, bottom: 12, left: 100 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis type="number" stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 100]} />
                            <YAxis dataKey="stage" type="category" stroke="#94a3b8" tick={{ fontSize: 12 }} width={90} />
                            <RechartsTooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                            <Bar dataKey="presence" name="Citation Rate" radius={[0, 6, 6, 0]}>
                              {funnelPresence.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={`hsl(${20 + (index * 40)}, 85%, 55%)`} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">Sem dados competitivos por funil.</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>
        </CardContent>
      </Card>
    </Tabs>
  )
}

function EngagementConversionSection({ overview }: { overview: any }) {
  const timelineRaw = overview?.timeline || []
  
  // Filter timeline data - data already comes transformed from overview
  const timeline = useMemo(() => {
    const filtered = timelineRaw.filter((point: any) => 
      (point.engagement != null && point.engagement > 0) || 
      (point.conversionPotential != null && point.conversionPotential > 0)
    )
    
    console.log('[EngagementConversion] Raw:', timelineRaw.length, 'Filtered:', filtered.length, 'Data:', filtered)
    return filtered
  }, [timelineRaw])
  
  const conversationalTriggers = overview?.metrics?.conversationalTriggerAvg || 0
  const engagementScore = overview?.metrics?.engagementScoreAvg || 0
  const conversionPotential = overview?.metrics?.topConversionPotential || 'Médio'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Engajamento & Potencial de Conversão</CardTitle>
      </CardHeader>
      <CardContent>
        {timeline.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={timeline}
                margin={{
                  left: 12,
                  right: 12,
                  top: 12,
                  bottom: 12,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tick={{ fontSize: 11 }}
                  stroke="#94a3b8"
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11 }}
                  stroke="#94a3b8"
                  domain={[0, 100]}
                />
                <RechartsTooltip />
                <Legend />
                <Line
                  dataKey="engagement"
                  name="Taxa de Engajamento"
                  type="monotone"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ fill: "#10b981", r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  dataKey="conversionPotential"
                  name="Potencial de Conversão"
                  type="monotone"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={{ fill: "#f59e0b", r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Sem dados de timeline.</p>
        )}
        
        <div className="mt-6 grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-slate-500">Gatilhos Conversacionais</p>
            <p className="text-xl font-semibold text-slate-900">{conversationalTriggers.toFixed(1)}</p>
            <p className="text-xs text-slate-500">média por resposta</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Score de Engajamento</p>
            <p className="text-xl font-semibold text-slate-900">{engagementScore.toFixed(0)}</p>
            <p className="text-xs text-slate-500">de 100 pontos</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Potencial de Conversão</p>
            <p className="text-xl font-semibold text-slate-900">{conversionPotential}</p>
            <p className="text-xs text-slate-500">68% das respostas</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Label mappings for Portuguese
const PRODUCT_LABELS: Record<string, string> = {
  cartoes: 'Cartões',
  credito: 'Crédito',
  investimentos: 'Investimentos',
  conta: 'Conta',
  seguros: 'Seguros',
  empresarial: 'Empresarial',
  digital: 'Digital',
  multiproduto: 'Multiproduto',
}

const FUNNEL_LABELS: Record<string, string> = {
  consciencia: 'Consciência',
  consideracao: 'Consideração',
  decisao: 'Decisão',
  pos_compra: 'Pós-Compra',
}

const QUESTION_LABELS: Record<string, string> = {
  informacional: 'Informacional',
  transacional: 'Transacional',
  navegacional: 'Navegacional',
  comparativa: 'Comparativa',
}

function CitationMonitoringSection({ data, aggregations }: { data: GeoDashboard; aggregations: any }) {
  const byProduct = (aggregations?.byProduct || []).filter((item: any) => item.product_category)
  const byFunnel = (aggregations?.byFunnel || []).filter((item: any) => item.funnel_stage)
  const byQuestion = (aggregations?.byQuestionType || []).filter((item: any) => item.question_type)

  // Prepare timeline data for Citation Rate graph
  const timeline = useMemo(() => {
    const timelineData = data.timeline || []
    return timelineData.map((point: any) => ({
      date: point.date,
      observed: point.citation_rate_observed_avg || 0,
      corrected: point.citation_rate_corrected_avg || 0,
    }))
  }, [data])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Monitoramento de Citações</CardTitle>
        <CardDescription>Taxa de Citação (CR)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Gráfico de linha temporal */}
        <div className="h-64">
          {timeline.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeline} margin={{ top: 12, right: 20, bottom: 12, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 12 }} />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 100]} />
                <RechartsTooltip formatter={(value: any) => `${value.toFixed(1)}%`} />
                <Legend />
                <Bar dataKey="observed" name="CR Observado" fill="#3b82f6" />
                <Bar dataKey="corrected" name="CR Corrigido" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500">
              Gráfico de linha temporal (CR Observado vs CR Corrigido)
            </div>
          )}
        </div>

        {/* Por Produto, Funil e Tipo */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3">Por Produto</h4>
            {byProduct.length > 0 ? (
              byProduct.slice(0, 5).map((item: any) => (
                <div key={item.product_category} className="mb-2">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-600">{PRODUCT_LABELS[item.product_category] || item.product_category}</span>
                    <span className="font-semibold text-slate-900">
                      {item.avg_citation_rate != null ? `${item.avg_citation_rate.toFixed(0)}%` : '–'}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500"
                      style={{ width: `${item.avg_citation_rate || 0}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">Sem dados disponíveis</p>
            )}
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3">Por Estágio do Funil</h4>
            {byFunnel.length > 0 ? (
              byFunnel.map((item: any) => (
                <div key={item.funnel_stage} className="mb-2">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-600">{FUNNEL_LABELS[item.funnel_stage] || item.funnel_stage}</span>
                    <span className="font-semibold text-slate-900">
                      {item.avg_citation_rate != null ? `${item.avg_citation_rate.toFixed(0)}%` : '–'}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-500"
                      style={{ width: `${item.avg_citation_rate || 0}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">Sem dados disponíveis</p>
            )}
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3">Por Tipo de Pergunta</h4>
            {byQuestion.length > 0 ? (
              byQuestion.slice(0, 4).map((item: any) => (
                <div key={item.question_type} className="mb-2">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-slate-600">{QUESTION_LABELS[item.question_type] || item.question_type}</span>
                    <span className="font-semibold text-slate-900">
                      {item.avg_citation_rate != null ? `${item.avg_citation_rate.toFixed(0)}%` : '–'}
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-orange-500"
                      style={{ width: `${item.avg_citation_rate || 0}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500">Sem dados disponíveis</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function DomainTrackingSection({ data }: { data: GeoDashboard }) {
  const topDomains = useMemo(() => {
    const ranking = data.positioning?.brand_ranking || []
    return ranking.slice(0, 5)
  }, [data])

  const totalMentions = (data.positioning as any)?.total_mentions || 0

  // Correction factor: difference between corrected and observed citation rates
  // Note: requires citation_rate_corrected and citation_rate_observed from backend
  const correctionFactor = useMemo(() => {
    const citationKpi = (data.kpis || []).find((k: any) => k.label === 'Taxa de Citação')
    // For now, using delta as proxy; ideally should be (corrected - observed) rates
    return citationKpi?.delta != null ? Math.abs(citationKpi.delta) : null
  }, [data])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Acompanhamento de Domínio</CardTitle>
        <CardDescription>Consolidação de Variantes</CardDescription>
      </CardHeader>
      <CardContent>
        {topDomains.length ? (
          <>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={topDomains}
                  layout="vertical"
                  margin={{ top: 12, right: 20, bottom: 12, left: 100 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" stroke="#94a3b8" tick={{ fontSize: 12 }} />
                  <YAxis dataKey="brand" type="category" stroke="#94a3b8" tick={{ fontSize: 12 }} width={90} />
                  <RechartsTooltip />
                  <Bar dataKey="mentions" name="Menções" fill="#2563eb" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-blue-100 p-2">
                  <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Total de Menções Consolidadas</p>
                  <p className="text-2xl font-bold text-slate-900">{totalMentions.toLocaleString('pt-BR')}</p>
                  <p className="text-xs text-slate-500">Todas as variantes de domínio combinadas</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-pink-100 p-2">
                  <svg className="h-5 w-5 text-pink-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Variação de Taxa de Citação</p>
                  <p className="text-2xl font-bold text-slate-900">
                    {correctionFactor != null ? `${correctionFactor > 0 ? '+' : ''}${correctionFactor.toFixed(1)}%` : '–'}
                  </p>
                  <p className="text-xs text-slate-500">
                    {correctionFactor != null ? 'Variação em relação ao período anterior' : 'Dados não disponíveis'}
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-500">Sem dados de domínios.</p>
        )}
      </CardContent>
    </Card>
  )
}

function CitationsSection({ data }: { data: GeoDashboard }) {
  const topUrls = useMemo(() => {
    const ranking = data.positioning?.brand_ranking || []
    return ranking.slice(0, 10).filter((item) => item.sample_url)
  }, [data])

  const topDomains = useMemo(() => {
    const ranking = data.positioning?.brand_ranking || []
    return ranking.slice(0, 8)
  }, [data])

  const radarMetrics = useMemo(() => {
    const semanticScores = ((data.geo_summary as any)?.semantic_scores || {}) as Record<string, number>
    const defaults = [
      { key: 'authority', label: 'Autoridade' },
      { key: 'relevance', label: 'Relevância' },
      { key: 'clarity', label: 'Clareza' },
      { key: 'context', label: 'Contexto' },
      { key: 'precision', label: 'Precisão' },
      { key: 'freshness', label: 'Atualidade' },
    ]

    return defaults.map(({ key, label }) => {
      const raw = Number(semanticScores[key] ?? 0)
      const value = Number.isFinite(raw) ? Math.max(0, Math.min(raw, 100)) : 0
      return { dimension: label, value }
    })
  }, [data])

  const hasSemanticScores = useMemo(() => {
    const scores = ((data.geo_summary as any)?.semantic_scores || {}) as Record<string, number>
    return Object.keys(scores).length > 0 && Object.values(scores).some(v => v > 0)
  }, [data])

  const perceivedValueCategories = useMemo(() => {
    const categories = ((data.geo_summary as any)?.perceived_value_categories || []) as Array<{ label: string; value: number }>
    const palette = ['bg-blue-100 text-blue-700', 'bg-purple-100 text-purple-700', 'bg-emerald-100 text-emerald-700', 'bg-amber-100 text-amber-700', 'bg-rose-100 text-rose-700']

    if (categories.length) {
      return categories.slice(0, 5).map((item, index) => ({
        label: item.label,
        value: item.value,
        className: palette[index % palette.length],
      }))
    }

    return []
  }, [data])

  return (
    <section>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-slate-900">Citações</h2>
        <p className="text-sm text-slate-500 mt-1">Análise de URLs, domínios e qualidade semântica</p>
      </div>

      <div className="grid grid-cols-1 gap-6 mb-6 lg:grid-cols-2">
        <Card className="h-full border-slate-200 bg-white/90">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold text-slate-900">Principais URLs Citadas da Marca</CardTitle>
            <CardDescription className="text-xs uppercase tracking-[0.22em] text-slate-400">URLs mais frequentes nas respostas</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1.5 pt-0">
            {topUrls.length ? (
              <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
                {topUrls.map((item, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 rounded-lg border border-slate-200/60 bg-white px-3 py-2 text-sm transition hover:-translate-y-0.5 hover:border-slate-300"
                  >
                    <Badge
                      variant="outline"
                      className="mt-0.5 shrink-0 rounded-md border-slate-200 bg-slate-50 px-2 text-[11px] font-medium text-slate-600"
                    >
                      {item.mentions}x
                    </Badge>
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <a
                        href={item.sample_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group flex items-center gap-1.5 text-sm font-medium text-blue-600 transition hover:text-blue-700"
                      >
                        <span className="truncate">{item.sample_url}</span>
                        <ExternalLink className="h-3 w-3 shrink-0 opacity-0 transition-opacity group-hover:opacity-100" />
                      </a>
                      <p className="text-[11px] text-slate-400">{item.brand}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">Nenhuma URL citada encontrada.</p>
            )}
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Qualidade Semântica</CardTitle>
            <CardDescription>Radar de atributos e categorias de valor percebido</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-2">
            <div className="h-72">
              {hasSemanticScores ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarMetrics} outerRadius={90}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12, fill: '#475569' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} stroke="#cbd5f5" />
                    <Radar dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.35} />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-slate-200 text-sm text-slate-500">
                  Análise semântica não disponível para este período.
                </div>
              )}
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">Categorias de Valor Percebido</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {perceivedValueCategories.length > 0 ? (
                  perceivedValueCategories.map((cat) => (
                    <span key={`perceived-${cat.label}`} className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${cat.className}`}>
                      {cat.label} ({cat.value}%)
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">Dados de categorias de valor não disponíveis para este período.</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
