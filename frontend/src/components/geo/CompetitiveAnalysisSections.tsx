import { useMemo, type ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  Legend,
} from 'recharts'
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '../ui/chart'
import type { GeoDashboard } from '../../lib/api'
import { Grid3x3, TrendingUp, MessageSquare } from 'lucide-react'
import { getGeoColorByName } from '../../lib/geoPalette'

// Função para simplificar nomes de domínios
function simplifyBankName(name: string): string {
  // Remover .com.br, .gov.br, etc
  const withoutDomain = name.replace(/\.(com|gov|net|org)\.(br|com)/gi, '')
  
  // Mapeamento de nomes simplificados
  const nameMap: Record<string, string> = {
    'bb': 'Banco do Brasil',
    'bcb': 'BCB',
    'nubank': 'Nubank',
    'santander': 'Santander',
    'itau': 'Itaú',
    'bradesco': 'Bradesco',
    'caixa': 'Caixa',
    'inter': 'Inter',
    'c6bank': 'C6 Bank',
    'neon': 'Neon',
    'picpay': 'Picpay',
    'will': 'Will Bank',
    'banco.bradesco': 'Bradesco',
  }
  
  const lowerName = withoutDomain.toLowerCase()
  for (const [key, value] of Object.entries(nameMap)) {
    if (lowerName.includes(key)) {
      return value
    }
  }
  
  return name
}

// Componente 1: Share of Voice
export function ShareOfVoiceSection({ data }: { data: GeoDashboard }) {
  const shareOfVoice = data.positioning?.share_of_voice || {}
  const pieData = useMemo(() => {
    return Object.entries(shareOfVoice).map(([name, value]) => ({
      name: simplifyBankName(name),
      originalName: name,
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Share of Voice</CardTitle>
        <CardDescription className="text-sm text-slate-600">
          Distribuição de menções por marca no período analisado
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
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
                        color: getGeoColorByName(item.originalName, index),
                      }
                      return acc
                    }, {} as ChartConfig),
                  [pieData]
                )}
                className="mx-auto h-[400px] w-full max-w-[550px] pb-0 [&_.recharts-pie-label-text]:fill-slate-700 [&_.recharts-pie-label-text]:text-xs [&_.recharts-pie-label-text]:font-medium"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart margin={{ top: 30, right: 100, bottom: 30, left: 100 }}>
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
                        <Cell key={`cell-${index}`} fill={getGeoColorByName(entry.originalName, index)} />
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
      </CardContent>
    </Card>
  )
}

