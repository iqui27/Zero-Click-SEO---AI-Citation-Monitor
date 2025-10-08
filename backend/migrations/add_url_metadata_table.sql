-- Migration: Add url_metadata table for caching crawled URL metadata
-- Date: 2025-01-08

CREATE TABLE url_metadata (
    id VARCHAR(50) PRIMARY KEY,
    url VARCHAR(2048) NOT NULL UNIQUE,
    domain VARCHAR(255) NOT NULL,
    
    -- HTML metadata
    title VARCHAR(1000),
    meta_description VARCHAR(2000),
    meta_keywords VARCHAR(1000),
    meta_robots VARCHAR(500),
    
    -- Open Graph tags (JSON)
    og_tags TEXT,  -- JSON stored as TEXT for Azure SQL compatibility
    
    -- AI Ready detection
    has_structured_data BIT NOT NULL DEFAULT 0,
    has_faq_schema BIT NOT NULL DEFAULT 0,
    has_lists BIT NOT NULL DEFAULT 0,
    has_tables BIT NOT NULL DEFAULT 0,
    
    -- Crawl status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message VARCHAR(1000),
    http_status_code INT,
    
    -- Timestamps
    crawled_at DATETIME2,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
);

-- Indexes
CREATE INDEX ix_url_metadata_url ON url_metadata(url);
CREATE INDEX ix_url_metadata_domain ON url_metadata(domain);
CREATE INDEX ix_url_metadata_domain_status ON url_metadata(domain, status);
