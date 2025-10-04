import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { ChevronDown, ChevronUp, X } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";

export interface FilterState {
  project_id?: string;
  subproject_id?: string;
  prompt_id?: string;
  run_id?: string;
  engine_ids?: string[];
  days: number;
  start_date?: string;
  end_date?: string;
  im_seo_min?: number;
  im_seo_max?: number;
  im_seoia_min?: number;
  im_seoia_max?: number;
}

type ProjectOption = { id: string; name: string };
type ThemeOption = { id: string; name: string; project_id: string };
type PromptOption = {
  id: string;
  name: string;
  project_id: string;
  intent?: string | null;
};
type RunOption = {
  id: string;
  project_id: string;
  subproject_id?: string | null;
  prompt_id?: string | null;
  prompt_name?: string | null;
  engine_name?: string | null;
  engine_region?: string | null;
  engine_device?: string | null;
  status?: string | null;
  started_at?: string | null;
  engine_group_key: string;
};
type EngineGroup = {
  key: string;
  label: string;
  name: string;
  region?: string | null;
  device?: string | null;
  engine_ids: string[];
};

interface FiltersResponse {
  projects: ProjectOption[];
  themes: ThemeOption[];
  prompts: PromptOption[];
  runs: RunOption[];
  engine_groups: EngineGroup[];
}

type FiltersProps = {
  onFilterChange: (filters: FilterState) => void;
};

const chipClass =
  "px-3 py-1 rounded-full border text-sm transition-colors whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400";

function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        chipClass +
        (active
          ? " bg-neutral-900 text-white border-neutral-900 shadow-sm"
          : " bg-white text-neutral-700 border-neutral-300 hover:bg-neutral-100")
      }
    >
      {label}
    </button>
  );
}

function formatRunLabel(run: RunOption) {
  const parts: string[] = [];
  if (run.prompt_name) parts.push(run.prompt_name);
  if (run.engine_name) {
    const engineBits = [run.engine_name];
    if (run.engine_region) engineBits.push(run.engine_region);
    if (run.engine_device) engineBits.push(run.engine_device.toUpperCase());
    parts.push(engineBits.join(" · "));
  }
  if (run.started_at) {
    const date = new Date(run.started_at);
    parts.push(
      date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "short",
      })
    );
  }
  return parts.join(" • ") || run.id;
}

type ActiveBadge = { key: string; label: string; variant?: "default" | "secondary" };

