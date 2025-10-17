import { useEffect, useMemo, useState } from 'react'
import {
  getGeoStatsByFunnel,
  getGeoStatsByProduct,
  getGeoStatsByQuestionType,
  type GeoStatsByFunnelItem,
  type GeoStatsByProductItem,
  type GeoStatsByQuestionTypeItem,
  getGeoDashboard,
  startGeoDashboardComputation,
  getGeoDashboardStatus,
  type GeoDashboard,
  type GeoPositioning,
  type GeoPositioningTimelinePoint,
} from './api'

export type GeoOverviewKpi = {
  id: string
  label: string
  value: number | null
  delta?: number | null
  unit?: string
  deltaUnit?: 'percent' | 'points' | null
  trendDirection?: 'up' | 'down' | 'neutral' | null
  footerPrimary?: string | null
  footerSecondary?: string | null
}

export type GeoOverviewData = {
  kpis: GeoOverviewKpi[]
  shareOfVoice?: Record<string, number>
  timeline?: Array<{ date: string; engagement: number | null; conversionPotential: number | null }>
  brandTimeline?: Array<{ date: string; mentions: number; firstMentionAvg: number | null; densityAvg: number | null }>
  metrics?: {
    brandMentionDensityAvg?: number | null
    brandFirstMentionPositionAvg?: number | null
    conversationalTriggerAvg?: number | null
    engagementScoreAvg?: number | null
    conversionPotentialScoreAvg?: number | null
    topConversionPotential?: string | null
    competitorMentionRatioAvg?: number | null
    cocitationPercentage?: number | null
  }
}

export type GeoAggregations = {
  byProduct: GeoStatsByProductItem[]
  byFunnel: GeoStatsByFunnelItem[]
  byQuestionType: GeoStatsByQuestionTypeItem[]
}

export type GeoDashboardState = {
  loading: boolean
  error: string | null
  data: GeoDashboard | null
}

export type GeoDashboardFilters = {
  subproject_id?: string
  date_from?: string
  date_to?: string
  llm_model?: string
  prompt_category?: string
  prompt_text?: string
  prompt_id?: string
  brand_presence?: string
}

