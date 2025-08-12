// @ts-nocheck
import * as React from 'react'

export default function KpiExplainer() {
  const [open, setOpen] = React.useState(false)
  return (
    <section className="relative">
      <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
        <div className="flex items-center gap-2 p-3">
          <div className="text-sm font-medium">Como medimos AMR, DCR e ZCRS?</div>
          <span className="ml-auto" />
          <button
            onClick={() => setOpen(v => !v)}
            className="text-xs px-2 py-1 rounded-md border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            aria-expanded={open}
          >{open ? 'Ocultar' : 'Ver explicação'}</button>
        </div>
        {open && (
          <div className="p-4 pt-0">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3 bg-neutral-50/60 dark:bg-neutral-900/40">
                <div className="text-xs opacity-70">AMR — Any Mention Rate</div>
                <div className="mt-1 text-sm leading-relaxed">
                  1.0 se houver ao menos uma citação cujo domínio pertença aos domínios do projeto; senão 0.0.
                </div>
                <div className="mt-2 text-[11px] opacity-70 font-mono">base: compute_amr(citations, our_domains)</div>
              </div>
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3 bg-neutral-50/60 dark:bg-neutral-900/40">
                <div className="text-xs opacity-70">DCR — Domain Click Rate</div>
                <div className="mt-1 text-sm leading-relaxed">
                  1.0 se houver ao menos uma citação “clicável” (type == 'link') cujo domínio pertença aos domínios do projeto; senão 0.0.
                </div>
                <div className="mt-2 text-[11px] opacity-70 font-mono">base: compute_dcr(citations, our_domains)</div>
              </div>
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3 bg-neutral-50/60 dark:bg-neutral-900/40">
                <div className="text-xs opacity-70">ZCRS — Zero‑Click Risk Score</div>
                <div className="mt-1 text-sm leading-relaxed">
                  Heurística de 0–100 (menor é pior) que penaliza links e menções totais.
                </div>
                <pre className="mt-2 text-[12px] p-2 rounded bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 overflow-auto">
score = 100 − (20 × links_useful + 10 × mentions + 5 × pos_weight)
                </pre>
                <ul className="mt-2 text-xs opacity-80 list-disc pl-5 space-y-0.5">
                  <li><span className="font-mono">links_useful</span>: número de citações com <span className="font-mono">type == 'link'</span></li>
                  <li><span className="font-mono">mentions</span>: total de citações</li>
                  <li><span className="font-mono">pos_weight</span>: 1.0 (constante por enquanto)</li>
                  <li>clamp entre 0 e 100 · base: <span className="font-mono">compute_zcrs</span></li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}


