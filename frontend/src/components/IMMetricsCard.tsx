import { Badge } from '../components/ui/badge'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Award,
  Brain,
  BarChart3,
  Sparkles
} from 'lucide-react'

// Simple Card components
const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`border border-neutral-200 dark:border-neutral-800 rounded-lg bg-white dark:bg-neutral-900 shadow-sm ${className}`}>
    {children}
  </div>
)

const CardHeader = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`p-4 pb-2 ${className}`}>{children}</div>
)

const CardTitle = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <h3 className={`font-semibold ${className}`}>{children}</h3>
)

const CardContent = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`p-4 pt-2 ${className}`}>{children}</div>
)

const Progress = ({ value, className = '' }: { value: number | null; className?: string }) => (
  <div className={`w-full bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden ${className}`}>
    <div 
      className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-300"
      style={{ width: `${Math.min(100, Math.max(0, value || 0))}%` }}
    />
  </div>
)

interface IMMetrics {
  im_seo_score: number | null
  im_seoia_score: number | null
  core_web_vitals: {
    score: number | null
    lcp: number | null
    fid: number | null
    cls: number | null
  }
  eeat: {
    overall: number | null
    expertise: number | null
    experience: number | null
    authoritativeness: number | null
    trustworthiness: number | null
  }
  irzc: {
    score: number | null
    ctr_expected: number | null
  }
  ia_ready: {
    score: number | null
    blocks_count: number | null
    has_lists: boolean
    has_faqs: boolean
    has_tables: boolean
    has_step_by_step: boolean
  }
  entities: {
    detected: number | null
    relevance_score: number | null
    connection_score: number | null
  }
  traffic: {
    share_of_voice: number | null
    serp_features_presence: number | null
  }
}

function getScoreColor(score: number | null): string {
  if (!score) return 'text-gray-400'
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  if (score >= 40) return 'text-orange-600'
  return 'text-red-600'
}

function getScoreBgColor(score: number | null): string {
  if (!score) return 'bg-gray-100'
  if (score >= 80) return 'bg-green-50'
  if (score >= 60) return 'bg-yellow-50'
  if (score >= 40) return 'bg-orange-50'
  return 'bg-red-50'
}

function getScoreLabel(score: number | null): string {
  if (!score) return 'N/A'
  if (score >= 80) return 'Excelente'
  if (score >= 60) return 'Bom'
  if (score >= 40) return 'Regular'
  return 'Ruim'
}

