import { CSSProperties, ReactNode } from 'react';
import { clsx } from 'clsx';
import { Target, Star, TrendingUp, MessageCircle, MoreVertical } from 'lucide-react';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';

export type DomeGalleryTrend = 'up' | 'down' | 'stable';

export interface DomeGalleryMetric {
  label: string;
  value: string;
  icon?: string;
  iconColor?: string;
  trend?: DomeGalleryTrend;
  description?: string;
}

export interface DomeGalleryMeta {
  label: string;
  value: string;
}

export interface DomeGalleryItem {
  id: string;
  title: string;
  description?: string;
  engines?: string[];
  metrics?: DomeGalleryMetric[];
  meta?: DomeGalleryMeta;
  accent?: string;
  trend?: DomeGalleryTrend;
  runsLabel?: string;
}

interface DomeGalleryProps {
  items: DomeGalleryItem[];
  onSelect?: (item: DomeGalleryItem) => void;
  selectedId?: string;
  emptyState?: ReactNode;
  className?: string;
}

const metricIcons: Record<string, typeof Target> = {
  target: Target,
  star: Star,
  'trending-up': TrendingUp,
  'message-circle': MessageCircle,
  'more-vertical': MoreVertical,
};

export default function DomeGallery({
  items,
  onSelect,
  selectedId,
  emptyState,
  className,
}: DomeGalleryProps) {
  if (!items.length && emptyState) {
    return <div className="py-16 text-center text-slate-400">{emptyState}</div>;
  }

  return (
    <div className={clsx('relative', className)}>
      <div className="pointer-events-none absolute inset-x-0 -top-24 h-48 bg-[radial-gradient(ellipse_at_top,_rgba(191,219,254,0.35),_rgba(255,255,255,0))] blur-3xl" />

      <div className="hidden gap-10 lg:flex lg:flex-col">
        <div className="relative flex items-end justify-center gap-8">
          {items.map((item, index) => {
            const centerIndex = (items.length - 1) / 2;
            const offset = index - centerIndex;
            const distance = Math.abs(offset);
            const isSelected = item.id === selectedId;
            const baseScale = 1 - distance * 0.08;
            const scale = isSelected ? baseScale + 0.12 : baseScale;

            const style: CSSProperties = {
              transform: [
                'perspective(1400px)',
                `translateX(${offset * 36}px)`,
                `translateY(${distance * 8}px)`,
                `rotateY(${offset * -12}deg)`,
                `translateZ(${isSelected ? 80 : 50 - distance * 12}px)`,
                `scale(${scale})`,
              ].join(' '),
              transformStyle: 'preserve-3d',
              opacity: distance > 3 ? 0 : 1,
            };

            return (
              <button
                key={item.id}
                type="button"
                style={style}
                className="group relative w-[320px] transform-gpu text-left focus:outline-none"
                onClick={() => onSelect?.(item)}
              >
                <Card className={clsx(
                  'relative cursor-pointer overflow-hidden border-0 bg-white/85 p-6 shadow-sm backdrop-blur-sm transition-all duration-300',
                  isSelected
                    ? 'shadow-xl shadow-blue-100/70'
                    : 'hover:shadow-xl hover:shadow-blue-100/70'
                )}>
                  <div className="mb-4 flex items-start justify-between">
                    <Badge variant="secondary" className="bg-blue-50 text-xs font-medium text-blue-700 hover:bg-blue-50">
                      📊 Tendência
                    </Badge>
                    {item.runsLabel ? (
                      <span className="text-xs font-medium text-slate-400">{item.runsLabel}</span>
                    ) : null}
                  </div>

                  <h3 className="mb-3 line-clamp-4 text-base font-semibold leading-snug text-slate-900">
                    {item.title}
                  </h3>

                  {item.description ? (
                    <p className="mb-4 text-xs text-slate-500">{item.description}</p>
                  ) : null}

                  {item.engines?.length ? (
                    <div className="mb-6 flex flex-wrap gap-2">
                      {item.engines.map((engine) => (
                        <span
                          key={engine}
                          className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
                        >
                          {engine}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="mb-6 h-4" />
                  )}

                  {item.metrics?.length ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        {item.metrics.slice(0, 2).map((metric) => (
                          <MetricItem key={`${item.id}-${metric.label}`} metric={metric} />
                        ))}
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        {item.metrics.slice(2, 4).map((metric) => (
                          <MetricItem key={`${item.id}-${metric.label}`} metric={metric} />
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {item.meta ? (
                    <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-400">
                      <span>{item.meta.label}</span>
                      <span className="text-xs font-medium text-slate-600">{item.meta.value}</span>
                    </div>
                  ) : null}

                  <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-pink-500/5" />
                  </div>
                </Card>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-col gap-5 lg:hidden">
        {items.map((item) => {
          const isSelected = item.id === selectedId;

          return (
            <button
              key={item.id}
              type="button"
              className={clsx(
                'group relative rounded-[32px] border border-slate-100 bg-white px-6 py-7 text-left text-slate-900 shadow-[0_16px_36px_rgba(15,23,42,0.1)] transition-all duration-300 ease-out',
                isSelected
                  ? 'shadow-[0_22px_44px_rgba(15,23,42,0.14)]'
                  : 'hover:-translate-y-2 hover:shadow-[0_22px_44px_rgba(15,23,42,0.14)]',
              )}
              onClick={() => onSelect?.(item)}
            >
              <div className="mb-4 flex items-start justify-between">
                <Badge variant="secondary" className="bg-blue-50 text-xs font-medium text-blue-700 hover:bg-blue-50">
                  📊 Tendência
                </Badge>
                {item.runsLabel ? (
                  <span className="text-xs font-medium text-slate-400">{item.runsLabel}</span>
                ) : null}
              </div>

              <h3 className="mb-3 line-clamp-4 text-base font-semibold leading-snug text-slate-900">
                {item.title}
              </h3>

              {item.description ? (
                <p className="mb-4 text-xs text-slate-500">{item.description}</p>
              ) : null}

              {item.engines?.length ? (
                <div className="mb-6 flex flex-wrap gap-2">
                  {item.engines.map((engine) => (
                    <span
                      key={engine}
                      className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
                    >
                      {engine}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="mb-6 h-4" />
              )}

              {item.metrics?.length ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    {item.metrics.slice(0, 2).map((metric) => (
                      <MetricItem key={`${item.id}-${metric.label}`} metric={metric} />
                    ))}
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {item.metrics.slice(2, 4).map((metric) => (
                      <MetricItem key={`${item.id}-${metric.label}`} metric={metric} />
                    ))}
                  </div>
                </div>
              ) : null}

              {item.meta ? (
                <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-400">
                  <span>{item.meta.label}</span>
                  <span className="text-xs font-medium text-slate-600">{item.meta.value}</span>
                </div>
              ) : null}

              <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-purple-500/5 to-pink-500/5" />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MetricItem({ metric }: { metric: DomeGalleryMetric }) {
  const IconComponent = metric.icon ? metricIcons[metric.icon as keyof typeof metricIcons] : null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{metric.label}</span>
        {IconComponent ? (
          <IconComponent className={clsx('h-3.5 w-3.5', metric.iconColor ?? 'text-slate-400')} />
        ) : null}
      </div>
      <div className="text-xl font-bold text-slate-900">{metric.value}</div>
    </div>
  );
}
