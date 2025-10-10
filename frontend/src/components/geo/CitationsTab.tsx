import { GeoAggregations } from '../../lib/geo'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { ResponsiveContainer, LineChart, Line, CartesianGrid, Tooltip, XAxis, YAxis, Legend, BarChart, Bar } from 'recharts'

const formatPercent = (value: number | null | undefined) =>
  value == null ? '–' : `${value.toFixed(1)}%`

const formatNumber = (value: number | null | undefined, digits = 1) =>
  value == null ? '–' : value.toFixed(digits)

export type CitationsTabProps = {
  aggregations: GeoAggregations | null
  isLoading: boolean
}

export function CitationsTab({ aggregations, isLoading }: CitationsTabProps) {
  if (isLoading) {
    return (
      <div className="grid gap-6">
        <Card><CardContent className="h-64 bg-slate-100 animate-pulse" /></Card>
        <Card><CardContent className="h-64 bg-slate-100 animate-pulse" /></Card>
      </div>
    )
  }

  const byProduct = aggregations?.byProduct || []
  const byFunnel = aggregations?.byFunnel || []
  const byQuestion = aggregations?.byQuestionType || []

  const summaryCards = [
    {
      title: 'CR Observado médio',
      value:
        formatPercent(
          (() => {
            const values = [...byProduct, ...byFunnel, ...byQuestion]
              .map((item: any) => item.avg_citation_rate)
              .filter((v): v is number => v != null)
            if (!values.length) return null
            return values.reduce((acc, v) => acc + v, 0) / values.length
          })()
        ),
      description: 'média ponderada entre produtos, funil e tipos de pergunta',
    },
    {
      title: 'Runs analisadas',
      value: (() => {
        const value = [...byProduct, ...byFunnel, ...byQuestion]
          .map((item: any) => item.runs_count || 0)
          .reduce((acc, v) => acc + v, 0)
        return value ? value.toLocaleString('pt-BR') : '0'
      })(),
      description: 'total consolidado no período selecionado',
    },
    {
      title: 'Score de engajamento médio',
      value:
        formatNumber(
          (() => {
            const values = [...byProduct, ...byFunnel]
              .map((item: any) => item.avg_engagement)
              .filter((v): v is number => v != null)
            if (!values.length) return null
            return values.reduce((acc, v) => acc + v, 0) / values.length
          })(),
          0
        ),
      description: 'quando disponível nos runs do período',
    },
    {
      title: 'Potencial de conversão',
      value:
        formatNumber(
          (() => {
            const values = [...byProduct, ...byFunnel]
              .map((item: any) => item.avg_conversion_potential)
              .filter((v): v is number => v != null)
            if (!values.length) return null
            return values.reduce((acc, v) => acc + v, 0) / values.length
          })(),
          0
        ),
      description: 'score médio considerando agregados',
    },
  ]

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Taxa de Citação por Produto</CardTitle>
          <CardDescription>Comparativo de CR, engajamento e conversão por categoria detectada nas respostas.</CardDescription>
        </CardHeader>
        <CardContent>
          {byProduct.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={byProduct} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="product_category" stroke="#94a3b8" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} domain={[0, 100]} />
                  <Tooltip
                    formatter={(value: any, key: string) =>
                      key === 'avg_engagement'
                        ? [`${Number(value).toFixed(1)} pts`, 'Engajamento']
                        : key === 'avg_conversion_potential'
                          ? [`${Number(value).toFixed(1)} pts`, 'Potencial de Conversão']
                          : [`${Number(value).toFixed(1)}%`, 'CR Observado']
                    }
                  />
                  <Legend />
                  <Bar dataKey="avg_citation_rate" name="CR Observado" fill="#2563eb" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="avg_conversion_potential" name="Potencial de Conversão" fill="#f97316" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="avg_engagement" name="Engajamento" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Sem dados disponíveis para produtos no período selecionado.</p>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Taxa de Citação por Estágio de Funil</CardTitle>
            <CardDescription>Média de CR, engajamento e potencial por estágio.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Estágio</TableHead>
                  <TableHead className="text-right">CR Observado</TableHead>
                  <TableHead className="text-right">Engajamento</TableHead>
                  <TableHead className="text-right">Potencial</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {byFunnel.length ? (
                  byFunnel.map((item) => (
                    <TableRow key={item.funnel_stage || 'unknown'}>
                      <TableCell className="capitalize">{item.funnel_stage || 'Sem estágio'}</TableCell>
                      <TableCell className="text-right">{formatPercent(item.avg_citation_rate)}</TableCell>
                      <TableCell className="text-right">{formatNumber(item.avg_engagement)}</TableCell>
                      <TableCell className="text-right">{formatNumber(item.avg_conversion_potential)}</TableCell>
                      <TableCell className="text-right">{item.runs_count}</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} className="text-sm text-slate-500">Sem dados para estágios de funil.</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Taxa por Tipo de Pergunta</CardTitle>
            <CardDescription>Quebra por intenção de busca detectada nas perguntas analisadas.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead className="text-right">CR Observado</TableHead>
                  <TableHead className="text-right">Prominência</TableHead>
                  <TableHead className="text-right">SOV</TableHead>
                  <TableHead className="text-right">Potencial</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {byQuestion.length ? (
                  byQuestion.map((item) => (
                    <TableRow key={item.question_type || 'unknown'}>
                      <TableCell className="capitalize">{item.question_type || 'Sem tipo'}</TableCell>
                      <TableCell className="text-right">{formatPercent(item.avg_citation_rate)}</TableCell>
                      <TableCell className="text-right">{formatNumber(item.avg_prominence)}</TableCell>
                      <TableCell className="text-right">{formatPercent(item.avg_sov)}</TableCell>
                      <TableCell className="text-right">{formatNumber(item.avg_conversion_potential)}</TableCell>
                      <TableCell className="text-right">{item.runs_count}</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-sm text-slate-500">Sem dados para tipos de pergunta.</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <Card className="border-dashed border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Monitoramento de Domínios</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500">
          A consolidação de variantes de domínio será exibida aqui assim que houver dados agregados suficientes.
        </CardContent>
      </Card>
    </div>
  )
}
