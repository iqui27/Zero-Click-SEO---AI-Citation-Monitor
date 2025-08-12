import * as React from 'react'
import { cn } from '../../lib/utils'

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(({ className, children, ...props }, ref) => (
  <div className="relative w-full">
    <select
      ref={ref}
      className={cn(
        'h-9 w-full appearance-none rounded-md border border-neutral-300 bg-white pl-3 pr-9 text-sm text-neutral-900 placeholder:text-neutral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 disabled:cursor-not-allowed disabled:opacity-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100 dark:placeholder:text-neutral-500 dark:focus-visible:ring-neutral-600',
        className
      )}
      {...props}
    >
      {children}
    </select>
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 opacity-60"
    >
      <path d="M7 10l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  </div>
))
Select.displayName = 'Select'

// shadcn-like API adapters (minimal) to support RunsFilter mock component
export function SelectTrigger({ className, children }: { className?: string; children?: React.ReactNode }) {
  return <div className={cn('h-10 w-full rounded-md border border-neutral-300 dark:border-neutral-700 px-3 py-2 text-sm flex items-center justify-between', className)}>{children}</div>
}
export function SelectValue({ placeholder }: { placeholder?: string }) {
  return <span className="opacity-60 text-sm">{placeholder || ''}</span>
}
export function SelectContent({ children }: { children?: React.ReactNode }) {
  return <div className="mt-1 border border-neutral-300 dark:border-neutral-700 rounded-md p-1 bg-white dark:bg-neutral-900 shadow-sm">{children}</div>
}
export function SelectItem({ value, children, onClick }: { value: string; children?: React.ReactNode; onClick?: () => void }) {
  return (
    <div className="px-2 py-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer" onClick={onClick} data-value={value}>
      {children}
    </div>
  )
}
