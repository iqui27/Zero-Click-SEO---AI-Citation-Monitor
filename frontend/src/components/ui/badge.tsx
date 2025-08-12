import * as React from 'react'
import { cn } from '../../lib/utils'

type BadgeVariant = 'default' | 'secondary' | 'outline' | 'destructive'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const base = 'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs border'
  const styles: Record<BadgeVariant, string> = {
    default: 'border-neutral-300 bg-neutral-100 text-neutral-900 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100',
    secondary: 'border-neutral-300 bg-white text-neutral-700 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300',
    outline: 'border-neutral-300 bg-transparent text-neutral-700 dark:border-neutral-700 dark:text-neutral-300',
    destructive: 'border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200',
  }
  return <span className={cn(base, styles[variant], className)} {...props} />
}


