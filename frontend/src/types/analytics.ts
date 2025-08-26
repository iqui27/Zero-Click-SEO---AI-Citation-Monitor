// Shared analytics-related types used across the frontend

export interface OverviewAnalytics {
  total_runs: number
  amr_avg: number
  dcr_avg: number
  zcrs_avg: number
}

export interface SeriesPoint {
  day: string
  // Some charts may only use zcrs_avg, but AMR/DCR can also be present
  amr_avg?: number
  dcr_avg?: number
  zcrs_avg: number
}

export interface TopDomain {
  domain: string
  count: number
}

export interface PerfByEngine {
  engine: string
  amr_avg: number
  dcr_avg: number
  zcrs_avg: number
  runs?: number
}

export interface CostsSeriesPoint {
  day: string
  engine: string
  cost_usd: number
  tokens: number
}

export interface CostsResponse {
  total_cost_usd: number
  total_tokens: number
  runs: number
  avg_cost_per_run: number
  series?: CostsSeriesPoint[]
}

// Runs (list item shape used in multiple screens)
export interface RunItem {
  id: string
  engine: string
  status: string
  started_at?: string
  finished_at?: string
  zcrs?: number
  amr_flag?: boolean
  dcr_flag?: boolean
  template_name?: string
  subproject_name?: string
  cost_usd?: number
  tokens_total?: number
}

// Grouped comparison interfaces (mirror backend schemas)
export interface EvidenceOut { id: string; run_id: string; parsed_json: any }

export interface GroupedRunWithEvidences {
  id: string
  engine: string
  status: string
  started_at?: string
  finished_at?: string
  prompt_text?: string
  evidences: EvidenceOut[]
}

export interface RunsBySubprojectGroup {
  subproject_id?: string
  subproject_name: string
  runs: GroupedRunWithEvidences[]
}
