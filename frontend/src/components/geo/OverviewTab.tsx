import { useEffect, useMemo, useState } from 'react'
import { GeoOverviewData, GeoOverviewKpi } from '../../lib/geo'
import { GeoKpiCard } from './KpiCard'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../../components/ui/card'
import { getGeoColorByIndex, getGeoColorByName, geoColorWithAlpha } from '../../lib/geoPalette'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  Tooltip,
  Legend,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
  Label,
  Sector,
  ComposedChart,
  Bar,
} from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'

type OverviewTabProps = {
  overview: GeoOverviewData | null
  isLoading: boolean
}

function renderKpis(kpis: GeoOverviewKpi[]) {
  if (!kpis.length) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-slate-500">
          Nenhum KPI disponível para o período selecionado.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 md:gap-6 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.slice(0, 4).map((kpi) => {
        let displayValue = '–'
        let displayUnit = kpi.unit

        if (kpi.value != null) {
          if (kpi.unit === 'percent') {
            displayValue = kpi.value.toFixed(1)
            displayUnit = '%'
          } else if (kpi.unit === 'total') {
            displayValue = Math.round(kpi.value).toLocaleString('pt-BR')
            displayUnit = undefined
          } else if (kpi.unit === 'score') {
            displayValue = Math.round(kpi.value).toString()
            displayUnit = undefined
          } else {
            displayValue = kpi.value.toFixed(1)
          }
        }

        return (
          <GeoKpiCard
            key={kpi.id}
            title={kpi.label}
            value={displayValue}
            delta={kpi.delta ?? null}
            unit={displayUnit}
            deltaUnit={kpi.deltaUnit ?? null}
            trendDirection={kpi.trendDirection ?? null}
            footerPrimary={kpi.footerPrimary || null}
            footerSecondary={kpi.footerSecondary || null}
          />
        )
      })}
    </div>
  )
}

type ShareOfVoiceSectionProps = {
  shareOfVoice?: Record<string, number>
  metrics?: GeoOverviewData['metrics']
}

function ShareOfVoiceSection({ shareOfVoice, metrics }: ShareOfVoiceSectionProps) {
  const data = useMemo(
    () =>
      Object.entries(shareOfVoice || {}).map(([name, value], index) => ({
        name,
        value,
        color: getGeoColorByName(name, index),
      })),
    [shareOfVoice]
  )

  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    if (data.length) {
      setActiveIndex(0)
    }
  }, [data.length])

  if (!data.length) {
    return (
      <Card className="border-dashed border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Share of Voice</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-slate-500">
          Sem dados de share of voice para este intervalo. Execute novas runs para alimentar a análise competitiva.
        </CardContent>
      </Card>
    )
  }

  const activeSlice = data[activeIndex] || data[0]
  const ratio = metrics?.competitorMentionRatioAvg
  const cocitation = metrics?.cocitationPercentage
  const accentColor = getGeoColorByIndex(0)
  const accentBorderColor = geoColorWithAlpha(accentColor, 0.25)

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-0">
        <CardTitle className="text-base">Share of Voice (LLM)</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 p-0">
        <div className="flex flex-col lg:flex-row gap-6 p-6">
          <div className="flex-1 min-h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip
                  cursor={false}
                  formatter={(value: any, name: string) => [`${Number(value).toFixed(1)}%`, name]}
                />
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={70}
                  outerRadius={100}
                  strokeWidth={4}
                  activeIndex={activeIndex}
                  onMouseEnter={(_, index) => setActiveIndex(index)}
                  activeShape={({ outerRadius = 0, ...props }) => (
                    <g>
                      <Sector {...props} outerRadius={outerRadius + 6} />
                      <Sector {...props} innerRadius={outerRadius + 10} outerRadius={outerRadius + 18} />
                    </g>
                  )}
                >
                  {data.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                  <Label
                    content={({ viewBox }) => {
                      if (viewBox && 'cx' in viewBox && 'cy' in viewBox && activeSlice) {
                        return (
                          <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle" dominantBaseline="middle">
                            <tspan x={viewBox.cx} y={viewBox.cy} className="fill-slate-900 text-3xl font-semibold">
                              {activeSlice.value.toFixed(1)}%
                            </tspan>
                            <tspan x={viewBox.cx} y={(viewBox.cy || 0) + 24} className="fill-slate-500 text-sm">
                              {activeSlice.name}
                            </tspan>
                          </text>
                        )
                      }
                      return null
                    }}
                  />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="w-full lg:w-60 space-y-5">
            <div className="space-y-2">
              {data.map((entry, index) => (
                <button
                  key={entry.name}
                  type="button"
                  onMouseEnter={() => setActiveIndex(index)}
                  className="flex w-full items-center justify-between rounded-md border px-3 py-2 text-sm transition"
                  style={
                    index === activeIndex
                      ? {
                          borderColor: accentColor,
                          backgroundColor: geoColorWithAlpha(accentColor, 0.08),
                          color: accentColor,
                        }
                      : {
                          borderColor: accentBorderColor,
                        }
                  }
                >
                  <span className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: entry.color }} />
                    <span className="truncate text-left">{entry.name}</span>
                  </span>
                  <span className="font-semibold">{entry.value.toFixed(1)}%</span>
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 gap-4 text-sm text-slate-600">
              <div>
                <p className="uppercase text-[11px] tracking-[0.2em] text-slate-400">Ratio competitivo</p>
                <p className="text-lg font-semibold text-slate-900">{ratio != null ? ratio.toFixed(2) : '–'}</p>
                <p className="text-xs text-slate-500 mt-1">nossas menções / (nossas + concorrentes)</p>
              </div>
              <div>
                <p className="uppercase text-[11px] tracking-[0.2em] text-slate-400">Co-citações</p>
                <p className="text-lg font-semibold" style={{ color: accentColor }}>
                  {cocitation != null ? `${cocitation.toFixed(0)}%` : '–'}
                </p>
                <p className="text-xs text-slate-500 mt-1">runs com menções compartilhadas com concorrentes</p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex flex-col gap-2 border-t border-slate-100 bg-slate-50/40 px-6 py-4 text-sm text-slate-600">
        <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Resumo competitivo</div>
        <div>Monitoramento diário das principais marcas citadas em experiências LLM.</div>
      </CardFooter>
    </Card>
  )
}