export function IMFilters({ onFilterChange }: FiltersProps) {
  const [options, setOptions] = useState<FiltersResponse>({
    projects: [],
    themes: [],
    prompts: [],
    runs: [],
    engine_groups: [],
  });
  const [loadingOptions, setLoadingOptions] = useState(false);

  const [selectedProject, setSelectedProject] = useState<string>("");
  const [selectedTheme, setSelectedTheme] = useState<string>("");
  const [selectedPrompt, setSelectedPrompt] = useState<string>("");
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [selectedEngineGroups, setSelectedEngineGroups] = useState<string[]>([]);
  const [days, setDays] = useState(30);
  const [useCustomRange, setUseCustomRange] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [imSeoRange, setImSeoRange] = useState<[number, number]>([0, 100]);
  const [imSeoiaRange, setImSeoiaRange] = useState<[number, number]>([0, 100]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const engineGroupMap = useMemo(() => {
    const map = new Map<string, EngineGroup>();
    options.engine_groups.forEach((group) => {
      map.set(group.key, group);
    });
    return map;
  }, [options.engine_groups]);

  useEffect(() => {
    const loadOptions = async () => {
      setLoadingOptions(true);
      try {
        const response = await axios.get<FiltersResponse>("/api/analytics/im-filters", {
          params: selectedProject ? { project_id: selectedProject } : undefined,
        });
        setOptions(response.data);
      } catch (error) {
        console.error("Erro ao carregar filtros IM:", error);
      } finally {
        setLoadingOptions(false);
      }
    };

    void loadOptions();
  }, [selectedProject]);

  useEffect(() => {
    if (selectedTheme && !options.themes.some((theme) => theme.id === selectedTheme)) {
      setSelectedTheme("");
    }
    if (selectedPrompt && !options.prompts.some((prompt) => prompt.id === selectedPrompt)) {
      setSelectedPrompt("");
    }
    if (selectedRun && !options.runs.some((run) => run.id === selectedRun)) {
      setSelectedRun("");
    }

    setSelectedEngineGroups((prev) => prev.filter((key) => engineGroupMap.has(key)));
  }, [options, selectedTheme, selectedPrompt, selectedRun, engineGroupMap]);

  const engineIds = useMemo(() => {
    if (selectedEngineGroups.length === 0) return [] as string[];
    return selectedEngineGroups.flatMap((key) => engineGroupMap.get(key)?.engine_ids ?? []);
  }, [engineGroupMap, selectedEngineGroups]);

  useEffect(() => {
    const filters: FilterState = { days };

    if (selectedProject) filters.project_id = selectedProject;
    if (selectedTheme) filters.subproject_id = selectedTheme;
    if (selectedPrompt) filters.prompt_id = selectedPrompt;
    if (selectedRun) filters.run_id = selectedRun;
    if (engineIds.length > 0) filters.engine_ids = engineIds;

    if (useCustomRange) {
      if (startDate) filters.start_date = startDate;
      if (endDate) filters.end_date = endDate;
    }
    if (imSeoRange[0] > 0 || imSeoRange[1] < 100) {
      filters.im_seo_min = imSeoRange[0];
      filters.im_seo_max = imSeoRange[1];
    }
    if (imSeoiaRange[0] > 0 || imSeoiaRange[1] < 100) {
      filters.im_seoia_min = imSeoiaRange[0];
      filters.im_seoia_max = imSeoiaRange[1];
    }

    onFilterChange(filters);
  }, [
    days,
    engineIds,
    endDate,
    imSeoRange,
    imSeoiaRange,
    onFilterChange,
    selectedProject,
    selectedPrompt,
    selectedRun,
    selectedTheme,
    startDate,
    useCustomRange,
  ]);

  const clearFilters = () => {
    setSelectedProject("");
    setSelectedTheme("");
    setSelectedPrompt("");
    setSelectedRun("");
    setSelectedEngineGroups([]);
    setDays(30);
    setUseCustomRange(false);
    setStartDate("");
    setEndDate("");
    setImSeoRange([0, 100]);
    setImSeoiaRange([0, 100]);
    setShowAdvanced(false);
  };

  const scopedThemes = selectedProject
    ? options.themes.filter((theme) => theme.project_id === selectedProject)
    : options.themes;
  const scopedPrompts = selectedProject
    ? options.prompts.filter((prompt) => prompt.project_id === selectedProject)
    : options.prompts;
  const scopedRuns = selectedProject
    ? options.runs.filter((run) => run.project_id === selectedProject)
    : options.runs;

  const selectedProjectOption = options.projects.find((p) => p.id === selectedProject);
  const selectedThemeOption = scopedThemes.find((t) => t.id === selectedTheme);
  const selectedPromptOption = scopedPrompts.find((p) => p.id === selectedPrompt);
  const selectedRunOption = scopedRuns.find((r) => r.id === selectedRun);

  const activeFilterBadges = useMemo<ActiveBadge[]>(() => {
    const badges: ActiveBadge[] = [];

    if (selectedProjectOption) {
      badges.push({
        key: `project-${selectedProjectOption.id}`,
        label: selectedProjectOption.name,
        variant: "default",
      });
    }

    if (selectedThemeOption) {
      badges.push({
        key: `theme-${selectedThemeOption.id}`,
        label: selectedThemeOption.name,
      });
    }

    if (selectedPromptOption) {
      badges.push({
        key: `prompt-${selectedPromptOption.id}`,
        label: selectedPromptOption.name,
      });
    }

    if (selectedRunOption) {
      badges.push({
        key: `run-${selectedRunOption.id}`,
        label: formatRunLabel(selectedRunOption),
      });
    }

    if (selectedEngineGroups.length > 0) {
      badges.push({
        key: "engines",
        label: `${selectedEngineGroups.length} engine(s)`,
      });
    }

    if (useCustomRange && (startDate || endDate)) {
      badges.push({
        key: "date-range",
        label: `${startDate || "?"} → ${endDate || "?"}`,
      });
    } else if (days !== 30) {
      badges.push({
        key: "days",
        label: `${days} dias`,
      });
    }

    if (imSeoRange[0] > 0 || imSeoRange[1] < 100) {
      badges.push({
        key: "im-seo-range",
        label: `IM-SEO ${imSeoRange[0]} - ${imSeoRange[1]}`,
      });
    }

    if (imSeoiaRange[0] > 0 || imSeoiaRange[1] < 100) {
      badges.push({
        key: "im-seoia-range",
        label: `IM-SEOIA ${imSeoiaRange[0]} - ${imSeoiaRange[1]}`,
      });
    }

    return badges;
  }, [
    days,
    endDate,
    imSeoRange,
    imSeoiaRange,
    selectedEngineGroups,
    selectedProjectOption,
    selectedPromptOption,
    selectedRunOption,
    selectedThemeOption,
    startDate,
    useCustomRange,
  ]);

  const hasFilters = activeFilterBadges.length > 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg">Filtros</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCollapsed((prev) => !prev)}
              className="h-8 gap-2"
            >
              {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              {collapsed ? "Expandir" : "Recolher"}
            </Button>
          </div>
          <div className="flex items-center gap-2">
            {hasFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="h-8">
                <X className="w-4 h-4 mr-1" />
                Limpar
              </Button>
            )}
            {hasFilters && (
              <Badge variant="secondary" className="hidden sm:inline-flex">
                {activeFilterBadges.length} filtro(s)
              </Badge>
            )}
          </div>
        </div>
        {collapsed && (
          <div className="mt-2 flex flex-wrap gap-2">
            {hasFilters ? (
              activeFilterBadges.map((badge) => (
                <Badge
                  key={`collapsed-${badge.key}`}
                  variant={badge.variant ?? "secondary"}
                  className="text-xs"
                >
                  {badge.label}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-neutral-500">Sem filtros ativos</span>
            )}
          </div>
        )}
      </CardHeader>

      {!collapsed && (
        <CardContent className="space-y-6">
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Escopo</h3>
              {loadingOptions && <span className="text-xs text-neutral-500">Carregando…</span>}
            </div>
            <div className="space-y-3">
              <div className="space-y-2">
                <span className="text-xs font-medium text-neutral-500">Projeto</span>
                <div className="flex flex-wrap gap-2">
                  {options.projects.map((project) => (
                    <Chip
                      key={project.id}
                      label={project.name}
                      active={selectedProject === project.id}
                      onClick={() =>
                        setSelectedProject((prev) => (prev === project.id ? "" : project.id))
                      }
                    />
                  ))}
                  {options.projects.length === 0 && (
                    <span className="text-sm text-neutral-500">Nenhum projeto encontrado.</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-medium text-neutral-500">Tema</span>
                <div className="flex flex-wrap gap-2">
                  {scopedThemes.map((theme) => (
                    <Chip
                      key={theme.id}
                      label={theme.name}
                      active={selectedTheme === theme.id}
                      onClick={() =>
                        setSelectedTheme((prev) => (prev === theme.id ? "" : theme.id))
                      }
                    />
                  ))}
                  {scopedThemes.length === 0 && (
                    <span className="text-sm text-neutral-500">Nenhum tema disponível.</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-medium text-neutral-500">Prompt</span>
                <div className="flex flex-wrap gap-2">
                  {scopedPrompts.map((prompt) => (
                    <Chip
                      key={prompt.id}
                      label={prompt.name}
                      active={selectedPrompt === prompt.id}
                      onClick={() =>
                        setSelectedPrompt((prev) => (prev === prompt.id ? "" : prompt.id))
                      }
                    />
                  ))}
                  {scopedPrompts.length === 0 && (
                    <span className="text-sm text-neutral-500">Nenhum prompt cadastrado.</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-medium text-neutral-500">Run</span>
                <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto border border-dashed border-neutral-200 rounded-md p-2">
                  {scopedRuns.map((run) => (
                    <Chip
                      key={run.id}
                      label={formatRunLabel(run)}
                      active={selectedRun === run.id}
                      onClick={() => setSelectedRun((prev) => (prev === run.id ? "" : run.id))}
                    />
                  ))}
                  {scopedRuns.length === 0 && (
                    <span className="text-sm text-neutral-500">Nenhuma run recente.</span>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">Engines</h3>
            <div className="flex flex-wrap gap-2">
              {options.engine_groups.map((engine) => (
                <Chip
                  key={engine.key}
                  label={engine.label}
                  active={selectedEngineGroups.includes(engine.key)}
                  onClick={() =>
                    setSelectedEngineGroups((prev) =>
                      prev.includes(engine.key)
                        ? prev.filter((key) => key !== engine.key)
                        : [...prev, engine.key]
                    )
                  }
                />
              ))}
              {options.engine_groups.length === 0 && (
                <span className="text-sm text-neutral-500">Nenhuma engine configurada.</span>
              )}
            </div>
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="space-y-2">
              <span className="text-xs font-medium text-neutral-500">Período</span>
              <div className="flex items-center gap-2">
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  disabled={useCustomRange}
                >
                  <option value={7}>Últimos 7 dias</option>
                  <option value={30}>Últimos 30 dias</option>
                  <option value={90}>Últimos 90 dias</option>
                  <option value={180}>Últimos 6 meses</option>
                  <option value={365}>Último ano</option>
                </select>
                <label className="flex items-center gap-2 text-sm text-neutral-600">
                  <input
                    type="checkbox"
                    checked={useCustomRange}
                    onChange={(e) => setUseCustomRange(e.target.checked)}
                    className="rounded"
                  />
                  Intervalo personalizado
                </label>
              </div>
              {useCustomRange && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="px-3 py-2 border rounded-lg text-sm"
                  />
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              )}
            </div>

            <div className="space-y-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAdvanced((prev) => !prev)}
                className="w-full sm:w-auto"
              >
                {showAdvanced ? "Ocultar" : "Mostrar"} filtros avançados
              </Button>
              {showAdvanced && (
                <div className="space-y-4 rounded-lg border border-dashed border-neutral-200 p-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      IM-SEO: {imSeoRange[0]} - {imSeoRange[1]}
                    </label>
                    <div className="flex gap-4 items-center">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={imSeoRange[0]}
                        onChange={(e) => setImSeoRange([Number(e.target.value), imSeoRange[1]])}
                        className="flex-1"
                      />
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={imSeoRange[1]}
                        onChange={(e) => setImSeoRange([imSeoRange[0], Number(e.target.value)])}
                        className="flex-1"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium mb-2 block">
                      IM-SEOIA: {imSeoiaRange[0]} - {imSeoiaRange[1]}
                    </label>
                    <div className="flex gap-4 items-center">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={imSeoiaRange[0]}
                        onChange={(e) => setImSeoiaRange([Number(e.target.value), imSeoiaRange[1]])}
                        className="flex-1"
                      />
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={imSeoiaRange[1]}
                        onChange={(e) => setImSeoiaRange([imSeoiaRange[0], Number(e.target.value)])}
                        className="flex-1"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="text-sm text-muted-foreground">
            {hasFilters ? (
              <div className="flex flex-wrap gap-2">
                <span className="font-medium text-neutral-600">Filtros ativos:</span>
                {activeFilterBadges.map((badge) => (
                  <Badge key={`active-${badge.key}`} variant={badge.variant ?? "secondary"}>
                    {badge.label}
                  </Badge>
                ))}
              </div>
            ) : (
              <span>Mostrando todos os dados</span>
            )}
          </section>
        </CardContent>
      )}
    </Card>
  );
}
