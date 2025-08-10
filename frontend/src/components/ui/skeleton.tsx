import * as React from 'react'
import { cn } from '../../lib/utils'

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('animate-pulse rounded-md bg-neutral-200/60 dark:bg-neutral-800', className)} {...props} />
}

export { Skeleton }
