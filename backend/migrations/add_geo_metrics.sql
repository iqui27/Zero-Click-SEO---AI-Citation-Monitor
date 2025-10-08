-- ========================================
-- Migração: Adicionar Métricas GEO
-- Data: 2025-10-08
-- Descrição: Campos para Generative Engine Optimization (ChatGPT, Gemini, Perplexity)
-- IMPORTANTE: Estes campos são EXCLUSIVOS para LLMs, NÃO devem ser usados para SERP
-- ========================================

-- ========================================
-- 1. ADICIONAR CAMPOS GEO À TABELA RUNS
-- ========================================

-- GEO - Brand Presence
ALTER TABLE runs ADD COLUMN brand_mention_count INT NULL;
ALTER TABLE runs ADD COLUMN brand_first_mention_position INT NULL;
ALTER TABLE runs ADD COLUMN brand_mention_density FLOAT NULL;
ALTER TABLE runs ADD COLUMN brand_prominence_score FLOAT NULL;

-- GEO - Citation Quality & Rate
ALTER TABLE runs ADD COLUMN citation_quality_score FLOAT NULL;
ALTER TABLE runs ADD COLUMN first_citation_position INT NULL;
ALTER TABLE runs ADD COLUMN citation_rate_observed FLOAT NULL;
ALTER TABLE runs ADD COLUMN citation_rate_corrected FLOAT NULL;

-- GEO - Competitive Intelligence
ALTER TABLE runs ADD COLUMN competitor_mention_ratio FLOAT NULL;
ALTER TABLE runs ADD COLUMN share_of_voice_llm FLOAT NULL;
ALTER TABLE runs ADD COLUMN cocitation_competitors TEXT NULL;

-- GEO - Engagement & Conversion
ALTER TABLE runs ADD COLUMN conversational_trigger_count INT NULL;
ALTER TABLE runs ADD COLUMN engagement_score FLOAT NULL;

-- ========================================
-- 2. CRIAR TABELA DOMAIN_VARIANTS
-- ========================================

CREATE TABLE domain_variants (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50) NOT NULL,
    variant_domain VARCHAR(255) NOT NULL,
    canonical_domain VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_domain_variants_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    
    CONSTRAINT uq_project_variant_domain
        UNIQUE (project_id, variant_domain)
);

CREATE INDEX ix_domain_variants_project_variant ON domain_variants(project_id, variant_domain);

-- ========================================
-- 3. CRIAR TABELA CONTENT_GAPS
-- ========================================

CREATE TABLE content_gaps (
    id VARCHAR(50) PRIMARY KEY,
    project_id VARCHAR(50) NOT NULL,
    url VARCHAR(1000) NULL,
    topic VARCHAR(500) NULL,
    gap_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    suggestion TEXT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    estimated_impact FLOAT NULL,
    assignee VARCHAR(255) NULL,
    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    
    CONSTRAINT fk_content_gaps_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX ix_content_gaps_project_status ON content_gaps(project_id, status);
CREATE INDEX ix_content_gaps_priority ON content_gaps(priority);

-- ========================================
-- 4. COMENTÁRIOS PARA DOCUMENTAÇÃO
-- ========================================

-- Adicionar comentários explicativos (se o banco suportar)
-- SQL Server: USE sys.sp_addextendedproperty
-- PostgreSQL: COMMENT ON COLUMN
-- MySQL: ALTER TABLE ... MODIFY ... COMMENT '...'

-- ========================================
-- 5. SEEDS INICIAIS (OPCIONAL)
-- ========================================

-- Exemplo: Variantes de domínio para Banco do Brasil
-- INSERT INTO domain_variants (id, project_id, variant_domain, canonical_domain, display_name)
-- VALUES 
--     ('dmv_bb1', 'prj_xxx', 'bancodobrasil.com.br', 'bb.com.br', 'Banco do Brasil'),
--     ('dmv_bb2', 'prj_xxx', 'ourocard.com.br', 'bb.com.br', 'Banco do Brasil'),
--     ('dmv_bb3', 'prj_xxx', 'bbseguros.com.br', 'bb.com.br', 'Banco do Brasil');

-- ========================================
-- 6. VALIDAÇÃO PÓS-MIGRAÇÃO
-- ========================================

-- Verificar se todas as colunas foram adicionadas
-- SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'runs' AND COLUMN_NAME LIKE '%geo%' OR COLUMN_NAME LIKE '%brand%';

-- Verificar se as tabelas foram criadas
-- SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('domain_variants', 'content_gaps');

-- ========================================
-- ROLLBACK (SE NECESSÁRIO)
-- ========================================

/*
-- Remover colunas adicionadas
ALTER TABLE runs DROP COLUMN brand_mention_count;
ALTER TABLE runs DROP COLUMN brand_first_mention_position;
ALTER TABLE runs DROP COLUMN brand_mention_density;
ALTER TABLE runs DROP COLUMN brand_prominence_score;
ALTER TABLE runs DROP COLUMN citation_quality_score;
ALTER TABLE runs DROP COLUMN first_citation_position;
ALTER TABLE runs DROP COLUMN citation_rate_observed;
ALTER TABLE runs DROP COLUMN citation_rate_corrected;
ALTER TABLE runs DROP COLUMN competitor_mention_ratio;
ALTER TABLE runs DROP COLUMN share_of_voice_llm;
ALTER TABLE runs DROP COLUMN cocitation_competitors;
ALTER TABLE runs DROP COLUMN conversational_trigger_count;
ALTER TABLE runs DROP COLUMN engagement_score;

-- Remover tabelas criadas
DROP TABLE IF EXISTS content_gaps;
DROP TABLE IF EXISTS domain_variants;
*/
