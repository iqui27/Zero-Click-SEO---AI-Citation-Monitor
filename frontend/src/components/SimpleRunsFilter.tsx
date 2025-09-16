"use client"

import React from "react"
import { Select } from "./ui/select"
import { Button } from "./ui/button"

export type Subproject = { id: string; name: string }

export interface SimpleRunsFilterProps {
  subprojects: Subproject[]
  subprojectId: string
  setSubprojectId: (v: string) => void
  engines: string[]
  engineFilter: string
  setEngineFilter: (v: string) => void
  // new filters
  sources?: Array<'manual'|'monitor'|'monitor_now'>
  sourceFilter?: string
  setSourceFilter?: (v: string) => void
  monitors?: Array<{ id: string; name: string }>
  monitorFilter?: string
  setMonitorFilter?: (v: string) => void
  // extended filters
  statusFilter?: string
  setStatusFilter?: (v: string) => void
  viewMode?: 'cards'|'list'
  setViewMode?: (v: 'cards'|'list') => void
  onlyWithText?: boolean
  setOnlyWithText?: (v: boolean) => void
  dateFrom?: string
  setDateFrom?: (v: string) => void
  dateTo?: string
  setDateTo?: (v: string) => void
  onRefresh?: () => void
}

export default function SimpleRunsFilter(props: SimpleRunsFilterProps) {
  const reset = () => {
    props.setSubprojectId("")
    props.setEngineFilter("")
  }

  return (
    <div className="border rounded-md p-3 bg-white dark:bg-neutral-900">
      <div className="grid gap-3 sm:grid-cols-8 items-end">
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>Tema</span>
          <Select
            value={props.subprojectId}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setSubprojectId(e.target.value)}
          >
            <option value="">Todos os temas</option>
            {props.subprojects.map((sp) => (
              <option key={sp.id} value={sp.id}>
                {sp.name}
              </option>
            ))}
          </Select>
        </label>
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>Engine</span>
          <Select
            value={props.engineFilter}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setEngineFilter(e.target.value)}
          >
            <option value="">Todas as engines</option>
            {props.engines.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </Select>
        </label>
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>Fonte</span>
          <Select
            value={props.sourceFilter || ''}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setSourceFilter && props.setSourceFilter(e.target.value)}
          >
            <option value="">Todas</option>
            {(['manual','monitor','monitor_now'] as const).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
        </label>
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>Monitor</span>
          <Select
            value={props.monitorFilter || ''}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setMonitorFilter && props.setMonitorFilter(e.target.value)}
          >
            <option value="">Todos</option>
            {(props.monitors || []).map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </Select>
        </label>
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>Status</span>
          <Select
            value={props.statusFilter || ''}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setStatusFilter && props.setStatusFilter(e.target.value)}
          >
            <option value="">Todos</option>
            {(['queued','running','completed','failed'] as const).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
        </label>
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>Visualização</span>
          <Select
            value={props.viewMode || 'cards'}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setViewMode && props.setViewMode((e.target.value as 'cards'|'list'))}
          >
            <option value="cards">Cartões</option>
            <option value="list">Lista</option>
          </Select>
        </label>
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>De</span>
          <input
            type="date"
            value={props.dateFrom || ''}
            onChange={(e) => props.setDateFrom && props.setDateFrom(e.target.value)}
            className="border rounded-md px-2 py-1 bg-white dark:bg-neutral-900"
          />
        </label>
        <label className="grid gap-1 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
          <span>Até</span>
          <input
            type="date"
            value={props.dateTo || ''}
            onChange={(e) => props.setDateTo && props.setDateTo(e.target.value)}
            className="border rounded-md px-2 py-1 bg-white dark:bg-neutral-900"
          />
        </label>
      </div>
      <div className="mt-3 flex gap-3 items-center">
        <label className="inline-flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={!!props.onlyWithText}
            onChange={(e) => props.setOnlyWithText && props.setOnlyWithText(e.target.checked)}
          />
          Somente com texto (parsed)
        </label>
        <div className="flex gap-2 sm:ml-auto">
          <Button variant="outline" size="sm" onClick={reset}>
            Limpar
          </Button>
          {props.onRefresh && (
            <Button variant="outline" size="sm" onClick={props.onRefresh}>
              Atualizar
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
