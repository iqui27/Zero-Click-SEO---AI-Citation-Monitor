import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import {
  TrendingUp,
  Zap,
  Award,
  Shield,
  Activity,
  Target,
  Brain,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Info,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { Badge } from "../components/ui/badge";
import { MetricCard } from "../components/Dashboard/MetricCard";
import { Filters } from "../components/Dashboard/Filters";
import type { FilterState } from "../components/Dashboard/Filters";
import { ExportDialog } from "../components/Dashboard/ExportDialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Download } from "lucide-react";

interface MetricsBlock {
  average: number | null;
  min?: number | null;
  max?: number | null;
  ctr_real_avg?: number | null;
  ctr_expected_avg?: number | null;
  share_of_voice_avg?: number | null;
  serp_features_avg?: number | null;
  organic_position_avg?: number | null;
  blocks_avg?: number | null;
  has_lists_pct?: number | null;
  has_faqs_pct?: number | null;
  has_tables_pct?: number | null;
  expertise?: number | null;
  experience?: number | null;
  authoritativeness?: number | null;
  trustworthiness?: number | null;
  lcp?: number | null;
  fid?: number | null;
  cls?: number | null;
}

interface SemanticDistributionItem {
  category: string;
  count: number;
  percentage: number;
}

interface SemanticBrandItem {
  name: string;
  score: number;
  mentions: number;
}

interface SemanticKeywordItem {
  token: string;
  weight: number;
  mentions: number;
  brands: string[];
  competitors: string[];
}

interface SemanticSnapshot {
  perception_distribution: SemanticDistributionItem[];
  brand_ranking: SemanticBrandItem[];
  top_keywords: SemanticKeywordItem[];
  competitors: SemanticBrandItem[];
  runs_analyzed: number;
}

interface MultidimensionalData {
  dimensions: { label: string; value: number }[];
}

interface IndexComparisonSeries {
  label: string;
  value: number | null;
}

interface IndexComparisonData {
  series: IndexComparisonSeries[];
  delta: number | null;
}

type InsightSeverity = "high" | "medium" | "positive" | "info" | string;

interface InsightItem {
  title: string;
  description: string;
  severity: InsightSeverity;
}

interface AnalyticsOverview {
  total_runs: number;
  period_days: number;
  metrics: {
    im_seo: MetricsBlock;
    im_seoia: MetricsBlock;
    eeat: MetricsBlock;
    core_web_vitals: MetricsBlock;
    irzc: MetricsBlock;
    serp: MetricsBlock;
    ia_ready: MetricsBlock;
  };
  trends: {
    im_seo: number | null;
    im_seoia: number | null;
    eeat: number | null;
    irzc: number | null;
  };
  distribution: {
    im_seo: Record<string, number>;
  } | null;
  multidimensional: MultidimensionalData | null;
  index_comparison: IndexComparisonData | null;
  insights: InsightItem[];
  semantic: SemanticSnapshot;
}

interface TimeSeriesPoint {
  period: string;
  count: number;
  im_seo_score: number | null;
  im_seoia_score: number | null;
  eeat_score: number | null;
  core_web_vitals_score: number | null;
  irzc_score: number | null;
  share_of_voice_serp: number | null;
}

const formatValue = (value: number | null | undefined, digits = 1) =>
  value != null ? value.toFixed(digits) : "N/A";

const formatPercent = (value: number | null | undefined, digits = 1) =>
  value != null ? `${value.toFixed(digits)}%` : "–";

const severityConfig: Record<string, { icon: ReactNode; badge: string; tone: string }> = {
  high: {
    icon: <AlertTriangle className="w-4 h-4 text-red-600" />,
    badge: "Crítico",
    tone: "bg-red-50 border-red-200 text-red-700",
  },
  medium: {
    icon: <AlertTriangle className="w-4 h-4 text-orange-500" />,
    badge: "Atenção",
    tone: "bg-orange-50 border-orange-200 text-orange-700",
  },
  positive: {
    icon: <CheckCircle2 className="w-4 h-4 text-emerald-600" />,
    badge: "Oportunidade",
    tone: "bg-emerald-50 border-emerald-200 text-emerald-700",
  },
  info: {
    icon: <Info className="w-4 h-4 text-sky-600" />,
    badge: "Insight",
    tone: "bg-sky-50 border-sky-200 text-sky-700",
  },
  default: {
    icon: <Sparkles className="w-4 h-4 text-neutral-600" />,
    badge: "Insight",
    tone: "bg-neutral-50 border-neutral-200 text-neutral-700",
  },
};

const DEFAULT_SEMANTIC: SemanticSnapshot = {
  perception_distribution: [],
  brand_ranking: [],
  top_keywords: [],
  competitors: [],
  runs_analyzed: 0,
};

const perceptionLabels: Record<string, string> = {
  inovacao: 'Inovação & tecnologia',
  tradicao: 'Tradição & segurança',
  custo: 'Baixo custo',
  atendimento: 'Atendimento & relacionamento',
};

const formatPeriodLabel = (value: string) => {
  if (!value) return "";
  if (value.includes("W")) {
    return value.replace("-", " ");
  }
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return `${date.getDate().toString().padStart(2, "0")}/${(date.getMonth() + 1)
      .toString()
      .padStart(2, "0")}`;
  }
  return value;
};

