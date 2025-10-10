import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import api, { getProjects, type Project } from '../lib/api';
import CountUp from '../components/reactbits/CountUp';
import GradientText from '../components/reactbits/GradientText';
import GlowCard from '../components/reactbits/GlowCard';
import DomeGallery, { type DomeGalleryItem } from '../components/reactbits/DomeGallery';
import SegmentedControl from '../components/reactbits/SegmentedControl';
import PrismBackground from '../components/reactbits/backgrounds/PrismBackground';
import { Badge } from '../components/ui/badge';
import { X, Newspaper, Target, Zap, MessageCircle, Sparkles, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface PromptData {
  prompt_text: string;
  prompt_preview: string;
  runs_count: number;
  engines: string[];
  brand_presence: {
    avg_mention_count: number;
    avg_first_mention_pos: number | null;
    avg_mention_density: number;
    avg_prominence_score: number;
  };
  citation_quality: {
    avg_citation_rate_observed: number;
    avg_citation_rate_corrected: number;
    avg_first_citation_pos: number | null;
    avg_quality_score: number;
  };
  competitive_intel: {
    avg_competitor_ratio: number;
    avg_sov_llm: number;
    avg_cocitation_count: number;
  };
  engagement: {
    avg_trigger_count: number;
    avg_engagement_score: number;
  };
  advanced_metrics: {
    avg_zero_click_presence: number;
    avg_authority_score: number;
    avg_relevance_score: number;
    avg_clarity_score: number;
    avg_conversion_potential: number;
  };
  zero_click_classification: {
    response_types: Record<string, number>;
    sufficiency_levels: Record<string, number>;
    actionability: Record<string, number>;
    trust_sources: Record<string, number>;
    brand_positions: Record<string, number>;
    funnel_stages: Record<string, number>;
  };
  latest_run_date: string;
  trend: 'up' | 'down' | 'stable';
}

interface VisualizerData {
  prompts: PromptData[];
  total_prompts: number;
  total_runs: number;
  period_start: string;
  period_end: string;
}

export default function PromptVisualizer() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<VisualizerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptData | null>(null);
  const [days, setDays] = useState(30);
  const [searchTerm, setSearchTerm] = useState('');

  // Load projects
  useEffect(() => {
    getProjects()
      .then((items) => {
        setProjects(items);
        const projectIdParam = searchParams.get('project_id');
        if (projectIdParam) {
          setSelectedProjectId(projectIdParam);
        } else if (items.length > 0) {
          const defaultProjectId = items[0].id;
          setSelectedProjectId(defaultProjectId);
          setSearchParams((prev) => {
            const params = new URLSearchParams(prev);
            params.set('project_id', defaultProjectId);
            return params;
          });
        }
      })
      .catch(() => {
        setProjects([]);
      });
  }, []);

  // Sync with URL params
  useEffect(() => {
    const projectIdParam = searchParams.get('project_id');
    if (projectIdParam && projectIdParam !== selectedProjectId) {
      setSelectedProjectId(projectIdParam);
    }
  }, [searchParams]);

  // Fetch data when project changes
  useEffect(() => {
    if (selectedProjectId) {
      fetchData();
    }
  }, [selectedProjectId, days]);

  const fetchData = async () => {
    if (!selectedProjectId) return;

    try {
      setLoading(true);
      const response = await api.get(`/projects/${selectedProjectId}/geo/prompt-visualizer`, {
        params: { days }
      });
      setData(response.data);
    } catch (error) {
      console.error('Error fetching prompt visualizer data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (projectId: string) => {
    setSelectedProjectId(projectId);
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (projectId) {
        params.set('project_id', projectId);
      } else {
        params.delete('project_id');
      }
      return params;
    });
  };

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return '📈';
    if (trend === 'down') return '📉';
    return '➡️';
  };

  const filteredPrompts = useMemo(() => {
    if (!data?.prompts?.length) return [];
    return data.prompts.filter((p) =>
      p.prompt_text.toLowerCase().includes(searchTerm.toLowerCase()),
    );
  }, [data, searchTerm]);

  const promptGalleryItems: DomeGalleryItem[] = useMemo(() => {
    return filteredPrompts.map((prompt) => ({
      id: prompt.prompt_text,
      title: prompt.prompt_preview || prompt.prompt_text,
      description: `Janela de ${days} dias com ${prompt.engines.length} ${
        prompt.engines.length === 1 ? 'engine' : 'engines'
      } ativas.`,
      engines: prompt.engines,
      accent: `${getTrendIcon(prompt.trend)} Tendência`,
      trend: prompt.trend,
      runsLabel: `${prompt.runs_count} runs`,
      metrics: [
        {
          label: 'CITATION',
          value: `${prompt.citation_quality.avg_citation_rate_corrected.toFixed(1)}%`,
          icon: 'target',
          iconColor: 'text-red-500',
          trend: prompt.trend,
        },
        {
          label: 'PROMINENCE',
          value: prompt.brand_presence.avg_prominence_score.toFixed(0),
          icon: 'star',
          iconColor: 'text-amber-500',
        },
        {
          label: 'SOV LLM',
          value: `${prompt.competitive_intel.avg_sov_llm.toFixed(1)}%`,
          icon: 'trending-up',
          iconColor: 'text-blue-500',
        },
        {
          label: 'ENGAGEMENT',
          value: prompt.engagement.avg_engagement_score.toFixed(0),
          icon: 'message-circle',
          iconColor: 'text-slate-400',
        },
      ],
      meta: {
        label: 'Última run',
        value: new Date(prompt.latest_run_date).toLocaleDateString('pt-BR'),
      },
    }));
  }, [filteredPrompts, days]);

  const promptById = useMemo(() => {
    const map = new Map<string, PromptData>();
    filteredPrompts.forEach((prompt) => map.set(prompt.prompt_text, prompt));
    return map;
  }, [filteredPrompts]);

  const selectedPromptId = selectedPrompt?.prompt_text ?? null;

  useEffect(() => {
    if (selectedPromptId && !filteredPrompts.some((p) => p.prompt_text === selectedPromptId)) {
      setSelectedPrompt(null);
    }
  }, [filteredPrompts, selectedPromptId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white text-xl font-light">Carregando visualizador de prompts...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900">
        <div className="text-center text-white">
          <p className="text-2xl">Erro ao carregar dados</p>
        </div>
      </div>
    );
  }

  return (
    <PrismBackground>
        {/* Header Section */}
        <div className="relative overflow-hidden">
        {/* Animated Background Pattern */}
        <div className="absolute inset-0 opacity-80">
          <div className="absolute inset-0 bg-gradient-to-r from-sky-200/80 via-indigo-100/70 to-transparent animate-[pulse_18s_ease-in-out_infinite]"></div>
        </div>

        <div className="relative z-10 container mx-auto px-6 py-12">
          <div className="text-center mb-8">
            <h1 className="text-6xl font-bold mb-4">
              <GradientText colors={['#1d4ed8', '#2563eb', '#38bdf8']} animationSpeed={6}>
                Prompt Visualizer
              </GradientText>
            </h1>
            <p className="text-xl text-slate-600 font-light">
              Análise visual de performance GEO por prompt
            </p>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <GlowCard glowColor="rgba(96, 165, 250, 0.4)">
              <div className="bg-white/70 backdrop-blur-md rounded-2xl p-6 border border-white/40 hover:bg-white/90 transition-all text-slate-800">
                <div className="text-sm text-slate-500 mb-2">Total de Prompts</div>
                <div className="text-4xl font-bold">
                  <GradientText colors={['#1d4ed8', '#0ea5e9']}>
                    <CountUp end={data.total_prompts} duration={1.5} />
                  </GradientText>
                </div>
              </div>
            </GlowCard>
            <GlowCard glowColor="rgba(168, 85, 247, 0.4)">
              <div className="bg-white/70 backdrop-blur-md rounded-2xl p-6 border border-white/40 hover:bg-white/90 transition-all text-slate-800">
                <div className="text-sm text-slate-500 mb-2">Total de Runs</div>
                <div className="text-4xl font-bold">
                  <GradientText colors={['#2563eb', '#38bdf8']}>
                    <CountUp end={data.total_runs} duration={1.5} />
                  </GradientText>
                </div>
              </div>
            </GlowCard>
            <GlowCard glowColor="rgba(244, 114, 182, 0.4)">
              <div className="bg-white/70 backdrop-blur-md rounded-2xl p-6 border border-white/40 hover:bg-white/90 transition-all text-slate-800">
                <div className="text-sm text-slate-500 mb-2">Período</div>
                <div className="text-2xl font-bold text-slate-900">
                  <CountUp end={days} duration={1} /> dias
                </div>
              </div>
            </GlowCard>
          </div>

          {/* Filters */}
          <div className="flex flex-col gap-4 md:flex-row md:items-center mb-8">
            <div className="w-full md:w-64">
              <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                Projeto
              </div>
              <select
                value={selectedProjectId}
                onChange={(e) => handleProjectChange(e.target.value)}
                className="w-full px-5 py-4 rounded-2xl border border-white/50 bg-white/70 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
              >
                <option value="" className="bg-gray-800">Selecione um projeto</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id} className="bg-white text-slate-900">
                    {project.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                Buscar
              </div>
              <input
                type="text"
                placeholder="🔍 Buscar prompts..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-6 py-4 bg-white/70 backdrop-blur-md rounded-2xl border border-white/50 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-all"
              />
            </div>
            <div className="w-full md:w-80">
              <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                Janela de análise
              </div>
              <SegmentedControl
                value={days}
                onChange={(value) => setDays(Number(value))}
                options={[
                  { label: '7 dias', value: 7 },
                  { label: '30 dias', value: 30 },
                  { label: '60 dias', value: 60 },
                  { label: '90 dias', value: 90 },
                ]}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Prompts Grid */}
      <div className="container mx-auto px-6 pb-12">
        {promptGalleryItems.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-2xl text-gray-400">Nenhum prompt encontrado</p>
          </div>
        ) : (
          <DomeGallery
            items={promptGalleryItems}
            selectedId={selectedPromptId ?? undefined}
            onSelect={(item) => {
              const prompt = promptById.get(item.id);
              if (prompt) {
                setSelectedPrompt(prompt);
              }
            }}
          />
        )}
      </div>

      {/* Detail Modal */}
      {selectedPrompt && (
        <PromptDetailModal
          prompt={selectedPrompt}
          onClose={() => setSelectedPrompt(null)}
        />
      )}
    </PrismBackground>
  );
}

