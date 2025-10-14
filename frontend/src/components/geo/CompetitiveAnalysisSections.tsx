import { useMemo } from 'react'
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

const COLORS = ['#2563eb', '#f97316', '#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#6366f1']

// Componente 1: Share of Voice
export function ShareOfVoiceSection({ data }: { data: GeoDashboard }) {
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
        color: COLORS[index % COLORS.length],
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
      </CardContent>
    </Card>
  )
}

// Componente 3: Contexto
export function ContextSection({ data, aggregations }: { data: GeoDashboard; aggregations: any }) {
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
    }>
    
    return items
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
  }, [aggregations])

  const funnelPresence = useMemo(() => {
    const items = (aggregations?.byFunnel || []) as Array<{
      funnel_stage: string | null
      avg_citation_rate?: number | null
    }>
    
    return items
      .filter((item) => {
        const hasStage = !!item.funnel_stage
        const hasRate = item.avg_citation_rate != null && item.avg_citation_rate > 0
        return hasStage && hasRate
      })
      .map((item) => ({
        stage: item.funnel_stage as string,
        presence: item.avg_citation_rate ?? 0,
      }))
  }, [aggregations])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Contexto</CardTitle>
        <CardDescription className="text-sm text-slate-600">
          Performance por categoria e etapa do funil
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
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
      </CardContent>
    </Card>
  )
}
