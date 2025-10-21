import { useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  Cell,
} from 'recharts'
import type { GeoDashboard } from '../../lib/api'
import { getGeoColorByName } from '../../lib/geoPalette'

const PRODUCT_LABELS: Record<string, string> = {
  cartoes: 'Cartões',
  credito: 'Crédito',
  investimentos: 'Investimentos',
  conta: 'Conta',
  seguros: 'Seguros',
  empresarial: 'Empresarial',
  digital: 'Digital',
  multiproduto: 'Multiproduto',
  outros: 'Outros',
}

export function CompetitivePresenceSection({ data }: { data: GeoDashboard }) {
  const productPresence = (data.positioning as any)?.product_presence || []

  type ProductBrand = {
    name: string
    share: number
    mentions: number
    color: string
  }

  type ProductChart = {
    productKey: string | null | undefined
    productLabel: string
    totalMentions: number
    percentage: number
    brands: ProductBrand[]
  }

  const perProductCharts = useMemo<ProductChart[]>(() => {
    if (!Array.isArray(productPresence) || !productPresence.length) {
      return []
    }

    return productPresence
      .map((item: any) => {
        const topBrands = Array.isArray(item.top_brands) ? item.top_brands.slice(0, 5) : []
        const brands: ProductBrand[] = topBrands
          .map((brand: any, index: number) => ({
            name: brand.brand,
            share: brand.share ?? 0,
            mentions: brand.mentions ?? 0,
            color: getGeoColorByName(brand.brand, index),
          }))
          .filter((brand: ProductBrand) => brand.share > 0 && brand.name !== 'vertexaisearch.cloud.google.com')

        if (!brands.length) {
          return null
        }

        return {
          productKey: item.product,
          productLabel: PRODUCT_LABELS[item.product] || item.product,
          totalMentions: item.total_mentions ?? 0,
          percentage: item.percentage ?? 0,
          brands,
        } satisfies ProductChart | null
      })
      .filter((chart): chart is ProductChart => chart !== null)
  }, [productPresence])

  if (!perProductCharts.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Presença por Produto</CardTitle>
          <CardDescription>Top 5 domínios por produto nas respostas das LLMs</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">
            Sem dados de presença competitiva disponíveis para o período selecionado.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="dark:bg-[color:var(--surface-card)] dark:border-[color:var(--border-strong)]">
      <CardHeader>
        <CardTitle className="text-base">Presença por Produto</CardTitle>
        <CardDescription>Top 5 domínios por produto nas respostas das LLMs</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {perProductCharts.map((item) => (
            <div
              key={item.productKey || item.productLabel}
              className="rounded-xl border border-slate-200/70 bg-white/80 p-4 shadow-sm dark:border-[color:var(--border-strong)] dark:bg-[color:var(--surface-elevated)]/85"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-[color:var(--text-primary)]">{item.productLabel}</p>
                  <p className="text-xs text-slate-500 mt-0.5 dark:text-[color:var(--text-muted)]">
                    {item.percentage?.toFixed?.(1) ?? '0.0'}% do total
                  </p>
                </div>
              </div>

              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={item.brands}
                    layout="vertical"
                    margin={{ top: 8, right: 24, bottom: 8, left: 120 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#e2e8f0"
                      horizontal
                      vertical={false}
                      className="dark:stroke-[color:var(--border-muted)]"
                    />
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      tick={{ fontSize: 12, fill: 'var(--text-muted, #475569)' }}
                      className="dark:[&_.recharts-cartesian-axis-tick-value]:fill-[color:var(--text-muted)]"
                      axisLine={false}
                      tickLine={false}
                      stroke="var(--border-subtle, #94a3b8)"
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={110}
                      tick={{ fontSize: 12, fill: 'var(--text-primary, #334155)' }}
                      className="dark:[&_.recharts-cartesian-axis-tick-value]:fill-[color:var(--text-primary)]"
                      axisLine={false}
                      tickLine={false}
                    />
                    <RechartsTooltip
                      formatter={(value: any, _name, payload) => {
                        const data = payload?.payload
                        const formatted = typeof value === 'number' ? `${value.toFixed(1)}%` : value
                        return [
                          `${formatted}`,
                          data?.name ? data.name : 'Marca',
                          data,
                        ]
                      }}
                      labelFormatter={() => undefined}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const brandData = payload[0].payload
                          return (
                            <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-lg dark:border-[color:var(--border-strong)] dark:bg-[color:var(--surface-card)]/95">
                              <p className="text-sm font-semibold text-slate-900 dark:text-[color:var(--text-primary)]">{brandData.name}</p>
                              <p className="text-xs text-slate-500 mt-1 dark:text-[color:var(--text-muted)]">
                                {brandData.share?.toFixed?.(1) ?? '0.0'}% das menções
                              </p>
                            </div>
                          )
                        }
                        return null
                      }}
                    />
                    <Bar dataKey="share" radius={[0, 6, 6, 0]}>
                      {item.brands.map((brand, index) => (
                        <Cell key={`${item.productKey}-${brand.name}-${index}`} fill={brand.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ))}
        </div>

      </CardContent>
    </Card>
  )
}