// Componente 2: Co-citação
export function CocitationSection({ data }: { data: GeoDashboard }) {
  const cocitationByCompetitor = useMemo(() => {
    const ranking = data.positioning?.brand_ranking || []
    const totalMentions = (data.positioning as any)?.total_mentions || 1

    return ranking
      .slice(1, 11)
      .map((item, index) => ({
        name: item.brand,
        value: (item.mentions / totalMentions) * 100,
        color: getGeoColorByName(item.brand, index),
      }))
      .filter(item => item.value > 0)
  }, [data])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Co-citação</CardTitle>
        <CardDescription className="text-sm text-slate-600">
          Concorrentes mencionados junto com sua marca
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {cocitationByCompetitor.length ? (
          <>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={cocitationByCompetitor}
                  layout="vertical"
                  margin={{ top: 12, right: 20, bottom: 12, left: 160 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 'dataMax']} />
                  <YAxis dataKey="name" type="category" stroke="#94a3b8" tick={{ fontSize: 12 }} width={150} />
                  <RechartsTooltip formatter={(value: any) => `${value.toFixed(1)}%`} />
                  <Bar dataKey="value" name="% de Menções" radius={[0, 6, 6, 0]}>
                    {cocitationByCompetitor.map((entry, index) => (
                      <Cell key={`cocitation-${entry.name}-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-lg bg-slate-50/40 dark:bg-[color:var(--surface-subtle)] border border-slate-200/60 dark:border-[color:var(--border-strong)] p-4">
              <h4 className="text-sm font-semibold text-slate-900 dark:text-[color:var(--text-primary)] mb-4 text-center">Concorrentes Mencionados</h4>
              <ul className="space-y-2 text-sm text-slate-700 dark:text-[color:var(--text-muted)] max-h-64 overflow-y-auto pr-2">
                {cocitationByCompetitor.map((item, index) => (
                  <li
                    key={`cocitation-list-${item.name}-${index}`}
                    className="flex items-center justify-center gap-2 text-center flex-wrap"
                  >
                    <span className="font-semibold" style={{ color: item.color }}>
                      {item.name}
                    </span>
                    <span>
                      representa <strong>{item.value.toFixed(1)}%</strong> das menções
                    </span>
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
      </CardContent>
    </Card>
  )
}

// Componente 3: Contexto e Performance LLM
export function ContextSection({ data, aggregations }: { data: GeoDashboard; aggregations: any }) {
  // Context Insights direto do backend
  const contextInsights = useMemo(() => {
    const insights = data.context_insights?.performance_by_context || []
    return insights.slice(0, 8).map((item: any) => ({
      context: item.context,
      type: item.type,
      runsCount: item.runs_count || 0,
      brandMentions: item.brand_mentions || 0,
      avgEngagement: item.avg_engagement || 0,
    }))
  }, [data])

  // Percived Value Categories
  const valueCategories = useMemo(() => {
    const categories = data.geo_summary?.perceived_value_categories || []
    return categories.map((cat: any) => ({
      label: cat.label,
      value: cat.value,
      percentage: cat.percentage,
    }))
  }, [data])

  // Performance por Categoria de Produto
  const productPerformance = useMemo(() => {
    const byProduct = (aggregations?.byProduct || []) as Array<{
      product_category: string | null
      avg_brand_mentions: number | null
      avg_engagement_score: number | null
      avg_citation_rate?: number | null
      avg_conversion_score?: number | null
    }>

    return byProduct
      .filter((item) => item.product_category)
      .map((item) => ({
        category: item.product_category as string,
        brandMentions: item.avg_brand_mentions ?? 0,
        engagement: item.avg_engagement_score ?? 0,
        citationRate: item.avg_citation_rate ?? 0,
        conversion: item.avg_conversion_score ?? 0,
      }))
      .slice(0, 6)
  }, [aggregations])

  // Question Type Performance
  const questionTypePerformance = useMemo(() => {
    return contextInsights
      .filter((item: { type: string }) => item.type === 'question_type')
      .map((item: { context: string; runsCount: number; brandMentions: number; avgEngagement: number }) => ({
        type: item.context,
        runs: item.runsCount,
        mentions: item.brandMentions,
        engagement: item.avgEngagement,
      }))
  }, [contextInsights])

  // Componentes auxiliares
  const MetricCard = ({ title, value, description, icon, color }: {
    title: string
    value: string
    description: string
    icon: ReactNode
    color: string
  }) => (
    <div className={`${color} dark:bg-[color:var(--surface-subtle)] rounded-lg p-5 border border-gray-200 dark:border-[color:var(--border-strong)]`}>
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-xs font-medium text-gray-600 dark:text-[color:var(--text-muted)] uppercase tracking-wider">{title}</h3>
      </div>
      <div className="mt-2">
        <p className="text-4xl font-bold text-gray-900 dark:text-[color:var(--text-primary)]">{value}</p>
        <p className="text-sm text-gray-600 dark:text-[color:var(--text-muted)] mt-2">{description}</p>
      </div>
    </div>
  )

  const ProductCard = ({ title, mentions, citationRate }: {
    title: string
    mentions: number
    citationRate: number
  }) => (
    <div className="bg-white dark:bg-[color:var(--surface-card)] rounded-lg border border-gray-200 dark:border-[color:var(--border-strong)] overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-4 bg-gray-50 dark:bg-[color:var(--surface-subtle)] border-b border-gray-200 dark:border-[color:var(--border-strong)]">
        <div className="flex justify-between items-center">
          <h3 className="font-semibold text-gray-800 dark:text-[color:var(--text-primary)] capitalize">{title}</h3>
          <span className="text-sm text-gray-500 dark:text-[color:var(--text-muted)]">{mentions.toFixed(0)} menções</span>
        </div>
      </div>
      <div className="p-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-600 dark:text-[color:var(--text-muted)]">Taxa de Citação</span>
          <span className={`font-semibold text-lg ${citationRate > 0 ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-gray-600'}`}>
            {citationRate.toFixed(1)}%
          </span>
        </div>
        {citationRate > 0 && (
          <div className="w-full bg-blue-100 dark:bg-blue-950/40 h-2 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 dark:bg-blue-400 h-2 rounded-full transition-all"
              style={{ width: `${Math.min(citationRate, 100)}%` }}
            ></div>
          </div>
        )}
      </div>
    </div>
  )

  const ProgressBar = ({ label, value, count, color }: {
    label: string
    value: number
    count: string
    color: string
  }) => (
    <div className="bg-white dark:bg-[color:var(--surface-card)] rounded-lg p-4 border border-gray-200 dark:border-[color:var(--border-strong)] hover:border-gray-300 dark:hover:border-[color:var(--accent-primary)] transition-colors">
      <div className="flex justify-between mb-3">
        <div className="flex flex-col">
          <span className="font-semibold text-gray-800 dark:text-[color:var(--text-primary)]">{label}</span>
          <span className="text-xs text-gray-500 dark:text-[color:var(--text-muted)] mt-1">{count}</span>
        </div>
        <span className="text-blue-600 dark:text-blue-400 font-bold text-lg">{value.toFixed(0)}%</span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700/50 h-2.5 rounded-full overflow-hidden">
        <div
          className={`${color} dark:bg-blue-500 h-2.5 rounded-full transition-all`}
          style={{ width: `${value}%` }}
        ></div>
      </div>
    </div>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-bold">Performance por Contexto</CardTitle>
        <CardDescription className="text-sm text-slate-600">
          Análise de citações e engajamento por categoria e tipo de pergunta
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        {/* Grid de Métricas Principais */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Total de Contextos"
            value={String(data.context_insights?.total_contexts || 0)}
            description="Categorias e tipos analisados"
            icon={<Grid3x3 className="h-5 w-5 text-blue-600" />}
            color="bg-blue-50"
          />
          <MetricCard
            title="Engajamento Médio"
            value={contextInsights.length ? (contextInsights.reduce((sum: number, item: { avgEngagement: number }) => sum + item.avgEngagement, 0) / contextInsights.length).toFixed(0) : '0'}
            description="Score médio de engajamento"
            icon={<TrendingUp className="h-5 w-5 text-green-600" />}
            color="bg-green-50"
          />
          <MetricCard
            title="Total de Menções"
            value={String(contextInsights.reduce((sum: number, item: { brandMentions: number }) => sum + item.brandMentions, 0))}
            description="Menções da marca no período"
            icon={<MessageSquare className="h-5 w-5 text-purple-600" />}
            color="bg-purple-50"
          />
        </div>

        {/* Categorias de Valor Percebido */}
        {valueCategories.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-[color:var(--text-primary)]">Categorias de Valor Percebido</h3>
              <span className="text-xs text-gray-500 dark:text-[color:var(--text-muted)]">Classificação por tipo de valor</span>
            </div>
            <div className="space-y-3">
              {valueCategories.map((cat: { label: string; value: number; percentage: number }, index: number) => (
                <ProgressBar
                  key={index}
                  label={cat.label.charAt(0).toUpperCase() + cat.label.slice(1)}
                  value={cat.percentage}
                  count={`${cat.value} runs`}
                  color="bg-blue-500"
                />
              ))}
            </div>
          </div>
        )}

        {/* Performance por Categoria de Produto */}
        {productPerformance.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-[color:var(--text-primary)]">Performance por Categoria de Produto</h3>
              <span className="text-xs text-gray-500 dark:text-[color:var(--text-muted)]">Taxa de Citação por Categoria</span>
            </div>
            
            {/* Lista de barras horizontais */}
            <div className="space-y-4">
              {productPerformance.map((item, index) => (
                <div key={index} className="bg-white dark:bg-[color:var(--surface-card)] rounded-lg p-4 border border-gray-200 dark:border-[color:var(--border-strong)]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-base font-semibold text-gray-800 dark:text-[color:var(--text-primary)] capitalize">
                      {item.category}
                    </span>
                    <span className="text-lg font-bold text-gray-900 dark:text-[color:var(--text-primary)]">
                      {item.citationRate > 0 ? `${item.citationRate.toFixed(1)}%` : '–'}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700/50 h-3 rounded-full overflow-hidden">
                    <div
                      className="bg-blue-500 dark:bg-blue-400 h-3 rounded-full transition-all"
                      style={{ width: `${Math.min(item.citationRate, 100)}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Performance por Tipo de Pergunta */}
        {questionTypePerformance.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-[color:var(--text-primary)]">Performance por Tipo de Pergunta</h3>
              <span className="text-xs text-gray-500 dark:text-[color:var(--text-muted)]">Análise por intent</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {questionTypePerformance.map((item: { type: string; runs: number; mentions: number; engagement: number }, index: number) => (
                <div key={index} className="bg-white dark:bg-[color:var(--surface-card)] rounded-lg border border-gray-200 dark:border-[color:var(--border-strong)] p-5 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-100 dark:border-[color:var(--border-strong)]">
                    <h4 className="font-semibold text-gray-800 dark:text-[color:var(--text-primary)] capitalize">{item.type}</h4>
                    <span className="text-xs text-gray-500 dark:text-[color:var(--text-muted)] bg-gray-100 dark:bg-[color:var(--surface-subtle)] px-2 py-1 rounded">{item.runs} runs</span>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-[color:var(--text-muted)]">Menções</span>
                      <span className="text-xl font-bold text-gray-900 dark:text-[color:var(--text-primary)]">{item.mentions}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-[color:var(--text-muted)]">Engajamento</span>
                      <span className="text-xl font-bold text-green-600 dark:text-green-400">{item.engagement.toFixed(0)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {contextInsights.length === 0 && productPerformance.length === 0 && (
          <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 text-center">
            <svg className="h-12 w-12 text-slate-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p className="text-sm font-medium text-slate-700">Sem dados de contexto disponíveis</p>
            <p className="text-xs text-slate-500 mt-1">Execute runs para visualizar performance por categoria e tipo de pergunta</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
