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
export type Monitor = { id: string; name: string; subproject_id?: string; schedule_cron?: string | null; engines_json?: any; active: boolean }

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
  // monitor/schedule
  monitor_id?: string
  monitor_name?: string
  schedule_date?: string
  schedule_slot?: string
  schedule_index_today?: number
  schedule_total_today?: number
  schedule_source?: string
  // Classificação Zero-Click
  response_type?: string
  sufficiency_level?: string
  actionability_type?: string
  trust_source?: string
  brand_positioning?: string
  classification_confidence?: number
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
  cycle_delay_seconds?: number
  // monitor/schedule
  monitor_id?: string
  schedule_date?: string
  // Classificação Zero-Click
  response_type?: string
  sufficiency_level?: string
  actionability_type?: string
  trust_source?: string
  brand_positioning?: string
  classification_confidence?: number
  classified_at?: string
  classification_version?: string
  schedule_slot?: string
  schedule_index_today?: number
  schedule_total_today?: number
  schedule_source?: 'manual'|'monitor'|'monitor_now'
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

// ---------- Monitors ----------
export const getMonitors = (projectId: string) => http.get<Monitor[]>(`/projects/${projectId}/monitors`).then(r => r.data)
export const stopMonitor = (monitorId: string) => http.post(`/monitors/${monitorId}/stop`, {}).then(r => r.data)
export const monitorStats = (monitorId: string, days = 7) => http.get<{ since: string; totals: { total: number; completed: number; failed: number }; by_day: Array<{ date: string; total: number; completed: number; failed: number }> }>(`/monitors/${monitorId}/stats`, { params: { days } }).then(r => r.data)
export const deleteMonitorRuns = (monitorId: string) => http.delete<{ deleted: number }>(`/monitors/${monitorId}/runs`).then(r => r.data)

// ---------- Runs ----------
export type ListRunsParams = Partial<{
  project_id: string
  subproject_id: string
  engine: string
  status: string
  schedule_source: 'manual'|'monitor'|'monitor_now'
  monitor_id: string
  date_from: string // ISO with T00:00:00
  date_to: string   // ISO with T23:59:59
  page: number
  page_size: number
  order_by: string
  order_dir: 'asc'|'desc'
  has_text: boolean
}>

export const listRuns = (params: ListRunsParams) => http.get<RunListItem[]>('/runs', { params }).then(r => r.data)
export const createRun = (payload: CreateRunPayload) => http.post('/runs', payload).then(r => r.data)
export const getRun = (id: string) => http.get<RunDetail>(`/runs/${id}`).then(r => r.data)
export const getRunReport = (id: string) => http.get<Report>(`/runs/${id}/report`).then(r => r.data)
export const getRunEvidences = (id: string) => http.get<Evidence[]>(`/runs/${id}/evidences`).then(r => r.data)
export const getRunEvents = (id: string) => http.get<EventItem[]>(`/runs/${id}/events`).then(r => r.data)
export const countRuns = (params: ListRunsParams) => http.get<{ count: number }>(`/runs/count`, { params }).then(r => r.data)

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

// ---------- Sandbox ----------
export type SandboxRequest = {
  engine: 'openai' | 'gemini' | 'perplexity' | 'google_serp' | 'sandbox'
  prompt: string
  model?: string
  config?: Record<string, any>
  language?: string
  region?: string
  device?: string
  timeout_seconds?: number
}

export type SandboxResponse = {
  ok: boolean
  engine: string
  model?: string
  timing_ms?: number
  text_preview?: string
  text?: string
  truncated?: boolean
  links?: Array<{ url: string; title?: string }>
  web_search_used?: boolean
  web_search_calls?: number
  raw_keys?: string[]
  output_types?: string[]
  error?: string
  request?: any
}

export const sandboxTest = (payload: SandboxRequest) =>
  http.post<SandboxResponse>('/sandbox/test', payload).then(r => r.data)

export type OpenAIModelsResponse = {
  ok: boolean
  ids?: string[]
  count?: number
  error?: string
  organization?: string
  project?: string
}

export const listOpenAIModels = (params: { org?: string; project?: string }) =>
  http.get<OpenAIModelsResponse>('/sandbox/openai/models', { params }).then(r => r.data)

// ---------- Classification (Zero-Click) ----------
export type ClassificationResult = {
  response_type: string
  sufficiency_level: string
  actionability_type: string
  trust_source: string
  brand_positioning: string
  confidence: number
  reasoning: Record<string, string>
}

