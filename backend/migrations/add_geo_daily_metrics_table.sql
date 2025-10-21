CREATE TABLE geo_daily_metrics (
    id VARCHAR(50) NOT NULL PRIMARY KEY,
    project_id VARCHAR(50) NOT NULL,
    metric_date DATE NOT NULL,
    window_days INT NOT NULL CONSTRAINT df_geo_daily_metrics_window DEFAULT (1),
    prompt_id VARCHAR(50) NULL,
    prompt_version_id VARCHAR(50) NULL,
    subproject_id VARCHAR(50) NULL,
    llm_model NVARCHAR(64) NULL,
    brand_presence NVARCHAR(32) NOT NULL CONSTRAINT df_geo_daily_metrics_brand_presence DEFAULT ('all'),
    runs_total INT NOT NULL CONSTRAINT df_geo_daily_metrics_runs_total DEFAULT (0),
    runs_with_brand INT NOT NULL CONSTRAINT df_geo_daily_metrics_runs_with_brand DEFAULT (0),
    brand_mentions_total INT NOT NULL CONSTRAINT df_geo_daily_metrics_brand_mentions DEFAULT (0),
    exclusive_mentions_total INT NOT NULL CONSTRAINT df_geo_daily_metrics_exclusive DEFAULT (0),
    brand_prominence_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_prominence DEFAULT (0),
    zero_click_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_zero_click DEFAULT (0),
    engagement_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_engagement DEFAULT (0),
    conversion_potential_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_conversion DEFAULT (0),
    authority_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_authority DEFAULT (0),
    relevance_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_relevance DEFAULT (0),
    clarity_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_clarity DEFAULT (0),
    im_seo_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_imseo DEFAULT (0),
    im_seoia_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_imseoia DEFAULT (0),
    citation_rate_observed_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_citation_obs DEFAULT (0),
    citation_rate_corrected_sum FLOAT NOT NULL CONSTRAINT df_geo_daily_metrics_citation_corr DEFAULT (0),
    metrics_payload NVARCHAR(MAX) NOT NULL CONSTRAINT df_geo_daily_metrics_payload DEFAULT ('{}'),
    created_at DATETIME2 NOT NULL CONSTRAINT df_geo_daily_metrics_created DEFAULT (SYSUTCDATETIME()),
    updated_at DATETIME2 NOT NULL CONSTRAINT df_geo_daily_metrics_updated DEFAULT (SYSUTCDATETIME())
);

ALTER TABLE geo_daily_metrics
ADD CONSTRAINT fk_geo_daily_metrics_project
FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;

ALTER TABLE geo_daily_metrics
ADD CONSTRAINT fk_geo_daily_metrics_prompt
FOREIGN KEY (prompt_id) REFERENCES prompts(id);

ALTER TABLE geo_daily_metrics
ADD CONSTRAINT fk_geo_daily_metrics_prompt_version
FOREIGN KEY (prompt_version_id) REFERENCES prompt_versions(id);

ALTER TABLE geo_daily_metrics
ADD CONSTRAINT fk_geo_daily_metrics_subproject
FOREIGN KEY (subproject_id) REFERENCES subprojects(id);

CREATE UNIQUE INDEX uq_geo_daily_metrics_scope
ON geo_daily_metrics (
    project_id,
    metric_date,
    window_days,
    ISNULL(prompt_id, ''),
    ISNULL(prompt_version_id, ''),
    ISNULL(subproject_id, ''),
    ISNULL(llm_model, ''),
    brand_presence
);

CREATE INDEX ix_geo_daily_metrics_project_date
ON geo_daily_metrics (project_id, metric_date);
