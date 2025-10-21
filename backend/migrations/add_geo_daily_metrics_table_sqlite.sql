CREATE TABLE IF NOT EXISTS geo_daily_metrics (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    metric_date DATE NOT NULL,
    window_days INTEGER NOT NULL DEFAULT 1,
    prompt_id TEXT,
    prompt_version_id TEXT,
    subproject_id TEXT,
    llm_model TEXT,
    brand_presence TEXT NOT NULL DEFAULT 'all',
    runs_total INTEGER NOT NULL DEFAULT 0,
    runs_with_brand INTEGER NOT NULL DEFAULT 0,
    brand_mentions_total INTEGER NOT NULL DEFAULT 0,
    exclusive_mentions_total INTEGER NOT NULL DEFAULT 0,
    brand_prominence_sum REAL NOT NULL DEFAULT 0,
    zero_click_sum REAL NOT NULL DEFAULT 0,
    engagement_sum REAL NOT NULL DEFAULT 0,
    conversion_potential_sum REAL NOT NULL DEFAULT 0,
    authority_sum REAL NOT NULL DEFAULT 0,
    relevance_sum REAL NOT NULL DEFAULT 0,
    clarity_sum REAL NOT NULL DEFAULT 0,
    im_seo_sum REAL NOT NULL DEFAULT 0,
    im_seoia_sum REAL NOT NULL DEFAULT 0,
    citation_rate_observed_sum REAL NOT NULL DEFAULT 0,
    citation_rate_corrected_sum REAL NOT NULL DEFAULT 0,
    metrics_payload TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_geo_daily_metrics_scope
ON geo_daily_metrics (
    project_id,
    metric_date,
    window_days,
    COALESCE(prompt_id, ''),
    COALESCE(prompt_version_id, ''),
    COALESCE(subproject_id, ''),
    COALESCE(llm_model, ''),
    brand_presence
);

CREATE INDEX IF NOT EXISTS ix_geo_daily_metrics_project_date
ON geo_daily_metrics (project_id, metric_date);