export type ClassificationResponse = {
  run_id: string
  classification: ClassificationResult
  classified_at: string
  version: string
}

export type ClassificationStats = {
  project_id: string
  overview: {
    total_runs: number
    classified_runs: number
    unclassified_runs: number
    classification_coverage: number
    avg_confidence: number
  }
  response_types: Record<string, number>
  brand_positioning: Record<string, number>
  sufficiency_levels: Record<string, number>
}

export type BatchClassificationResult = {
  project_id: string
  total_processed: number
  successful: number
  failed: number
  force_update: boolean
  limit: number
  processed_at: string
}

export const classifyRun = (runId: string) =>
  http.post<ClassificationResponse>(`/runs/${runId}/classify`).then(r => r.data)

export const batchClassifyProject = (projectId: string, forceUpdate = false, limit = 1000) =>
  http.post<BatchClassificationResult>(`/projects/${projectId}/classify/batch`, null, {
    params: { force_update: forceUpdate, limit }
  }).then(r => r.data)

export const getClassificationStats = (projectId: string) =>
  http.get<ClassificationStats>(`/projects/${projectId}/classification/stats`).then(r => r.data)

export const getUnprocessedRuns = (projectId?: string, limit = 100) =>
  http.get<{ unclassified_runs: string[]; count: number; project_id?: string; limit: number }>(`/classification/unprocessed`, {
    params: { project_id: projectId, limit }
  }).then(r => r.data)

// ---------- Gemini-Powered Classification ----------
export type GeminiClassificationResponse = {
  run_id: string
  classification: ClassificationResult
  advanced_metrics: {
    user_intent: string
    satisfaction_score: number
    competitive_mentions: number
    financial_value_score: number
    content_gap_detected: boolean
    conversion_potential: string
  }
  ai_insights: {
    strategic_insights: string[]
    optimization_suggestions: string[]
    reasoning: Record<string, string>
  }
  classified_at: string
  version: string
}

export type GeminiBatchResult = {
  project_id: string
  processing_summary: {
    total_processed: number
    successful: number
    failed: number
    success_rate: number
    limit: number
  }
  aggregated_insights: {
    strategic_insights: string[]
    optimization_suggestions: string[]
  }
  processed_at: string
  version: string
}

export type GeminiInsights = {
  analysis_period: string
  summary: {
    total_runs_analyzed: number
    high_value_opportunities: number
    content_gaps_detected: number
    high_satisfaction_responses: number
    gap_percentage: number
  }
  intent_distribution: Record<string, number>
  brand_positioning: Record<string, number>
  priority_opportunities: Array<{
    run_id: string
    prompt_preview?: string
    competitive_mentions: number
    financial_value: number
    user_intent: string
    date: string
  }>
  strategic_insights: string[]
  recommendations: string[]
}

export type GeminiStatus = {
  project_id: string
  classification_status: {
    total_completed_runs: number
    gemini_classified: number
    basic_classified: number
    unclassified: number
    gemini_coverage: number
    gemini_avg_confidence: number
  }
  recommendations: {
    should_upgrade_to_gemini: boolean
    needs_initial_classification: boolean
    upgrade_candidates: number
    new_classification_needed: number
  }
}

export const classifyRunWithGemini = (runId: string) =>
  http.post<GeminiClassificationResponse>(`/runs/${runId}/classify/gemini`).then(r => r.data)

export const batchClassifyWithGemini = (projectId: string, limit = 500) =>
  http.post<GeminiBatchResult>(`/projects/${projectId}/classify/gemini/batch`, null, {
    params: { limit }
  }).then(r => r.data)

export const getGeminiInsights = (projectId: string, days = 7) =>
  http.get<GeminiInsights>(`/projects/${projectId}/insights/gemini`, {
    params: { days }
  }).then(r => r.data)

export const getGeminiStatus = (projectId: string) =>
  http.get<GeminiStatus>(`/projects/${projectId}/classification/gemini-status`).then(r => r.data)

export const migrateToGemini = (projectId?: string, limit = 200) =>
  http.post<{
    migration_summary: {
      candidates_found: number
      processed: number
      successful_migrations: number
      migration_rate: number
    }
    project_id?: string
    limit: number
    completed_at: string
  }>(`/classification/migrate-to-gemini`, null, {
    params: { project_id: projectId, limit }
  }).then(r => r.data)
