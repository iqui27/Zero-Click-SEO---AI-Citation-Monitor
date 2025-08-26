import axios, { AxiosInstance } from 'axios'

// Base URL comes from Vite env, defaulting to '/api' (proxy to backend)
const API_BASE = (import.meta as any)?.env?.VITE_API_BASE || '/api'

export const http: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// ---------- Types (minimal) ----------
export type Project = { id: string; name: string }
export type Subproject = { id: string; name: string; description?: string }
export type Template = { id: string; category: string; name: string; text: string; intent?: string; persona?: string; subproject_id?: string }

export type RunListItem = {
  id: string
  engine: string
  status: string
  started_at?: string
  finished_at?: string
  zcrs?: number
  amr_flag?: boolean
  dcr_flag?: boolean
  template_name?: string
  template_category?: string
  subproject_name?: string
  cost_usd?: number
  tokens_total?: number
  cycles_total?: number
  cycle_delay_seconds?: number
}

export type EngineConfig = {
  name: string
  region?: string
  device?: string
  config_json?: Record<string, any>
}

export type CreateRunPayload = {
  project_id: string
  prompt_version_id: string
  engines: EngineConfig[]
  cycles?: number
  cycle_delay_seconds?: number | null
  subproject_id?: string | null
}

export type RunDetail = {
  id: string
  project_id: string
  prompt_version_id: string
  engine: { name: string; region?: string; device?: string; config_json?: any }
  status: string
  started_at?: string
  finished_at?: string
  subproject_id?: string
  prompt_text?: string
  model_name?: string
  tokens_input?: number
  tokens_output?: number
  tokens_total?: number
  cost_usd?: number
  latency_ms?: number
  cycles_total?: number
}

export type EventItem = { step: string; status: string; message?: string; created_at: string }
export type Evidence = { id: string; run_id: string; parsed_json: any }
export type Report = { id: string; amr: number; dcr: number; zcrs: number; citations: Array<{ domain: string; url?: string; anchor?: string; type?: string; is_ours: boolean }> }

// ---------- Projects ----------
export const getProjects = () => http.get<Project[]>('/projects').then(r => r.data)
export const createProject = (body: { name: string; country?: string; language?: string; timezone?: string }) => http.post('/projects', body).then(r => r.data)
export const getSubprojects = (projectId: string) => http.get<Subproject[]>(`/projects/${projectId}/subprojects`).then(r => r.data)

// ---------- Templates (used as simple prompts library) ----------
export const getTemplates = (projectId: string, category?: string, subproject_id?: string) =>
  http.get<Template[]>(`/projects/${projectId}/templates`, {
    params: {
      ...(category ? { category } : {}),
      ...(subproject_id ? { subproject_id } : {}),
    },
  }).then(r => r.data)
export const createTemplate = (projectId: string, body: { category: string; name: string; text: string; intent?: string; persona?: string; subproject_id?: string | null }) =>
  http.post(`/projects/${projectId}/templates`, body).then(r => r.data)
export const deleteTemplate = (templateId: string) => http.delete(`/templates/${templateId}`).then(r => r.data)

// ---------- Prompts & Versions ----------
export const createPrompt = (projectId: string, body: { name: string; text: string; intent?: string; persona?: string; variables?: Record<string, any> }) =>
  http.post(`/projects/${projectId}/prompts`, body).then(r => r.data)
export const getPromptVersions = (promptId: string) => http.get<Array<{ id: string }>>(`/prompts/${promptId}/versions`).then(r => r.data)

// ---------- Runs ----------
export type ListRunsParams = Partial<{
  project_id: string
  subproject_id: string
  engine: string
  status: string
  date_from: string // ISO with T00:00:00
  date_to: string   // ISO with T23:59:59
  page: number
  page_size: number
  order_by: string
  order_dir: 'asc'|'desc'
}>

export const listRuns = (params: ListRunsParams) => http.get<RunListItem[]>('/runs', { params }).then(r => r.data)
export const createRun = (payload: CreateRunPayload) => http.post('/runs', payload).then(r => r.data)
export const getRun = (id: string) => http.get<RunDetail>(`/runs/${id}`).then(r => r.data)
export const getRunReport = (id: string) => http.get<Report>(`/runs/${id}/report`).then(r => r.data)
export const getRunEvidences = (id: string) => http.get<Evidence[]>(`/runs/${id}/evidences`).then(r => r.data)
export const getRunEvents = (id: string) => http.get<EventItem[]>(`/runs/${id}/events`).then(r => r.data)

// ---------- Project & Subproject management ----------
export const updateProject = (
  id: string,
  body: Partial<{ name: string; country?: string; language?: string; timezone?: string }>
) => http.patch(`/projects/${id}`, body).then(r => r.data)

export const createSubproject = (
  projectId: string,
  body: { name: string; description?: string }
) => http.post(`/projects/${projectId}/subprojects`, body).then(r => r.data)

export const updateSubproject = (
  id: string,
  body: Partial<{ name: string; description?: string }>
) => http.patch(`/subprojects/${id}`, body).then(r => r.data)

// ---------- Deletes ----------
export const deleteProject = (id: string) => http.delete(`/projects/${id}`).then(r => r.data)
export const deleteSubproject = (id: string) => http.delete(`/subprojects/${id}`).then(r => r.data)
export const deleteRun = (id: string) => http.delete(`/runs/${id}`).then(r => r.data)

// ---------- Utils ----------
export const getUrlTitle = (url: string) => http.get<{ title: string }>(`/utils/url-title`, { params: { url } }).then(r => r.data)

// ---------- Streaming (SSE) helper ----------
export const openRunStream = (id: string) => new EventSource(`${API_BASE}/runs/${id}/stream`)
