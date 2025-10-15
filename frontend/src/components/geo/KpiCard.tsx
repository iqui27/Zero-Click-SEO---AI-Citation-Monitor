import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { getGeoColorByIndex, geoColorWithAlpha } from '../../lib/geoPalette'

export type GeoKpiCardProps = {
  title: string
  value: string
  unit?: string
  delta?: number | null
  deltaUnit?: 'percent' | 'points' | null
  trendDirection?: 'up' | 'down' | 'neutral' | null
  footerPrimary?: string | null
  footerSecondary?: string | null
}

export function GeoKpiCard({
  title,
  value,
  unit,
  delta,
  deltaUnit,
  trendDirection,
  footerPrimary,
  footerSecondary,
}: GeoKpiCardProps) {
  const primaryColor = getGeoColorByIndex(0)
  const positiveColor = getGeoColorByIndex(7)
  const negativeColor = getGeoColorByIndex(8)
  const neutralColor = getGeoColorByIndex(1)

  const resolvedDirection: 'up' | 'down' | 'neutral' = trendDirection
    ? trendDirection
    : delta == null
      ? 'neutral'
      : delta > 0
        ? 'up'
        : delta < 0
          ? 'down'
          : 'neutral'

  const TrendIcon = resolvedDirection === 'up' ? TrendingUp : resolvedDirection === 'down' ? TrendingDown : Minus
  const showBadge = delta != null
  const formattedDelta = !showBadge
    ? null
    : deltaUnit === 'points'
      ? `${delta > 0 ? '+' : ''}${delta.toFixed(1)} pts`
      : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}%`

  const badgeStyles = (() => {
    const base = {
      borderColor: geoColorWithAlpha(primaryColor, 0.25),
      backgroundColor: geoColorWithAlpha(neutralColor, 0.15),
      color: neutralColor,
    }

    if (resolvedDirection === 'up') {
      return {
        borderColor: geoColorWithAlpha(positiveColor, 0.25),
        backgroundColor: geoColorWithAlpha(positiveColor, 0.2),
        color: positiveColor,
      }
    }

    if (resolvedDirection === 'down') {
      return {
        borderColor: geoColorWithAlpha(negativeColor, 0.25),
        backgroundColor: geoColorWithAlpha(negativeColor, 0.2),
        color: negativeColor,
      }
    }

    return base
  })()

  const hasFooter = Boolean(footerPrimary || footerSecondary)

  return (
    <Card
      className="relative overflow-hidden border-slate-200 shadow-sm dark:border-slate-800 dark:from-slate-900/30 dark:via-slate-900 dark:to-slate-900"
      style={{
        background: `linear-gradient(180deg, ${geoColorWithAlpha(primaryColor, 0.18)} 0%, rgba(255,255,255,0.96) 60%, rgba(255,255,255,1) 100%)`,
      }}
    >
      <CardHeader className="gap-3 pb-4">
        <CardDescription className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.25em] text-slate-500">
          {title}
        </CardDescription>
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-3xl font-semibold text-slate-900 dark:text-slate-50">
            <span>{value}</span>
            {unit ? <span className="ml-1 text-base font-medium text-slate-500 dark:text-slate-300">{unit}</span> : null}
          </CardTitle>
          {showBadge ? (
            <Badge
              variant="outline"
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium"
              style={badgeStyles}
            >
              <TrendIcon className="h-4 w-4" />
              {formattedDelta}
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      {hasFooter ? (
        <CardFooter className="flex-col items-start gap-2 text-sm">
          {footerPrimary ? (
            <div className="flex items-center gap-2 font-medium text-slate-700 dark:text-slate-200">
              {resolvedDirection !== 'neutral' ? <TrendIcon className="h-4 w-4" /> : null}
              <span>{footerPrimary}</span>
            </div>
          ) : null}
          {footerSecondary ? <div className="text-sm text-slate-500 dark:text-slate-400">{footerSecondary}</div> : null}
        </CardFooter>
      ) : null}
    </Card>
  )
}
