-- Migration: Add GEO metrics columns to runs table
-- Date: 2025-10-13
-- Description: Adds columns for Generative Engine Optimization metrics

-- Brand Presence Metrics
ALTER TABLE runs ADD brand_mention_count INT NULL;
ALTER TABLE runs ADD brand_first_mention_position FLOAT NULL;
ALTER TABLE runs ADD brand_mention_density FLOAT NULL;
ALTER TABLE runs ADD brand_prominence_score FLOAT NULL;

-- Citation Quality Metrics
ALTER TABLE runs ADD citation_quality_score FLOAT NULL;
ALTER TABLE runs ADD first_citation_position INT NULL;

-- Citation Rate Metrics
ALTER TABLE runs ADD citation_rate_observed FLOAT NULL;
ALTER TABLE runs ADD citation_rate_corrected FLOAT NULL;

-- Competitive Metrics
ALTER TABLE runs ADD competitor_mention_ratio FLOAT NULL;
ALTER TABLE runs ADD share_of_voice_llm FLOAT NULL;
ALTER TABLE runs ADD cocitation_competitors NVARCHAR(MAX) NULL;

-- Engagement Metrics
ALTER TABLE runs ADD conversational_trigger_count INT NULL;
ALTER TABLE runs ADD engagement_score FLOAT NULL;

-- Advanced Metrics
ALTER TABLE runs ADD zero_click_presence FLOAT NULL;
ALTER TABLE runs ADD authority_score FLOAT NULL;
ALTER TABLE runs ADD relevance_score FLOAT NULL;
ALTER TABLE runs ADD clarity_score FLOAT NULL;

-- Product & Conversion
ALTER TABLE runs ADD product_category VARCHAR(100) NULL;
ALTER TABLE runs ADD conversion_potential_score FLOAT NULL;

-- Create indexes for common queries
CREATE INDEX idx_runs_brand_mention_count ON runs(brand_mention_count);
CREATE INDEX idx_runs_engagement_score ON runs(engagement_score);
CREATE INDEX idx_runs_conversion_potential_score ON runs(conversion_potential_score);
CREATE INDEX idx_runs_product_category ON runs(product_category);
