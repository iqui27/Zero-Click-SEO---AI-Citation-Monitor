-- ============================
-- Script: Limpeza de tabelas relacionadas a RUNS no schema dbo (db-ai-geo-hml)
-- Ambiente: Azure SQL Database
-- 
-- Este script realiza:
-- 1. Lista todas as FKs que referenciam tabelas run-related
-- 2. Gera comandos CREATE para recriar FKs com ON DELETE CASCADE (SALVE ESTES ANTES DE DROPAR!)
-- 3. Gera comandos DROP para remover as FKs temporariamente
-- 4. Executa DELETEs na ordem correta de dependência
-- 5. (Opcional) Recria as FKs com ON DELETE CASCADE
--
-- IMPORTANTE:
-- - Teste este script em ambiente de staging/desenvolvimento ANTES de produção
-- - Execute seção por seção e revise os resultados
-- - Salve os CREATE statements antes de dropar as FKs
-- - Considere fazer backup do banco antes de executar
-- ============================

-- Conecte-se ao banco: db-ai-geo-hml
-- USE [db-ai-geo-hml]; -- Não suportado em Azure SQL Single DB, conecte-se diretamente ao banco

SET NOCOUNT ON;

-- ============================
-- SEÇÃO 1: Listar FKs que referenciam tabelas run-related
-- ============================
PRINT '=== SEÇÃO 1: FKs que referenciam tabelas run-related ===';
PRINT '';