export default function IMMetricsDashboard() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [timeseries, setTimeseries] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<FilterState>({ days: 30 });
  const [showExport, setShowExport] = useState(false);

  const handleFilterChange = useCallback((next: FilterState) => {
    setFilters((prev: FilterState) => {
      const prevString = JSON.stringify(prev);
      const nextString = JSON.stringify(next);
      return prevString === nextString ? prev : next;
    });
  }, []);

  useEffect(() => {
    void loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("days", filters.days.toString());
      if (filters.project_id) params.append("project_id", filters.project_id);
      if (filters.subproject_id) params.append("subproject_id", filters.subproject_id);
      if (filters.prompt_id) params.append("prompt_id", filters.prompt_id);
      if (filters.run_id) params.append("run_id", filters.run_id);
      if (filters.engine_ids?.length) params.append("engine_ids", filters.engine_ids.join(","));
      if (filters.start_date) params.append("start_date", filters.start_date);
      if (filters.end_date) params.append("end_date", filters.end_date);
      if (filters.im_seo_min != null) params.append("im_seo_min", filters.im_seo_min.toString());
      if (filters.im_seo_max != null) params.append("im_seo_max", filters.im_seo_max.toString());
      if (filters.im_seoia_min != null) params.append("im_seoia_min", filters.im_seoia_min.toString());
      if (filters.im_seoia_max != null) params.append("im_seoia_max", filters.im_seoia_max.toString());

      const [overviewRes, timeseriesRes] = await Promise.all([
        axios.get(`/api/analytics/im-overview?${params.toString()}`),
        axios.get(`/api/analytics/timeseries?${params.toString()}&granularity=day`),
      ]);

      const overviewData: AnalyticsOverview = {
        ...overviewRes.data,
        semantic: overviewRes.data?.semantic ?? DEFAULT_SEMANTIC,
      };

      setOverview(overviewData);
      setTimeseries(timeseriesRes.data?.data ?? []);
    } catch (error) {
      console.error("Failed to load IM metrics", error);
    } finally {
      setLoading(false);
    }
  };

  const metricsLoaded = Boolean(overview?.metrics);
  const hasTimeseries = timeseries.length > 0;

  const renderMetricCards = () => {
    if (!metricsLoaded || !overview) {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {Array.from({ length: 4 }).map((_, idx) => (
            <Card key={`metric-skeleton-${idx}`} className="h-32">
              <CardContent className="h-full flex flex-col justify-center space-y-3">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-4 w-20" />
              </CardContent>
            </Card>
          ))}
        </div>
      );
    }

    const { metrics, trends } = overview;

    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <MetricCard
          title="IM-SEO Médio"
          value={metrics.im_seo.average}
          min={metrics.im_seo.min ?? undefined}
          max={metrics.im_seo.max ?? undefined}
          trend={trends.im_seo ?? undefined}
          icon={TrendingUp}
          color="blue"
          subtitle="SEO tradicional"
        />
        <MetricCard
          title="IM-SEOIA Médio"
          value={metrics.im_seoia.average}
          min={metrics.im_seoia.min ?? undefined}
          max={metrics.im_seoia.max ?? undefined}
          trend={trends.im_seoia ?? undefined}
          icon={Zap}
          color="purple"
          subtitle="Preparação para IA"
        />
        <MetricCard
          title="E-E-A-T Médio"
          value={metrics.eeat.average}
          min={metrics.eeat.min ?? undefined}
          max={metrics.eeat.max ?? undefined}
          trend={trends.eeat ?? undefined}
          icon={Award}
          color="green"
          subtitle="Expertise & Trust"
        />
        <MetricCard
          title="IRZC Médio"
          value={metrics.irzc.average}
          min={metrics.irzc.min ?? undefined}
          max={metrics.irzc.max ?? undefined}
          trend={trends.irzc ?? undefined}
          icon={Shield}
          color="orange"
          subtitle="Risco zero-click"
        />
      </div>
    );
  };

  const renderSkeleton = () => <Skeleton className="h-72 w-full" />;

  const renderTimelineChart = (
    lines: { key: keyof TimeSeriesPoint; label: string; color: string }[]
  ) => {
    if (!hasTimeseries) {
      return renderSkeleton();
    }

    return (
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={timeseries}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" tick={{ fontSize: 12 }} tickFormatter={formatPeriodLabel} />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Legend />
          {lines.map((line) => (
            <Line
              key={line.key as string}
              type="monotone"
              dataKey={line.key}
              name={line.label}
              stroke={line.color}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  };

  const renderSemanticSection = () => {
    if (!overview) return null;

    const semantic = overview.semantic ?? DEFAULT_SEMANTIC;
    const topCategory = semantic.perception_distribution[0];
    const topLabel = topCategory ? (perceptionLabels[topCategory.category] ?? topCategory.category) : null;
    const maxKeywordWeight = Math.max(
      1,
      ...semantic.top_keywords.map((kw) => (kw.weight ?? 0) > 0 ? kw.weight : 0.5)
    );

    return (
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Posicionamento IA &amp; Palavras-chave</CardTitle>
            <p className="text-sm text-muted-foreground">
              Consolidado das entidades e tópicos extraídos pelo Gemini nos AI Overviews.
            </p>
          </div>
          <div className="flex flex-col items-end gap-2 text-right">
            {topLabel && <Badge variant="secondary" className="capitalize">{topLabel}</Badge>}
            <span className="text-xs text-muted-foreground">
              {semantic.runs_analyzed} runs com insights semânticos
            </span>
          </div>
        </CardHeader>
        <CardContent>
          {semantic.runs_analyzed === 0 ? (
            <div className="text-sm opacity-70 border rounded-lg p-6 text-center">
              Ainda não há dados semânticos processados para o recorte selecionado.
            </div>
          ) : (
            <div className="grid gap-4 md:gap-6 md:grid-cols-3">
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Percepção / Valor</h3>
                <ul className="space-y-2 text-sm">
                  {semantic.perception_distribution.length ? (
                    semantic.perception_distribution.map((item) => (
                      <li key={item.category} className="flex items-center justify-between gap-2">
                        <span className="capitalize">{perceptionLabels[item.category] ?? item.category}</span>
                        <span className="text-muted-foreground">{item.percentage.toFixed(1)}% · {item.count}</span>
                      </li>
                    ))
                  ) : (
                    <li className="opacity-70">Sem classificação.</li>
                  )}
                </ul>
              </div>
              <div className="space-y-3">
                <h3 className="text-sm font-medium">Marcas em destaque</h3>
                <div className="space-y-2">
                  {semantic.brand_ranking.length ? (
                    semantic.brand_ranking.slice(0, 6).map((brand, idx) => (
                      <div
                        key={brand.name}
                        className="flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                      >
                        <span className="font-medium truncate">{idx + 1}. {brand.name}</span>
                        <span className="text-xs text-muted-foreground">score {formatValue(brand.score, 2)}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm opacity-70 border rounded-lg p-4">Sem menções de marca relevantes.</div>
                  )}
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-medium mb-2">Palavras-chave</h3>
                  {semantic.top_keywords.length ? (
                    <div className="flex flex-wrap gap-2">
                      {semantic.top_keywords.slice(0, 14).map((kw) => {
                        const norm = Math.max(0.2, kw.weight / maxKeywordWeight);
                        const fontSize = 0.9 + norm * 1.2;
                        return (
                          <span
                            key={kw.token}
                            className="rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-100 px-2 py-1"
                            style={{ fontSize: `${fontSize}rem`, opacity: 0.6 + norm * 0.4 }}
                            title={`Marcas: ${kw.brands?.join(', ') || '—'}${kw.competitors?.length ? ` | Concorrentes: ${kw.competitors.join(', ')}` : ''}`}
                          >
                            {kw.token}
                          </span>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-sm opacity-70 border rounded-lg p-4">Sem palavras-chave mapeadas.</div>
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-medium mb-2">Concorrentes citados</h3>
                  {semantic.competitors.length ? (
                    <ul className="space-y-1 text-sm">
                      {semantic.competitors.slice(0, 6).map((competitor, idx) => (
                        <li key={competitor.name} className="flex items-center justify-between">
                          <span>{idx + 1}. {competitor.name}</span>
                          <span className="text-xs text-muted-foreground">menções {competitor.mentions}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-sm opacity-70 border rounded-lg p-4">Sem concorrentes relevantes.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6 pb-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Dashboard IM-SEO & IM-SEOIA</h1>
          <p className="text-muted-foreground">
            Monitoramento de maturidade SEO, preparação IA e risco zero-click.
          </p>
        </div>
        <Button variant="outline" size="lg" onClick={() => setShowExport((prev) => !prev)}>
          <Download className="w-4 h-4 mr-2" />
          Exportar Dados
        </Button>
      </div>

      <div className="bg-white rounded-xl border shadow-sm">
        <Filters onFilterChange={handleFilterChange} />
      </div>

      {showExport && (
        <Card>
          <CardHeader className="flex items-center justify-between">
            <CardTitle>Exportar dados das runs</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setShowExport(false)}>
              ✕
            </Button>
          </CardHeader>
          <CardContent>
            <ExportDialog filters={filters} totalRecords={overview?.total_runs || 0} />
          </CardContent>
        </Card>
      )}

      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 rounded-lg z-10">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-neutral-600" />
              Atualizando métricas...
            </div>
          </div>
        )}
        {renderMetricCards()}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 md:gap-6">
        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Panorama IM-SEOIA vs IM-SEO</CardTitle>
              <p className="text-sm text-muted-foreground">
                Diferencial competitivo frente ao índice tradicional.
              </p>
            </div>
            <Badge variant="secondary">Últimos {filters.days} dias</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Delta IM-SEOIA</p>
                <div className="flex items-center gap-2 text-3xl font-semibold">
                  {(() => {
                    const delta = overview?.index_comparison?.delta;
                    if (delta == null) return <span>–</span>;
                    const positive = delta > 0;
                    return (
                      <>
                        {positive ? (
                          <ArrowUpRight className="w-6 h-6 text-emerald-500" />
                        ) : (
                          <ArrowDownRight className="w-6 h-6 text-red-500" />
                        )}
                        <span className={positive ? "text-emerald-600" : "text-red-600"}>
                          {delta.toFixed(2)}
                        </span>
                      </>
                    );
                  })()}
                </div>
              </div>
              <div className="rounded-lg border border-dashed border-neutral-200 px-4 py-3 text-center">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Total de Runs</p>
                <div className="text-2xl font-semibold">{overview?.total_runs ?? "-"}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(overview?.index_comparison?.series ?? []).map((serie) => (
                <div
                  key={serie.label}
                  className="rounded-lg border border-neutral-200 p-4 flex items-center justify-between"
                >
                  <span className="text-sm text-muted-foreground">{serie.label}</span>
                  <span className="font-semibold text-base">
                    {serie.value != null ? serie.value.toFixed(2) : "–"}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="space-y-1">
            <CardTitle>Análise Multidimensional</CardTitle>
            <p className="text-sm text-muted-foreground">
              Radar consolidando os índices principais do projeto.
            </p>
          </CardHeader>
          <CardContent className="h-[280px]">
            {overview?.multidimensional?.dimensions?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={overview.multidimensional.dimensions}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} angle={30} />
                  <Radar
                    name="Score"
                    dataKey="value"
                    stroke="#8b5cf6"
                    fill="#8b5cf6"
                    fillOpacity={0.35}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                {loading ? (
                  <Skeleton className="h-48 w-full" />
                ) : (
                  <span className="text-sm text-muted-foreground">
                    Sem dados suficientes para plotar o radar.
                  </span>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {renderSemanticSection()}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Evolução IM-SEO & IM-SEOIA</CardTitle>
          </CardHeader>
          <CardContent>
            {renderTimelineChart([
              { key: "im_seo_score", label: "IM-SEO", color: "#3b82f6" },
              { key: "im_seoia_score", label: "IM-SEOIA", color: "#8b5cf6" },
            ])}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Distribuição IM-SEO</CardTitle>
          </CardHeader>
          <CardContent>
            {overview?.distribution?.im_seo ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={Object.entries(overview.distribution.im_seo).map(([label, count]) => ({
                    label,
                    count,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              renderSkeleton()
            )}
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList>
          <TabsTrigger value="performance">
            <Activity className="w-4 h-4 mr-2" />
            Performance
          </TabsTrigger>
          <TabsTrigger value="content">
            <Award className="w-4 h-4 mr-2" />
            Conteúdo
          </TabsTrigger>
          <TabsTrigger value="serp">
            <Target className="w-4 h-4 mr-2" />
            SERP
          </TabsTrigger>
          <TabsTrigger value="ia">
            <Brain className="w-4 h-4 mr-2" />
            IA-Ready
          </TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Core Web Vitals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatValue(overview?.metrics?.core_web_vitals.average)}</div>
                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">LCP</span>
                    <span className="font-medium">{formatValue(overview?.metrics?.core_web_vitals.lcp)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">FID</span>
                    <span className="font-medium">{formatValue(overview?.metrics?.core_web_vitals.fid)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">CLS</span>
                    <span className="font-medium">{formatValue(overview?.metrics?.core_web_vitals.cls)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">IRZC</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatValue(overview?.metrics?.irzc.average)}</div>
                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">CTR Real</span>
                    <span className="font-medium">{formatPercent(overview?.metrics?.irzc.ctr_real_avg, 2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">CTR Esperado</span>
                    <span className="font-medium">{formatPercent(overview?.metrics?.irzc.ctr_expected_avg, 2)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Posição SERP</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatValue(overview?.metrics?.serp.organic_position_avg)}</div>
                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Share of Voice</span>
                    <span className="font-medium">{formatPercent(overview?.metrics?.serp.share_of_voice_avg)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">SERP Features</span>
                    <span className="font-medium">{formatPercent(overview?.metrics?.serp.serp_features_avg)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="content" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">E-E-A-T Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={[
                      { name: "Expertise", value: overview?.metrics?.eeat.expertise },
                      { name: "Experience", value: overview?.metrics?.eeat.experience },
                      { name: "Authority", value: overview?.metrics?.eeat.authoritativeness },
                      { name: "Trust", value: overview?.metrics?.eeat.trustworthiness },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">IA-Ready Blocks</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold mb-4">
                  {(overview?.metrics?.ia_ready.blocks_avg ?? 0).toFixed(1)} blocos/run
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Listas</span>
                    <span className="font-medium">
                      {(overview?.metrics?.ia_ready.has_lists_pct ?? 0).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">FAQs</span>
                    <span className="font-medium">
                      {(overview?.metrics?.ia_ready.has_faqs_pct ?? 0).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tabelas</span>
                    <span className="font-medium">
                      {(overview?.metrics?.ia_ready.has_tables_pct ?? 0).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="serp" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Métricas SERP ao Longo do Tempo</CardTitle>
            </CardHeader>
            <CardContent>
              {renderTimelineChart([
                { key: "share_of_voice_serp", label: "Share of Voice", color: "#f59e0b" },
              ])}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ia" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Evolução IA-Ready</CardTitle>
            </CardHeader>
            <CardContent>
              {renderTimelineChart([
                { key: "im_seoia_score", label: "IM-SEOIA", color: "#8b5cf6" },
                { key: "eeat_score", label: "E-E-A-T", color: "#10b981" },
              ])}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Insights Prioritários</CardTitle>
            <p className="text-sm text-muted-foreground">
              Recomendações geradas a partir das métricas mais recentes.
            </p>
          </div>
          <Badge variant="secondary">{overview?.insights.length ?? 0} ativos</Badge>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
            {loading && (overview?.insights?.length ?? 0) === 0 ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <div
                  key={`insight-skeleton-${idx}`}
                  className="rounded-lg border border-dashed border-neutral-200 p-4 space-y-3"
                >
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ))
            ) : (overview?.insights?.length ?? 0) === 0 ? (
              <div className="col-span-full rounded-lg border border-dashed border-neutral-200 p-6 text-sm text-muted-foreground">
                Nenhum insight crítico encontrado para o recorte atual.
              </div>
            ) : (
              (overview?.insights ?? []).map((insight, idx) => {
                const severity = severityConfig[insight.severity] ?? severityConfig.default;
                return (
                  <div
                    key={insight.title + idx}
                    className={`rounded-lg border p-4 space-y-3 ${severity.tone}`}
                  >
                    <div className="flex items-center gap-2">
                      {severity.icon}
                      <span className="font-medium text-sm uppercase tracking-wide">
                        {severity.badge}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-base font-semibold">{insight.title}</h3>
                      <p className="text-sm text-neutral-600">{insight.description}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold">{overview?.total_runs ?? "-"}</div>
              <div className="text-sm text-muted-foreground">Total de Runs</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{filters.days}</div>
              <div className="text-sm text-muted-foreground">Dias Analisados</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{formatValue(overview?.metrics?.im_seo.max)}</div>
              <div className="text-sm text-muted-foreground">Melhor IM-SEO</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{formatValue(overview?.metrics?.im_seoia.max)}</div>
              <div className="text-sm text-muted-foreground">Melhor IM-SEOIA</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