export function useGeoDashboard(projectId: string | undefined, filters?: GeoDashboardFilters) {
  const [state, setState] = useState<GeoDashboardState>({ loading: !!projectId, error: null, data: null })

  useEffect(() => {
    if (!projectId) {
      setState({ loading: false, error: null, data: null })
      return
    }

    let mounted = true
    setState((prev) => ({ ...prev, loading: true, error: null }))

    // Convert filter values to API format
    // Default to last 30 days if no date filter specified
    const defaultDateFrom = new Date()
    defaultDateFrom.setDate(defaultDateFrom.getDate() - 30)
    
    const apiFilters = {
      subproject_id: filters?.subproject_id !== 'all' ? filters?.subproject_id : undefined,
      date_from: filters?.date_from || defaultDateFrom.toISOString().split('T')[0],
      date_to: filters?.date_to,
      llm_model: filters?.llm_model !== 'all' ? filters?.llm_model : undefined,
      prompt_category: filters?.prompt_category !== 'all' ? filters?.prompt_category : undefined,
      prompt_text: filters?.prompt_text !== 'all' ? filters?.prompt_text : undefined,
      prompt_id: filters?.prompt_id !== 'all' ? filters?.prompt_id : undefined,
      brand_presence: filters?.brand_presence !== 'all' ? filters?.brand_presence : undefined,
    }

    // Carregar dados com retry para 202 (processando)
    const loadDashboard = async (retryCount = 0) => {
      try {
        const data = await getGeoDashboard(projectId, apiFilters)
        if (!mounted) return
        console.log('[GEO] Dashboard carregado (cache ou processado)')
        setState({ loading: false, error: null, data })
      } catch (err: any) {
        if (!mounted) return
        
        // Se 202 (processando), retry após 5 segundos
        if (err?.response?.status === 202 && retryCount < 30) {
          console.log(`[GEO] Dashboard processando... tentativa ${retryCount + 1}/30`)
          setTimeout(() => loadDashboard(retryCount + 1), 5000)
          return
        }
        
        console.error('[GEO] Erro ao carregar dashboard:', err)
        setState({ 
          loading: false, 
          error: err?.response?.status === 202 
            ? 'Timeout: processamento demorou mais de 2.5 minutos' 
            : err?.message || 'Erro ao carregar GEO dashboard', 
          data: null 
        })
      }
    }
    
    loadDashboard()

    return () => {
      mounted = false
    }
  }, [projectId, filters?.subproject_id, filters?.date_from, filters?.date_to, filters?.llm_model, filters?.prompt_category, filters?.prompt_text, filters?.prompt_id, filters?.brand_presence])

  const overview: GeoOverviewData | null = useMemo(() => {
    if (!state.data) return null

    const kpis: GeoOverviewKpi[] = (state.data.kpis || []).map((kpi, index) => {
      const rawValue = kpi.value
      let value: number | null
      if (typeof rawValue === 'number') {
        value = rawValue
      } else if (rawValue == null || rawValue === '') {
        value = null
      } else {
        const parsed = Number(rawValue)
        value = Number.isFinite(parsed) ? parsed : null
      }

      return {
        id: kpi.label || `kpi-${index}`,
        label: kpi.label,
        value,
        delta: kpi.delta ?? null,
        unit: kpi.unit,
        deltaUnit: kpi.delta_unit ?? null,
        trendDirection: kpi.trend_direction ?? null,
        footerPrimary: kpi.footer_primary ?? null,
        footerSecondary: kpi.footer_secondary ?? null,
      }
    })


    const positioning = state.data.positioning as GeoPositioning | undefined
    const shareOfVoice = positioning?.share_of_voice || undefined

    const timelineData = state.data.timeline || []
    const engagementTimeline = timelineData.map((point) => ({
      date: point.date,
      engagement: point.engagement_score_avg ?? 0,
      conversionPotential: point.conversion_potential_score_avg ?? 0,
    }))

    const brandTimeline = timelineData.map((point) => ({
      date: point.date,
      mentions: point.brand_mention_count ?? 0,
      firstMentionAvg: point.brand_first_mention_position_avg ?? null,
      densityAvg: point.brand_mention_density_avg ?? null,
    }))

    const summary = state.data.geo_summary || {}
    const metrics = {
      brandMentionDensityAvg: summary.brand_mention_density_avg ?? null,
      brandFirstMentionPositionAvg: summary.brand_first_mention_position_avg ?? null,
      conversationalTriggerAvg: summary.conversational_trigger_avg ?? null,
      engagementScoreAvg: summary.engagement_score_avg ?? null,
      conversionPotentialScoreAvg: summary.conversion_potential_score_avg ?? null,
      topConversionPotential: summary.top_conversion_potential ?? null,
      competitorMentionRatioAvg: summary.competitor_mention_ratio_avg ?? null,
      cocitationPercentage: summary.cocitation_percentage ?? null,
    }

    return { kpis, shareOfVoice, timeline: engagementTimeline, brandTimeline, metrics }
  }, [state.data])

  return {
    ...state,
    overview,
  }
}

export function useGeoAggregations(projectId: string | undefined, options: { days?: number } = {}) {
  const [loading, setLoading] = useState<boolean>(!!projectId)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<GeoAggregations | null>(null)
  const { days = 30 } = options

  useEffect(() => {
    if (!projectId) {
      setLoading(false)
      setError(null)
      setData(null)
      return
    }

    let mounted = true
    setLoading(true)
    setError(null)

    Promise.all([
      getGeoStatsByProduct(projectId, days),
      getGeoStatsByFunnel(projectId, days),
      getGeoStatsByQuestionType(projectId, days),
    ])
      .then(([product, funnel, question]) => {
        if (!mounted) return

        // Transform objects to arrays with category field included
        const productArray = Object.entries(product || {}).map(([key, value]) => ({
          ...value,
          product_category: key
        })) as GeoStatsByProductItem[]

        const funnelArray = Object.entries(funnel || {}).map(([key, value]) => ({
          ...value,
          funnel_stage: key
        })) as GeoStatsByFunnelItem[]

        const questionArray = Object.entries(question || {}).map(([key, value]) => ({
          ...value,
          question_type: key
        })) as GeoStatsByQuestionTypeItem[]

        setData({
          byProduct: productArray,
          byFunnel: funnelArray,
          byQuestionType: questionArray,
        })
        setLoading(false)
      })
      .catch((err: any) => {
        if (!mounted) return
        setError(err?.message || 'Erro ao carregar agregações GEO')
        setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [projectId, days])

  return { loading, error, data }
}
