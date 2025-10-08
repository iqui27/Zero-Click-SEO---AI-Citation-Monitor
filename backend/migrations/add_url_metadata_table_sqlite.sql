-- Migration: Add url_metadata table for caching crawled URL metadata (SQLite version)
-- Date: 2025-01-08

CREATE TABLE IF NOT EXISTS url_metadata (
    id VARCHAR(50) PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    domain VARCHAR(255) NOT NULL,
    
    -- HTML metadata
    title TEXT,
    meta_description TEXT,
    meta_keywords TEXT,
    meta_robots TEXT,
    
    -- Open Graph tags (JSON)
    og_tags TEXT,  -- JSON stored as TEXT
    
    -- AI Ready detection
    has_structured_data INTEGER NOT NULL DEFAULT 0,
    has_faq_schema INTEGER NOT NULL DEFAULT 0,
    has_lists INTEGER NOT NULL DEFAULT 0,
    has_tables INTEGER NOT NULL DEFAULT 0,
    
    -- Crawl status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    http_status_code INTEGER,
    
    -- Timestamps
    crawled_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_url_metadata_url ON url_metadata(url);
CREATE INDEX IF NOT EXISTS ix_url_metadata_domain ON url_metadata(domain);
CREATE INDEX IF NOT EXISTS ix_url_metadata_domain_status ON url_metadata(domain, status);