export function IMMetricsCard({ metrics }: { metrics: IMMetrics }) {
  const imSeoScore = metrics.im_seo_score ?? 0
  const imSeoiaScore = metrics.im_seoia_score ?? 0
  
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">

      {/* IM-SEO Score - Destaque Principal */}
      <Card className={`${getScoreBgColor(imSeoScore)} border-2`}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">IM-SEO</CardTitle>
          <Target className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2">
            <div className={`text-4xl font-bold ${getScoreColor(imSeoScore)}`}>
              {imSeoScore.toFixed(1)}
            </div>
            <span className="text-sm text-muted-foreground">/100</span>
          </div>
          <Progress value={imSeoScore} className="mt-3 h-2" />
          <div className="flex items-center justify-between mt-2">
            <Badge variant={imSeoScore >= 60 ? 'default' : 'destructive'} className="text-xs">
              {getScoreLabel(imSeoScore)}
            </Badge>
            <p className="text-xs text-muted-foreground">SEO Tradicional</p>
          </div>
        </CardContent>
      </Card>

      {/* IM-SEOIA Score - Destaque Principal */}
      <Card className={`${getScoreBgColor(imSeoiaScore)} border-2`}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">IM-SEOIA</CardTitle>
          <Zap className="h-5 w-5 text-purple-500" />
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2">
            <div className={`text-4xl font-bold ${getScoreColor(imSeoiaScore)}`}>
              {imSeoiaScore.toFixed(1)}
            </div>
            <span className="text-sm text-muted-foreground">/100</span>
          </div>
          <Progress value={imSeoiaScore} className="mt-3 h-2" />
          <div className="flex items-center justify-between mt-2">
            <Badge variant={imSeoiaScore >= 60 ? 'default' : 'destructive'} className="text-xs">
              {getScoreLabel(imSeoiaScore)}
            </Badge>
            <p className="text-xs text-muted-foreground">Otimização IA</p>
          </div>
        </CardContent>
      </Card>

      {/* IRZC - Risco Zero Click */}
      <Card className="border-2 border-orange-200">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">IRZC</CardTitle>
          <AlertTriangle className={`h-5 w-5 ${getScoreColor(100 - (metrics.irzc.score ?? 50))}`} />
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2">
            <div className={`text-3xl font-bold ${getScoreColor(100 - (metrics.irzc.score ?? 50))}`}>
              {(metrics.irzc.score ?? 0).toFixed(1)}
            </div>
            <span className="text-sm text-muted-foreground">/100</span>
          </div>
          <Progress 
            value={100 - (metrics.irzc.score ?? 50)} 
            className="mt-3 h-2" 
          />
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-muted-foreground">
              Risco Zero-Click {(metrics.irzc.score ?? 0) > 70 ? '(Alto)' : (metrics.irzc.score ?? 0) > 40 ? '(Médio)' : '(Baixo)'}
            </p>
            <Badge variant="outline" className="text-xs">
              CTR: {(metrics.irzc.ctr_expected ?? 0).toFixed(1)}%
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Core Web Vitals */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Performance (CWV)</CardTitle>
          <Activity className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2 mb-3">
            <div className={`text-2xl font-bold ${getScoreColor(metrics.core_web_vitals.score)}`}>
              {(metrics.core_web_vitals.score ?? 0).toFixed(0)}
            </div>
            <span className="text-xs text-muted-foreground">/100</span>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">LCP</span>
              <Badge variant={(metrics.core_web_vitals.lcp ?? 0) <= 2.5 ? 'default' : 'destructive'} className="text-xs">
                {(metrics.core_web_vitals.lcp ?? 0).toFixed(2)}s
              </Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">FID</span>
              <Badge variant={(metrics.core_web_vitals.fid ?? 0) <= 100 ? 'default' : 'destructive'} className="text-xs">
                {(metrics.core_web_vitals.fid ?? 0).toFixed(0)}ms
              </Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">CLS</span>
              <Badge variant={(metrics.core_web_vitals.cls ?? 0) <= 0.1 ? 'default' : 'destructive'} className="text-xs">
                {(metrics.core_web_vitals.cls ?? 0).toFixed(3)}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* E-E-A-T */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">E-E-A-T</CardTitle>
          <Award className="h-4 w-4 text-amber-500" />
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2 mb-3">
            <div className={`text-2xl font-bold ${getScoreColor(metrics.eeat.overall)}`}>
              {(metrics.eeat.overall ?? 0).toFixed(1)}
            </div>
            <span className="text-xs text-muted-foreground">/100</span>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Expertise</span>
              <span className="font-medium">{(metrics.eeat.expertise ?? 0).toFixed(0)}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Experience</span>
              <span className="font-medium">{(metrics.eeat.experience ?? 0).toFixed(0)}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Authority</span>
              <span className="font-medium">{(metrics.eeat.authoritativeness ?? 0).toFixed(0)}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Trust</span>
              <span className="font-medium">{(metrics.eeat.trustworthiness ?? 0).toFixed(0)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* IA-Ready Blocks */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">IA-Ready Blocks</CardTitle>
          <Sparkles className="h-4 w-4 text-purple-500" />
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2 mb-3">
            <div className={`text-2xl font-bold ${getScoreColor(metrics.ia_ready.score)}`}>
              {(metrics.ia_ready.score ?? 0).toFixed(0)}
            </div>
            <span className="text-xs text-muted-foreground">/100</span>
          </div>
          <p className="text-xs text-muted-foreground mb-2">
            {metrics.ia_ready.blocks_count ?? 0} blocos detectados
          </p>
          <div className="flex flex-wrap gap-1">
            {metrics.ia_ready.has_lists && (
              <Badge variant="outline" className="text-xs">✓ Listas</Badge>
            )}
            {metrics.ia_ready.has_faqs && (
              <Badge variant="outline" className="text-xs">✓ FAQs</Badge>
            )}
            {metrics.ia_ready.has_tables && (
              <Badge variant="outline" className="text-xs">✓ Tabelas</Badge>
            )}
            {metrics.ia_ready.has_step_by_step && (
              <Badge variant="outline" className="text-xs">✓ Passo-a-passo</Badge>
            )}
            {!metrics.ia_ready.has_lists && !metrics.ia_ready.has_faqs && 
             !metrics.ia_ready.has_tables && !metrics.ia_ready.has_step_by_step && (
              <span className="text-xs text-muted-foreground">Nenhum bloco detectado</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Entidades */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Entidades</CardTitle>
          <Brain className="h-4 w-4 text-indigo-500" />
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2 mb-3">
            <div className="text-2xl font-bold text-indigo-600">
              {metrics.entities.detected ?? 0}
            </div>
            <span className="text-xs text-muted-foreground">detectadas</span>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Relevância</span>
              <span className="font-medium">{((metrics.entities.relevance_score ?? 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Conexão</span>
              <Badge variant="outline" className="text-xs">
                {(metrics.entities.connection_score ?? 0).toFixed(0)}/100
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tráfego SERP */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tráfego SERP</CardTitle>
          <BarChart3 className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Share of Voice</span>
                <span className="text-sm font-medium">{(metrics.traffic.share_of_voice ?? 0).toFixed(1)}%</span>
              </div>
              <Progress value={metrics.traffic.share_of_voice ?? 0} className="h-2" />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">SERP Features</span>
                <span className="text-sm font-medium">{(metrics.traffic.serp_features_presence ?? 0).toFixed(1)}%</span>
              </div>
              <Progress value={metrics.traffic.serp_features_presence ?? 0} className="h-2" />
            </div>
          </div>
        </CardContent>
      </Card>

    </div>
  )
}