function renderBrandPresence(overview: GeoOverviewData | null) {
  const timeline = overview?.brandTimeline || []

  if (!timeline.length) {
    return (
      <Card className="border-dashed border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Presença da Marca</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-slate-500">
          Ainda não temos histórico de menções suficiente para este intervalo.
        </CardContent>
      </Card>
    )
  }

  const chartData = timeline.slice(-8).map((point) => {
    const date = new Date(point.date)
    const label = Number.isNaN(date.getTime())
      ? point.date
      : date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '')

    return {
      label,
      mentions: point.mentions ?? 0,
      firstMentionPct: point.firstMentionAvg ?? null,
      mentionDensity: point.densityAvg ?? null,
    }
  })

  const latest = chartData[chartData.length - 1]
  const previous = chartData.length > 1 ? chartData[chartData.length - 2] : null
  const mentionDelta = previous ? (latest.mentions ?? 0) - (previous.mentions ?? 0) : null
  const DeltaIcon = mentionDelta != null && mentionDelta < 0 ? TrendingDown : TrendingUp
  const mentionDeltaText = mentionDelta == null
    ? 'Variação indisponível para o período atual'
    : `${mentionDelta > 0 ? '+' : ''}${mentionDelta.toFixed(0)} menções vs. ponto anterior`

  const densityMetric = latest?.mentionDensity ?? null
  const firstMentionMetric = latest?.firstMentionPct ?? null

  const mentionsColor = getGeoColorByIndex(0)
  const firstMentionColor = getGeoColorByIndex(1)
  const accentColor = getGeoColorByIndex(2)

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Presença da Marca</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 pt-0">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 16, right: 24, bottom: 12, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis yAxisId="mentions" stroke={mentionsColor} tick={{ fontSize: 12 }} allowDecimals={false} />
              <YAxis
                yAxisId="percent"
                orientation="right"
                stroke={firstMentionColor}
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `${value.toFixed(0)}%`}
                domain={[0, 100]}
              />
              <Tooltip
                cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }}
                formatter={(value: any, key: string) => {
                  if (key === 'firstMentionPct') {
                    return [`${Number(value).toFixed(1)}%`, 'Primeira menção']
                  }
                  if (key === 'mentionDensity') {
                    return [`${Number(value).toFixed(2)} por 1k chars`, 'Densidade']
                  }
                  return [value, 'Menções']
                }}
                labelFormatter={(label: string) => `Dia ${label}`}
              />
              <Legend
                verticalAlign="bottom"
                height={32}
                formatter={(value) =>
                  value === 'mentions'
                    ? 'Menções'
                    : value === 'firstMentionPct'
                      ? 'Primeira menção (%)'
                      : 'Densidade'
                }
              />
              <Bar yAxisId="mentions" dataKey="mentions" name="Menções" fill={mentionsColor} radius={[6, 6, 0, 0]} />
              <Bar yAxisId="percent" dataKey="firstMentionPct" name="Primeira menção (%)" fill={firstMentionColor} radius={[6, 6, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
      <CardFooter className="-mt-10 flex flex-col gap-3 px-6 pb-6 text-sm text-slate-600">
        <div className="flex items-center gap-2 font-medium text-slate-800">
          <DeltaIcon className="h-4 w-4" />
          {mentionDeltaText}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-white px-4 py-3 shadow-sm border border-slate-100">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Densidade de Menções</p>
            <p className="text-2xl font-semibold text-slate-900 mt-2">
              {densityMetric != null ? densityMetric.toFixed(2) : '–'}
            </p>
            <p className="text-xs text-slate-500 mt-1">menções por 1000 caracteres</p>
          </div>
          <div className="rounded-lg bg-white px-4 py-3 shadow-sm border border-slate-100">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Posição Média 1ª Menção</p>
            <p className="text-2xl font-semibold text-slate-900 mt-2">
              {firstMentionMetric != null ? `${firstMentionMetric.toFixed(1)}%` : '–'}
            </p>
            <p className="text-xs text-slate-500 mt-1">do início do texto</p>
          </div>
        </div>
      </CardFooter>
    </Card>
  )
}

