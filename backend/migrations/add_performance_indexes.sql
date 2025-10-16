-- Migration: Add performance indexes for dashboard queries
-- Database: Azure SQL Server
-- Date: 2025-01-16
-- Description: Adiciona índices para otimizar queries do dashboard analytics

-- Índice para filtros por data (usado em todas as queries de analytics)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_runs_started_at' AND object_id = OBJECT_ID('runs'))
BEGIN
    CREATE INDEX idx_runs_started_at ON runs(started_at) 
    WHERE started_at IS NOT NULL;
    PRINT 'Index idx_runs_started_at created successfully';
END
ELSE
    PRINT 'Index idx_runs_started_at already exists';
GO

-- Índice para filtros por subproject_id
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_runs_subproject_id' AND object_id = OBJECT_ID('runs'))
BEGIN
    CREATE INDEX idx_runs_subproject_id ON runs(subproject_id)
    WHERE subproject_id IS NOT NULL;
    PRINT 'Index idx_runs_subproject_id created successfully';
END
ELSE
    PRINT 'Index idx_runs_subproject_id already exists';
GO

-- Índice para JOIN com engines
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_runs_engine_id' AND object_id = OBJECT_ID('runs'))
BEGIN
    CREATE INDEX idx_runs_engine_id ON runs(engine_id);
    PRINT 'Index idx_runs_engine_id created successfully';
END
ELSE
    PRINT 'Index idx_runs_engine_id already exists';
GO

-- Índice composto para queries de analytics com filtro de subproject e data
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_runs_subproject_started' AND object_id = OBJECT_ID('runs'))
BEGIN
    CREATE INDEX idx_runs_subproject_started ON runs(subproject_id, started_at)
    INCLUDE (amr_flag, dcr_flag, zcrs, cost_usd, tokens_total)
    WHERE started_at IS NOT NULL;
    PRINT 'Index idx_runs_subproject_started created successfully';
END
ELSE
    PRINT 'Index idx_runs_subproject_started already exists';
GO

-- Índice para JOIN de citations com runs
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_citations_run_id' AND object_id = OBJECT_ID('citations'))
BEGIN
    CREATE INDEX idx_citations_run_id ON citations(run_id);
    PRINT 'Index idx_citations_run_id created successfully';
END
ELSE
    PRINT 'Index idx_citations_run_id already exists';
GO

-- Índice para agregação de domains em citations
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_citations_domain' AND object_id = OBJECT_ID('citations'))
BEGIN
    CREATE INDEX idx_citations_domain ON citations(domain)
    WHERE domain IS NOT NULL;
    PRINT 'Index idx_citations_domain created successfully';
END
ELSE
    PRINT 'Index idx_citations_domain already exists';
GO

-- Estatísticas para otimização do query planner
UPDATE STATISTICS runs;
UPDATE STATISTICS citations;
UPDATE STATISTICS engines;
PRINT 'Statistics updated successfully';
GO

PRINT 'Performance indexes migration completed successfully!';
