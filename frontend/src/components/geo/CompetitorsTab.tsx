import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, Tooltip } from 'recharts'
import { getGeoColorByIndex, getGeoColorByName, geoColorWithAlpha } from '../../lib/geoPalette'

export type CompetitorMetric = {
  name: string
  shareOfVoice: number
  mentionRatio?: number
}

export type SemanticQualityPoint = {
  dimension: string
  value: number
}

export type CompetitorsTabProps = {
  shareOfVoice?: Record<string, number>
  semanticQuality?: SemanticQualityPoint[]
}

export function CompetitorsTab({ shareOfVoice, semanticQuality }: CompetitorsTabProps) {
  const sovEntries = shareOfVoice ? Object.entries(shareOfVoice) : []
  const radarData = semanticQuality || []

  const radarStroke = getGeoColorByIndex(0)
  const radarFill = geoColorWithAlpha(getGeoColorByIndex(0), 0.25)
  const polarGridStroke = geoColorWithAlpha(getGeoColorByIndex(1), 0.3)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Share of Voice (LLM)</CardTitle>
        </CardHeader>
        <CardContent>
          {sovEntries.length ? (
            <ul className="space-y-2 text-sm text-slate-700">
              {sovEntries.map(([name, value]) => (
                <li key={name} className="flex justify-between">
                  <span className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: getGeoColorByName(name, 0) }}
                    />
                    <span>{name}</span>
                  </span>
                  <span className="font-semibold">{value.toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">Sem dados de share of voice para este intervalo.</p>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Qualidade Semântica</CardTitle>
        </CardHeader>
        <CardContent>
          {radarData.length ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius={110}>
                  <PolarGrid stroke={polarGridStroke} />
                  <PolarAngleAxis dataKey="dimension" stroke="#475569" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis angle={45} stroke={geoColorWithAlpha(getGeoColorByIndex(2), 0.6)} tick={{ fontSize: 10 }} domain={[0, 100]} />
                  <Tooltip formatter={(value: any) => `${Number(value).toFixed(1)} pts`} />
                  <Radar name="Qualidade" dataKey="value" stroke={radarStroke} fill={radarFill} fillOpacity={0.6} />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Ainda não há métricas de qualidade semântica agregadas.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
