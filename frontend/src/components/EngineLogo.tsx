import * as React from 'react'

type EngineName = 'openai' | 'gemini' | 'perplexity' | 'google_serp' | string

function asset(path: string) {
  try {
    // Vite will transform to a URL
    return new URL(path, import.meta.url).href
  } catch {
    return ''
  }
}

export function EngineLogo({ name, className = 'h-5 w-5' }: { name: EngineName; className?: string }) {
  const key = (name || '').toLowerCase()
  let src = ''
  if (key.startsWith('openai')) src = asset('../assets/engines/openai.svg')
  else if (key.startsWith('gemini') || key.startsWith('google_gemini')) src = asset('../assets/engines/gemini.svg')
  else if (key.startsWith('perplexity')) src = asset('../assets/engines/perplexity.svg')
  else if (key.startsWith('google_serp') || key.startsWith('serp')) src = asset('../assets/engines/google-serp.svg')

  if (src) {
    return <img src={src} alt={name} className={className} />
  }

  // Fallback: colored initial
  const initial = (name || '?').charAt(0).toUpperCase()
  return (
    <span className={`inline-flex items-center justify-center rounded ${className}`} style={{ background: '#eee', color: '#111', fontSize: '0.7rem', fontWeight: 700 }}>
      {initial}
    </span>
  )
}