SELECT 
    fk.name AS fk_constraint_name,
    SCHEMA_NAME(tp.schema_id) + '.' + tp.name AS parent_table,
    SCHEMA_NAME(tr.schema_id) + '.' + tr.name AS referenced_table,
    parent_cols.cols AS parent_columns,
    ref_cols.cols AS referenced_columns
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
CROSS APPLY (
    SELECT STRING_AGG(cp.name, ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
    FROM sys.foreign_key_columns fkc
    JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
    WHERE fkc.constraint_object_id = fk.object_id
) parent_cols
CROSS APPLY (
    SELECT STRING_AGG(cr.name, ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
    FROM sys.foreign_key_columns fkc
    JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
    WHERE fkc.constraint_object_id = fk.object_id
) ref_cols
WHERE tr.name IN ('runs','projects','prompt_versions','prompts','engines','domains','subprojects')
  AND SCHEMA_NAME(tr.schema_id) = 'dbo'
ORDER BY parent_table, fk.name;

PRINT '';
PRINT '=== FIM SEÇÃO 1 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 2: Gerar comandos CREATE para recriar FKs com ON DELETE CASCADE
-- ** SALVE ESTE OUTPUT EM UM ARQUIVO ANTES DE DROPAR AS FKs **
-- ============================
PRINT '=== SEÇÃO 2: Comandos CREATE para recriar FKs com ON DELETE CASCADE ===';
PRINT '** SALVE ESTE OUTPUT ANTES DE PROSSEGUIR **';
PRINT '';

SELECT 
    fk.name AS fk_constraint_name,
    'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) +
    ' ADD CONSTRAINT ' + QUOTENAME(fk.name) + 
    ' FOREIGN KEY (' + parent_cols.cols + ')' +
    ' REFERENCES ' + QUOTENAME(SCHEMA_NAME(tr.schema_id)) + '.' + QUOTENAME(tr.name) + 
    ' (' + ref_cols.cols + ')' +
    ' ON DELETE CASCADE;' AS create_fk_statement
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
CROSS APPLY (
    SELECT STRING_AGG(QUOTENAME(cp.name), ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
    FROM sys.foreign_key_columns fkc
    JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
    WHERE fkc.constraint_object_id = fk.object_id
) parent_cols
CROSS APPLY (
    SELECT STRING_AGG(QUOTENAME(cr.name), ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
    FROM sys.foreign_key_columns fkc
    JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
    WHERE fkc.constraint_object_id = fk.object_id
) ref_cols
WHERE tr.name IN ('runs','projects','prompt_versions','prompts','engines','domains','subprojects')
  AND SCHEMA_NAME(tr.schema_id) = 'dbo'
ORDER BY tp.name, fk.name;

PRINT '';
PRINT '=== FIM SEÇÃO 2 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 3: Gerar comandos DROP para remover as FKs
-- Revise antes de executar
-- ============================
PRINT '=== SEÇÃO 3: Comandos DROP para remover FKs ===';
PRINT '';

SELECT 
    fk.name AS fk_constraint_name,
    'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) +
    ' DROP CONSTRAINT ' + QUOTENAME(fk.name) + ';' AS drop_fk_statement
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
WHERE tr.name IN ('runs','projects','prompt_versions','prompts','engines','domains','subprojects')
  AND SCHEMA_NAME(tr.schema_id) = 'dbo'
ORDER BY tp.name, fk.name;

PRINT '';
PRINT '=== FIM SEÇÃO 3 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 4: Sequência de DELETEs (ordem de dependência)
-- Comandos prontos para executar após dropar as FKs
-- ============================
PRINT '=== SEÇÃO 4: Sequência de DELETEs ===';
PRINT 'Ordem sugerida baseada nas dependências entre tabelas:';
PRINT '';
PRINT 'DELETE FROM dbo.run_events;';
PRINT 'DELETE FROM dbo.run_semantic_insights;';
PRINT 'DELETE FROM dbo.evidences;';
PRINT 'DELETE FROM dbo.citations;';
PRINT 'DELETE FROM dbo.reasons;';
PRINT 'DELETE FROM dbo.entities;';
PRINT 'DELETE FROM dbo.serp_features;';
PRINT 'DELETE FROM dbo.insights;';
PRINT 'DELETE FROM dbo.competitor_scores;';
PRINT 'DELETE FROM dbo.content_gaps;';
PRINT 'DELETE FROM dbo.domain_variants;';
PRINT 'DELETE FROM dbo.url_metadata;';
PRINT 'DELETE FROM dbo.monitor_history;';
PRINT 'DELETE FROM dbo.monitor_history_runs;';
PRINT 'DELETE FROM dbo.runs;';
PRINT 'DELETE FROM dbo.prompt_versions;';
PRINT 'DELETE FROM dbo.prompts;';
PRINT 'DELETE FROM dbo.engines;';
PRINT 'DELETE FROM dbo.domains;';
PRINT 'DELETE FROM dbo.prompt_templates;';
PRINT 'DELETE FROM dbo.monitor_templates;';
PRINT 'DELETE FROM dbo.monitors;';
PRINT 'DELETE FROM dbo.subprojects;';
PRINT 'DELETE FROM dbo.projects;';
PRINT '';
PRINT '=== FIM SEÇÃO 4 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 5 (OPCIONAL): Executar DROP + DELETE + CREATE em uma transação
-- ATENÇÃO: Descomente este bloco APENAS se:
-- 1. Você salvou os CREATE statements da SEÇÃO 2
-- 2. Você revisou os DROP statements da SEÇÃO 3
-- 3. Você testou em ambiente de desenvolvimento/staging
-- 4. Você tem backup do banco
-- ============================
/*
PRINT '=== SEÇÃO 5: Executando DROP, DELETE e CREATE (TRANSAÇÃO) ===';
PRINT 'ATENÇÃO: Este bloco fará alterações permanentes no banco!';
PRINT '';

SET XACT_ABORT ON;
BEGIN TRANSACTION CleanupRunTables;

BEGIN TRY
    PRINT 'Passo 1: Dropando FKs...';

    -- Cursor para executar todos os DROPs dinamicamente
    DECLARE @drop_sql NVARCHAR(MAX);
    DECLARE drop_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT 
        'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) +
        ' DROP CONSTRAINT ' + QUOTENAME(fk.name) + ';'
    FROM sys.foreign_keys fk
    JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
    JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
    WHERE tr.name IN ('runs','projects','prompt_versions','prompts','engines','domains','subprojects')
      AND SCHEMA_NAME(tr.schema_id) = 'dbo'
    ORDER BY tp.name, fk.name;

    OPEN drop_cursor;
    FETCH NEXT FROM drop_cursor INTO @drop_sql;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        PRINT '  Executando: ' + @drop_sql;
        EXEC sp_executesql @drop_sql;
        FETCH NEXT FROM drop_cursor INTO @drop_sql;
    END

    CLOSE drop_cursor;
    DEALLOCATE drop_cursor;

    PRINT 'FKs dropadas com sucesso.';
    PRINT '';

    -- Passo 2: Executar DELETEs na ordem de dependência
    PRINT 'Passo 2: Deletando dados...';

    DELETE FROM dbo.run_events;
    PRINT '  Deletado de dbo.run_events: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.run_semantic_insights;
    PRINT '  Deletado de dbo.run_semantic_insights: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.evidences;
    PRINT '  Deletado de dbo.evidences: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.citations;
    PRINT '  Deletado de dbo.citations: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.reasons;
    PRINT '  Deletado de dbo.reasons: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.entities;
    PRINT '  Deletado de dbo.entities: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.serp_features;
    PRINT '  Deletado de dbo.serp_features: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.insights;
    PRINT '  Deletado de dbo.insights: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.competitor_scores;
    PRINT '  Deletado de dbo.competitor_scores: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.content_gaps;
    PRINT '  Deletado de dbo.content_gaps: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.domain_variants;
    PRINT '  Deletado de dbo.domain_variants: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.url_metadata;
    PRINT '  Deletado de dbo.url_metadata: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.monitor_history;
    PRINT '  Deletado de dbo.monitor_history: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.monitor_history_runs;
    PRINT '  Deletado de dbo.monitor_history_runs: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.runs;
    PRINT '  Deletado de dbo.runs: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.prompt_versions;
    PRINT '  Deletado de dbo.prompt_versions: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.prompts;
    PRINT '  Deletado de dbo.prompts: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.engines;
    PRINT '  Deletado de dbo.engines: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.domains;
    PRINT '  Deletado de dbo.domains: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.prompt_templates;
    PRINT '  Deletado de dbo.prompt_templates: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.monitor_templates;
    PRINT '  Deletado de dbo.monitor_templates: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.monitors;
    PRINT '  Deletado de dbo.monitors: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.subprojects;
    PRINT '  Deletado de dbo.subprojects: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    DELETE FROM dbo.projects;
    PRINT '  Deletado de dbo.projects: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' linhas';

    PRINT 'Dados deletados com sucesso.';
    PRINT '';

    -- Passo 3: Recriar FKs com ON DELETE CASCADE
    PRINT 'Passo 3: Recriando FKs com ON DELETE CASCADE...';

    DECLARE @create_sql NVARCHAR(MAX);
    DECLARE create_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT 
        'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) +
        ' ADD CONSTRAINT ' + QUOTENAME(fk.name) + 
        ' FOREIGN KEY (' + parent_cols.cols + ')' +
        ' REFERENCES ' + QUOTENAME(SCHEMA_NAME(tr.schema_id)) + '.' + QUOTENAME(tr.name) + 
        ' (' + ref_cols.cols + ')' +
        ' ON DELETE CASCADE;'
    FROM sys.foreign_keys fk
    JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
    JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
    CROSS APPLY (
        SELECT STRING_AGG(QUOTENAME(cp.name), ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
        FROM sys.foreign_key_columns fkc
        JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
        WHERE fkc.constraint_object_id = fk.object_id
    ) parent_cols
    CROSS APPLY (
        SELECT STRING_AGG(QUOTENAME(cr.name), ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
        FROM sys.foreign_key_columns fkc
        JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
        WHERE fkc.constraint_object_id = fk.object_id
    ) ref_cols
    WHERE tr.name IN ('runs','projects','prompt_versions','prompts','engines','domains','subprojects')
      AND SCHEMA_NAME(tr.schema_id) = 'dbo'
    ORDER BY tp.name, fk.name;

    -- Nota: Este cursor tentará recriar FKs que foram dropadas.
    -- Como as FKs já foram dropadas, sys.foreign_keys não as conterá mais.
    -- Você DEVE usar os CREATE statements salvos na SEÇÃO 2!
    -- Por isso, este cursor NÃO funcionará aqui - use os statements salvos manualmente.

    CLOSE create_cursor;
    DEALLOCATE create_cursor;

    PRINT 'AVISO: Para recriar as FKs, você DEVE executar os CREATE statements';
    PRINT 'que foram salvos na SEÇÃO 2. Eles não podem ser gerados aqui porque';
    PRINT 'as FKs já foram dropadas.';
    PRINT '';
    PRINT 'Execute os CREATE statements salvos manualmente após o COMMIT desta transação.';
    PRINT '';

    -- Commit da transação
    PRINT 'Commitando transação...';
    COMMIT TRANSACTION CleanupRunTables;
    PRINT 'Transação commitada com sucesso!';
    PRINT '';
    PRINT 'PRÓXIMO PASSO: Execute os CREATE statements que você salvou da SEÇÃO 2.';

END TRY
BEGIN CATCH
    PRINT 'ERRO detectado! Fazendo ROLLBACK...';
    PRINT 'Erro: ' + ERROR_MESSAGE();
    ROLLBACK TRANSACTION CleanupRunTables;
    PRINT 'Transação revertida. Nenhuma alteração foi aplicada.';
END CATCH;

PRINT '';
PRINT '=== FIM SEÇÃO 5 ===';
*/
GO

-- ============================
-- FIM DO SCRIPT
-- ============================
PRINT '';
PRINT '=================================================';
PRINT 'Script de limpeza carregado com sucesso.';
PRINT 'Execute cada seção conforme necessário:';
PRINT '  1. SEÇÃO 1: Listar FKs';
PRINT '  2. SEÇÃO 2: Gerar CREATE statements (SALVE!)';
PRINT '  3. SEÇÃO 3: Gerar DROP statements';
PRINT '  4. SEÇÃO 4: Ver sequência de DELETEs';
PRINT '  5. SEÇÃO 5: Executar tudo (OPCIONAL, descomente)';
PRINT '=================================================';
PRINT '';
