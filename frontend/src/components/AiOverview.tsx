// @ts-nocheck
import * as React from 'react'

type RefItem = { title?: string; link?: string; url?: string; snippet?: string }
type Organic = { title?: string; link?: string; displayed_link?: string; snippet?: string }

export function AiOverview({
  source,
  ai,
  organics,
}: {
  source?: string
  ai?: { text_blocks?: any[]; references?: RefItem[] } | null
  organics?: Organic[] | null
}) {
  const hasAi = !!(source && source.startsWith('serpapi_ai'))
  const blocks = ai?.text_blocks || []
  const refs = ai?.references || []

  return (
    <section className="space-y-2">
      <h2 className="text-lg font-medium">AI Overview</h2>
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
        {!hasAi && (
          <div className="px-3 py-2 text-xs border-b border-neutral-200 dark:border-neutral-800 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300">
            AI Overview não está disponível para esta consulta. Exibindo resultados orgânicos.
          </div>
        )}

        <div className="p-3 grid gap-3">
          {hasAi ? (
            <div className="grid gap-2">
              {renderBlocks(blocks)}
              {!!refs.length && (
                <div className="pt-2 border-t border-neutral-200 dark:border-neutral-800">
                  <div className="text-xs font-medium opacity-70 mb-1">Referências</div>
                  <ul className="grid gap-1">
                    {refs.slice(0, 20).map((r, i) => (
                      <li key={i} className="text-sm truncate">
                        <a className="text-blue-600 hover:underline" href={r.link || r.url} target="_blank" rel="noreferrer">
                          {r.title || r.link || r.url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="grid gap-2">
              <div className="text-sm opacity-70">Resultados orgânicos</div>
              <ul className="grid gap-1">
                {(organics || []).slice(0, 10).map((o, i) => (
                  <li key={i} className="text-sm">
                    <a className="text-blue-600 hover:underline" href={o.link} target="_blank" rel="noreferrer">
                      {o.title || o.link}
                    </a>
                    {o.displayed_link && (
                      <span className="ml-2 text-xs opacity-60">{o.displayed_link}</span>
                    )}
                    {o.snippet && (
                      <div className="text-xs opacity-70 truncate">{o.snippet}</div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function renderBlocks(list: any[]): React.ReactNode {
  if (!Array.isArray(list) || !list.length) return null
  return list.map((b, idx) => (
    <div key={idx} className="grid gap-1">
      {b.type === 'heading' && (
        <h3 className="text-base font-semibold leading-snug">{b.snippet}</h3>
      )}
      {b.type === 'paragraph' && (
        <p className="text-sm leading-relaxed opacity-90">{b.snippet}</p>
      )}
      {b.type === 'list' && (
        <div className="grid gap-1">
          {Array.isArray(b.list) && (
            <ul className="list-disc ml-5 space-y-1">
              {b.list.map((li: any, i: number) => (
                <li key={i} className="text-sm">
                  <span className="font-medium">{li.title}</span>
                  {li.snippet && <span className="opacity-90"> {li.snippet}</span>}
                  {Array.isArray(li.list) && (
                    <ul className="list-[circle] ml-5 space-y-1 mt-1">
                      {li.list.map((sub: any, j: number) => (
                        <li key={j} className="text-sm opacity-90">{sub.snippet}</li>
                      ))}
                    </ul>
                  )}
                  {Array.isArray(li.text_blocks) && (
                    <div className="ml-2 mt-1 grid gap-1">{renderBlocks(li.text_blocks)}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {b.type === 'expandable' && (
        <details className="rounded-md border border-neutral-200 dark:border-neutral-800">
          <summary className="px-2 py-1 cursor-pointer text-sm font-medium">{b.title || 'Detalhes'}</summary>
          <div className="p-2 grid gap-1">{renderBlocks(b.text_blocks || [])}</div>
        </details>
      )}
      {b.type === 'comparison' && Array.isArray(b.comparison) && (
        <div className="overflow-auto">
          <table className="min-w-[480px] text-sm border border-neutral-200 dark:border-neutral-800 rounded-md">
            <thead>
              <tr>
                <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-800">Recurso</th>
                {(b.product_labels || []).map((pl: string, i: number) => (
                  <th key={i} className="text-left p-2 border-b border-neutral-200 dark:border-neutral-800">{pl}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {b.comparison.map((row: any, i: number) => (
                <tr key={i} className="border-t border-neutral-200 dark:border-neutral-800">
                  <td className="p-2 font-medium">{row.feature}</td>
                  {(row.values || []).map((v: any, j: number) => (
                    <td key={j} className="p-2">{String(v)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {Array.isArray(b.text_blocks) && b.type !== 'expandable' && (
        <div className="grid gap-1">{renderBlocks(b.text_blocks)}</div>
      )}
    </div>
  ))
}


