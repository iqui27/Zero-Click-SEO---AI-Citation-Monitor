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
  Legend,
  Cell,
} from 'recharts'
import type { GeoDashboard } from '../../lib/api'
import { getGeoColorByName } from '../../lib/geoPalette'

export function CompetitivePresenceSection({ data }: { data: GeoDashboard }) {
  const productPresence = (data.positioning as any)?.product_presence || []

  const chartData = useMemo(() => {
    if (!productPresence.length) return []

    // Get all products with their percentages
    return productPresence.map((item: any) => {
      // Find if our brand (BB) is in top brands for this product
      const topBrands = item.top_brands || []
      const ourBrand = topBrands.find((b: any) => 
        b.brand.toLowerCase().includes('bb.com.br') || 
        b.brand.toLowerCase().includes('banco do brasil')
      )
      
      return {
        product: item.product,
        mentions: item.total_mentions,
        percentage: item.percentage,
        isOurs: !!ourBrand,
        ourShare: ourBrand ? ourBrand.share : 0,
        topBrands: topBrands.slice(0, 3).map((b: any) => `${b.brand} (${b.share}%)`).join(', '),
      }
    })
  }, [productPresence])

  if (!chartData.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Presença Competitiva por Produto</CardTitle>
          <CardDescription>% de presença de concorrentes por produto</CardDescription>
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
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Presença Competitiva por Produto</CardTitle>
        <CardDescription>% de presença de concorrentes por produto</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 12, right: 40, bottom: 12, left: 120 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={true} vertical={false} />
              <XAxis
                type="number"
                stroke="#94a3b8"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                domain={[0, 100]}
                label={{ value: '% de Presença', position: 'insideBottom', offset: -8, fontSize: 12, fill: '#64748b' }}
              />
              <YAxis
                dataKey="product"
                type="category"
                stroke="#94a3b8"
                tick={{ fontSize: 12 }}
                width={110}
                tickLine={false}
                axisLine={false}
              />
              <RechartsTooltip
                formatter={(value: any, name: string, props: any) => {
                  if (name === 'percentage') {
                    return [`${value}%`, 'Presença']
                  }
                  return [value, name]
                }}
                labelFormatter={(label: string) => `Produto: ${label}`}
                contentStyle={{
                  backgroundColor: 'rgba(255, 255, 255, 0.96)',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '8px 12px',
                }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload
                    return (
                      <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-lg">
                        <p className="font-semibold text-slate-900 capitalize">{data.product}</p>
                        <p className="text-sm text-slate-600 mt-1">{data.percentage}% de presença</p>
                        <p className="text-xs text-slate-500 mt-1">{data.mentions} menções</p>
                        {data.topBrands && (
                          <p className="text-xs text-slate-500 mt-2 border-t border-slate-100 pt-2">
                            Top: {data.topBrands}
                          </p>
                        )}
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, paddingTop: '12px' }}
                formatter={(value) => (value === 'percentage' ? 'Presença (%)' : value)}
              />
              <Bar dataKey="percentage" name="percentage" radius={[0, 6, 6, 0]}>
                {chartData.map((entry: any, index: number) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getGeoColorByName(entry.product, index)}
                    fillOpacity={entry.isOurs ? 1 : 0.7}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Total de Produtos</p>
            <p className="text-2xl font-bold text-slate-900">{productPresence.length}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Total de Menções</p>
            <p className="text-2xl font-bold text-slate-900">
              {productPresence.reduce((sum: number, p: any) => sum + p.total_mentions, 0)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