// Detail Modal Component
function PromptDetailModal({
  prompt,
  onClose,
}: {
  prompt: PromptData;
  onClose: () => void;
}) {
  const trendBadge = prompt.trend === 'up' ? 'Alta' : prompt.trend === 'down' ? 'Baixa' : 'Estável';
  const trendIcon = prompt.trend === 'up' ? '📈' : prompt.trend === 'down' ? '📉' : '➖';
  const clampProgress = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return 0;
    return Math.max(0, Math.min(100, value));
  };

  const invertProgress = (value: number | null | undefined) => clampProgress(value !== undefined && value !== null ? 100 - value : 0);

  const determineTrend = (progress: number, positive = true): 'up' | 'down' | 'neutral' => {
    if (progress >= 66) return positive ? 'up' : 'down';
    if (progress <= 33) return positive ? 'down' : 'up';
    return 'neutral';
  };

  const sections = [
    {
      title: 'Brand Presence',
      icon: <Newspaper className="h-5 w-5 text-blue-600" />,
      iconBg: 'bg-blue-50',
      metrics: [
        (() => {
          const value = prompt.brand_presence.avg_mention_count;
          const display = Number.isFinite(value) ? value.toFixed(1) : 'N/A';
          const progress = clampProgress((value ?? 0) * 10);
          return { label: 'Menções', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const raw = prompt.brand_presence.avg_first_mention_pos ?? 0;
          const display = prompt.brand_presence.avg_first_mention_pos !== null ? raw.toFixed(0) : 'N/A';
          const progress = invertProgress(clampProgress(Math.min(raw, 100)));
          return { label: '1ª Menção (pos)', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const percent = (prompt.brand_presence.avg_mention_density ?? 0) * 100;
          const display = `${percent.toFixed(2)}%`;
          const progress = clampProgress(percent);
          return { label: 'Densidade', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.brand_presence.avg_prominence_score;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Prominence Score', value: display, progress, trend: determineTrend(progress) };
        })(),
      ],
    },
    {
      title: 'Citation Quality',
      icon: <Target className="h-5 w-5 text-purple-600" />,
      iconBg: 'bg-purple-50',
      metrics: [
        (() => {
          const value = prompt.citation_quality.avg_citation_rate_observed;
          const percent = value ?? 0;
          const display = `${percent.toFixed(1)}%`;
          const progress = clampProgress(percent);
          return { label: 'Citation Rate (Obs)', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.citation_quality.avg_citation_rate_corrected;
          const percent = value ?? 0;
          const display = `${percent.toFixed(1)}%`;
          const progress = clampProgress(percent);
          return { label: 'Citation Rate (Cor)', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const raw = prompt.citation_quality.avg_first_citation_pos ?? 0;
          const display = prompt.citation_quality.avg_first_citation_pos !== null ? raw.toFixed(0) : 'N/A';
          const progress = invertProgress(clampProgress(Math.min(raw, 100)));
          return { label: '1ª Citação (pos)', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.citation_quality.avg_quality_score;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Quality Score', value: display, progress, trend: determineTrend(progress) };
        })(),
      ],
    },
    {
      title: 'Competitive Intelligence',
      icon: <Zap className="h-5 w-5 text-amber-600" />,
      iconBg: 'bg-amber-50',
      metrics: [
        (() => {
          const value = prompt.competitive_intel.avg_competitor_ratio;
          const display = Number.isFinite(value) ? value.toFixed(2) : 'N/A';
          const progress = clampProgress((value ?? 0) * 100);
          return { label: 'Competitor Ratio', value: display, progress, trend: determineTrend(progress, false) };
        })(),
        (() => {
          const value = prompt.competitive_intel.avg_sov_llm ?? 0;
          const display = `${value.toFixed(1)}%`;
          const progress = clampProgress(value);
          return { label: 'Share of Voice (LLM)', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.competitive_intel.avg_cocitation_count;
          const display = Number.isFinite(value) ? value.toFixed(1) : 'N/A';
          const progress = clampProgress((value ?? 0) * 10);
          return { label: 'Co-citation Count', value: display, progress, trend: determineTrend(progress) };
        })(),
      ],
    },
    {
      title: 'Engagement',
      icon: <MessageCircle className="h-5 w-5 text-emerald-600" />,
      iconBg: 'bg-emerald-50',
      metrics: [
        (() => {
          const value = prompt.engagement.avg_trigger_count;
          const display = Number.isFinite(value) ? value.toFixed(1) : 'N/A';
          const progress = clampProgress((value ?? 0) * 5);
          return { label: 'Trigger Count', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.engagement.avg_engagement_score;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Engagement Score', value: display, progress, trend: determineTrend(progress) };
        })(),
      ],
    },
    {
      title: 'Advanced Metrics',
      icon: <Sparkles className="h-5 w-5 text-pink-600" />,
      iconBg: 'bg-pink-50',
      metrics: [
        (() => {
          const value = prompt.advanced_metrics.avg_zero_click_presence;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Zero-Click', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.advanced_metrics.avg_authority_score;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Authority', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.advanced_metrics.avg_relevance_score;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Relevance', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.advanced_metrics.avg_clarity_score;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Clarity', value: display, progress, trend: determineTrend(progress) };
        })(),
        (() => {
          const value = prompt.advanced_metrics.avg_conversion_potential;
          const display = Number.isFinite(value) ? value.toFixed(0) : 'N/A';
          const progress = clampProgress(value ?? 0);
          return { label: 'Conversion', value: display, progress, trend: determineTrend(progress) };
        })(),
      ],
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div
        className="relative z-10 max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-20 border-b border-gray-200 bg-white p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h2 className="mb-3 text-balance text-2xl font-bold leading-tight text-slate-900">{prompt.prompt_text}</h2>
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm font-medium text-slate-600">{prompt.runs_count} execuções</span>
                <Badge className="bg-emerald-50 text-xs font-semibold text-emerald-700 hover:bg-emerald-50">
                  {trendIcon} Tendência: {trendBadge}
                </Badge>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-gray-100 hover:text-slate-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="space-y-6 p-6">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-700">Engines Executadas</h3>
            <div className="flex flex-wrap gap-2">
              {prompt.engines.map((engine) => (
                <Badge
                  key={engine}
                  className="bg-white px-4 py-2 text-sm font-medium text-slate-800 shadow-sm hover:bg-white"
                >
                  {engine}
                </Badge>
              ))}
            </div>
          </div>

          {sections.map((section) => (
            <DashboardMetricSection
              key={section.title}
              icon={section.icon}
              title={section.title}
              iconBg={section.iconBg}
              metrics={section.metrics}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function DashboardMetricSection({
  icon,
  title,
  iconBg,
  metrics,
}: {
  icon: React.ReactNode;
  title: string;
  iconBg: string;
  metrics: Array<{ label: string; value: string; progress: number; trend: 'up' | 'down' | 'neutral' }>;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-3">
        <div className={`rounded-lg p-2 ${iconBg}`}>{icon}</div>
        <h3 className="text-lg font-bold text-slate-900">{title}</h3>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={`${title}-${metric.label}`} {...metric} />
        ))}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  progress,
  trend,
}: {
  label: string;
  value: string;
  progress: number;
  trend: 'up' | 'down' | 'neutral';
}) {
  const trendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />;
      case 'down':
        return <TrendingDown className="h-3.5 w-3.5 text-rose-600" />;
      default:
        return <Minus className="h-3.5 w-3.5 text-slate-400" />;
    }
  };

  const trendColor =
    trend === 'up' ? 'text-emerald-600' : trend === 'down' ? 'text-rose-600' : 'text-slate-600';

  return (
    <div className="group rounded-lg border border-gray-200 bg-gray-50 p-4 transition-all hover:border-blue-200 hover:bg-white hover:shadow-md">
      <div className="mb-3 flex items-start justify-between">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
        {trendIcon()}
      </div>
      <div className={`mb-3 text-2xl font-bold ${trendColor}`}>{value}</div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
    </div>
  );
}
