"use client"

import { useState, useMemo } from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
// Simple badge element to avoid extra deps
function Chip({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <span
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs border border-neutral-300 bg-neutral-100 text-neutral-900 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100 cursor-pointer"
    >
      {children}
    </span>
  )
}
import { Select } from "./ui/select"

type Project = { id: string; name: string }
type Subproject = { id: string; name: string }

export interface RunsFilterProps {
  projects: Project[]
  projectId: string
  setProjectId: (v: string) => void
  subprojects: Subproject[]
  subprojectId: string
  setSubprojectId: (v: string) => void
  engines: string[]
  engineFilter: string
  setEngineFilter: (v: string) => void
  statusFilter: string
  setStatusFilter: (v: string) => void
  dateFrom: string
  setDateFrom: (v: string) => void
  dateTo: string
  setDateTo: (v: string) => void
  query: string
  setQuery: (v: string) => void
  onSearch: () => void
  onRefresh: () => void
  isLoading?: boolean
  totalResults?: number
}

export default function RunsFilter(props: RunsFilterProps) {
  const [open, setOpen] = useState<boolean>(false)
  const projectName = props.projects.find(p => p.id === props.projectId)?.name
  const themeName = props.subprojects.find(s => s.id === props.subprojectId)?.name

  const fmtChipDate = (s: string) => {
    if (!s) return ''
    try { const d = new Date(s); return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}` } catch { return s }
  }

  const chips = useMemo(() => {
    const list: Array<{ key: string; label: string; onClear: () => void }> = []
    if (projectName) list.push({ key: 'project', label: `Projeto: ${projectName}`, onClear: () => {} })
    if (themeName) list.push({ key: 'theme', label: `Tema: ${themeName}`, onClear: () => props.setSubprojectId('') })
    if (props.engineFilter) list.push({ key: 'engine', label: `Engine: ${props.engineFilter}`, onClear: () => props.setEngineFilter('') })
    if (props.statusFilter) list.push({ key: 'status', label: `Status: ${props.statusFilter}`, onClear: () => props.setStatusFilter('') })
    if (props.dateFrom) list.push({ key: 'from', label: `De: ${fmtChipDate(props.dateFrom)}`, onClear: () => props.setDateFrom('') })
    if (props.dateTo) list.push({ key: 'to', label: `Até: ${fmtChipDate(props.dateTo)}`, onClear: () => props.setDateTo('') })
    if (props.query) list.push({ key: 'q', label: `ID: ${props.query}`, onClear: () => props.setQuery('') })
    return list
  }, [projectName, themeName, props.engineFilter, props.statusFilter, props.dateFrom, props.dateTo, props.query])

  const setQuickRange = (range: 'today' | 7 | 30 | 'all') => {
    if (range === 'all') { props.setDateFrom(''); props.setDateTo(''); return }
    const now = new Date()
    const end = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()))
    const start = new Date(end)
    if (range !== 'today') start.setUTCDate(start.getUTCDate() - (range as number))
    const fmt = (d: Date) => `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`
    props.setDateFrom(fmt(start))
    props.setDateTo(fmt(end))
  }

  const resetAll = () => {
    props.setSubprojectId('')
    props.setEngineFilter('')
    props.setStatusFilter('')
    props.setDateFrom('')
    props.setDateTo('')
    props.setQuery('')
  }

  return (
    <div className="border rounded-md">
      <div className="p-3 flex flex-wrap items-center gap-3">
        <div className="text-sm font-semibold">Filtros</div>
        <div className="flex flex-wrap gap-1">
          {chips.length ? chips.map(ch => (
            <Chip key={ch.key} onClick={ch.onClear}>{ch.label} ×</Chip>
          )) : <span className="text-xs opacity-60">Nenhum filtro ativo</span>}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2 text-xs">
          <Button variant="outline" size="sm" onClick={() => setQuickRange('today')}>Hoje</Button>
          <Button variant="outline" size="sm" onClick={() => setQuickRange(7)}>7d</Button>
          <Button variant="outline" size="sm" onClick={() => setQuickRange(30)}>30d</Button>
          <Button variant="outline" size="sm" onClick={() => setQuickRange('all')}>Tudo</Button>
          <Button variant="outline" size="sm" onClick={resetAll}>Limpar</Button>
          <Button variant="outline" size="sm" onClick={props.onRefresh}>Atualizar</Button>
          <Button variant="outline" size="sm" onClick={() => setOpen(v=>!v)}>{open ? 'Ocultar' : 'Mostrar'}</Button>
        </div>
      </div>
      {open && (
        <div className="p-3 grid gap-3 items-start" style={{ gridTemplateColumns: 'repeat(12, minmax(0, 1fr))' }}>
          <label className="col-span-12 sm:col-span-3 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
            Projeto
            <Select value={props.projectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setProjectId(e.target.value)} className="mt-1">
            {props.projects.map((p: Project) => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
            </Select>
          </label>
          <label className="col-span-12 sm:col-span-3 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
            Tema
            <Select value={props.subprojectId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setSubprojectId(e.target.value)} className="mt-1">
              <option value="">Todos os temas</option>
              {props.subprojects.map((sp: Subproject) => <option key={sp.id} value={sp.id}>{sp.name}</option>)}
            </Select>
          </label>
          <label className="col-span-6 sm:col-span-2 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
            Engine
            <Select value={props.engineFilter} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setEngineFilter(e.target.value)} className="mt-1">
              <option value="">Todas as engines</option>
              {props.engines.map((e: string) => <option key={e} value={e}>{e}</option>)}
            </Select>
          </label>
          <label className="col-span-6 sm:col-span-2 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
            Status
            <Select value={props.statusFilter} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => props.setStatusFilter(e.target.value)} className="mt-1">
              <option value="">Todos os status</option>
              {['queued','running','completed','failed'].map((s: string) => <option key={s} value={s}>{s}</option>)}
            </Select>
          </label>
          <label className="col-span-12 sm:col-span-2 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
            Período
            <div className="mt-1 flex items-center gap-2">
              <Input type="date" value={props.dateFrom} onChange={(e: React.ChangeEvent<HTMLInputElement>) => props.setDateFrom(e.target.value)} />
              <Input type="date" value={props.dateTo} onChange={(e: React.ChangeEvent<HTMLInputElement>) => props.setDateTo(e.target.value)} />
            </div>
          </label>
          <label className="col-span-12 sm:col-span-4 text-xs font-semibold text-neutral-700 dark:text-neutral-300">
            Buscar
            <div className="mt-1 flex items-center gap-2">
              <Input placeholder="Buscar por ID" value={props.query} onChange={(e: React.ChangeEvent<HTMLInputElement>) => props.setQuery(e.target.value)} onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => { if (e.key === 'Enter') props.onSearch() }} />
              <Button variant="secondary" size="sm" onClick={props.onSearch}>Buscar</Button>
            </div>
          </label>
        </div>
      )}
    </div>
  )
}
