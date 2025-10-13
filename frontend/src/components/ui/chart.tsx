import * as React from 'react'
import {
  Tooltip as RechartsTooltip,
  type TooltipProps,
} from 'recharts'

import { cn } from '../../lib/utils'

export type ChartConfig = Record<
  string,
  {
    label?: string
    color?: string
  }
>

type ChartContainerProps = React.HTMLAttributes<HTMLDivElement> & {
  config: ChartConfig
}

export const ChartContainer = React.forwardRef<HTMLDivElement, ChartContainerProps>(
  ({ config, className, style, children, ...props }, ref) => {
    const cssVars = React.useMemo(() => {
      return Object.entries(config).reduce<Record<string, string>>((acc, [key, value]) => {
        if (value?.color) {
          acc[`--color-${key}`] = value.color
        }
        return acc
      }, {})
    }, [config])

    return (
      <div
        ref={ref}
        style={{ ...cssVars, ...style }}
        className={cn('relative flex h-full w-full flex-1 items-center justify-center', className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)
ChartContainer.displayName = 'ChartContainer'

type ChartTooltipProps = TooltipProps<number, string>

export function ChartTooltip({ content, cursor, wrapperStyle, ...props }: ChartTooltipProps) {
  return (
    <RechartsTooltip
      {...props}
      cursor={cursor ?? { fill: 'var(--chart-cursor, rgba(148, 163, 184, 0.15))' }}
      wrapperStyle={{ outline: 'none', border: 'none', borderRadius: '0.5rem', ...wrapperStyle }}
      content={content}
    />
  )
}

type ChartTooltipItem = {
  name?: React.ReactNode
  value?: React.ReactNode
  color?: string
}

type ChartTooltipContentProps = React.HTMLAttributes<HTMLDivElement> & {
  active?: boolean
  payload?: ChartTooltipItem[]
  label?: string
  hideLabel?: boolean
}

export function ChartTooltipContent({
  active,
  payload,
  label,
  hideLabel = false,
  className,
  ...props
}: ChartTooltipContentProps) {
  if (!active || !payload?.length) {
    return null
  }

  return (
    <div
      className={cn('rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md', className)}
      {...props}
    >
      {!hideLabel && label ? <p className="mb-1 font-semibold text-slate-900">{label}</p> : null}
      <div className="space-y-1">
        {payload.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            {item.color ? <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} /> : null}
            <span className="font-medium text-slate-700">
              {item.name}: {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
