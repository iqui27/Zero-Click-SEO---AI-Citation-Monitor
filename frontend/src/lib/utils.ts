import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumberCompact(n?: number | null): string {
  if (n === null || n === undefined || isNaN(Number(n))) return '-'
  const abs = Math.abs(Number(n))
  if (abs >= 1_000_000) return `${(n as number / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `${(n as number / 1_000).toFixed(2)}K`
  return String(n)
}