function renderTimeline(overview: GeoOverviewData | null) {
  const timeline = overview?.timeline || []
  const metrics = overview?.metrics

  const cards = metrics
    ? [
        {
          title: 'Densidade de Menções',
          value: metrics.brandMentionDensityAvg != null ? `${metrics.brandMentionDensityAvg.toFixed(2)}` : '–',
          description: 'menções por 1000 caracteres',
        },
        {
          title: 'Posição 1ª Menção',
          value: metrics.brandFirstMentionPositionAvg != null ? `${metrics.brandFirstMentionPositionAvg.toFixed(1)}%` : '–',
          description: 'da resposta (quanto menor, melhor)',
        },
        {
          title: 'Gatilhos Conversacionais',
          value: metrics.conversationalTriggerAvg != null ? metrics.conversationalTriggerAvg.toFixed(1) : '–',
          description: 'média de CTAs por resposta',
        },
        {
          title: 'Score de Engajamento',
          value: metrics.engagementScoreAvg != null ? metrics.engagementScoreAvg.toFixed(0) : '–',
          description: 'de 0 a 100 pontos',
        },
        {
          title: 'Potencial de Conversão',
          value: metrics.conversionPotentialScoreAvg != null ? metrics.conversionPotentialScoreAvg.toFixed(0) : '–',
          description: metrics.topConversionPotential ? `${metrics.topConversionPotential} predominante` : undefined,
        },
      ]
    : []

  const metricsRow = cards.length ? (
    <CardFooter className="border-t border-slate-100 bg-slate-50/40 px-6 py-5">
      <div className="grid w-full gap-3 md:grid-cols-2 xl:grid-cols-5">
        {cards.map((card, index) => (
          <div
            key={card.title}
            className="rounded-xl border bg-white px-4 py-3 shadow-sm"
            style={{ borderColor: geoColorWithAlpha(getGeoColorByIndex(index), 0.35) }}
          >
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{card.title}</p>
            <p className="text-2xl font-semibold text-slate-900 mt-2">{card.value}</p>
            {card.description ? <p className="text-xs text-slate-500 mt-1">{card.description}</p> : null}
          </div>
        ))}
      </div>
    </CardFooter>
  ) : null

  if (!timeline.length) {
    return (
      <Card className="border-dashed border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Engajamento vs. Potencial de Conversão</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-sm text-slate-500">
          Ainda não há séries temporais suficientes para este recorte.
        </CardContent>
        {metricsRow}
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Engajamento vs. Potencial de Conversão</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={timeline} margin={{ top: 12, right: 20, bottom: 12, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 12 }} />
              <YAxis stroke="#94a3b8" domain={[0, 100]} tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: any) => `${Number(value).toFixed(1)} pts`} labelStyle={{ fontWeight: 600 }} />
              <Legend />
              <Line type="monotone" dataKey="engagement" name="Engajamento" stroke="#2563eb" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="conversionPotential" name="Potencial de Conversão" stroke="#f97316" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
      {metricsRow}
    </Card>
  )
}

export function OverviewTab({ overview, isLoading }: OverviewTabProps) {
  if (isLoading) {
    return (
      <div className="grid gap-4">
        <Card><CardContent className="h-24 animate-pulse bg-slate-100" /></Card>
        <Card><CardContent className="h-72 animate-pulse bg-slate-100" /></Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {renderKpis(overview?.kpis || [])}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-stretch">
        <div className="h-full">{renderBrandPresence(overview)}</div>
        <div className="h-full">
          <ShareOfVoiceSection shareOfVoice={overview?.shareOfVoice} metrics={overview?.metrics} />
        </div>
      </div>
      {renderTimeline(overview)}
    </div>
  )
}
