-- ============================
-- Script: DROPAR TODAS AS TABELAS do schema dbo (db-ai-geo-hml)
-- Ambiente: Azure SQL Database
-- 
-- ⚠️ ATENÇÃO: Este script vai DELETAR PERMANENTEMENTE todas as tabelas do schema dbo!
-- ⚠️ TODOS OS DADOS SERÃO PERDIDOS!
-- ⚠️ NÃO HÁ COMO REVERTER APÓS O COMMIT!
--
-- Este script realiza:
-- 1. Lista todas as Foreign Keys do schema dbo
-- 2. Gera comandos DROP para todas as FKs
-- 3. Gera comandos DROP para todas as tabelas
-- 4. (Opcional) Executa todos os DROPs em uma transação
--
-- ANTES DE EXECUTAR:
-- ✓ Confirme que está no banco correto (db-ai-geo-hml)
-- ✓ Faça backup completo do banco
-- ✓ Teste em ambiente de desenvolvimento primeiro
-- ✓ Confirme com o time que pode dropar TUDO
-- ✓ Documente os schemas das tabelas se precisar recriá-las
-- ============================

-- Conecte-se ao banco: db-ai-geo-hml
SET NOCOUNT ON;

PRINT '╔════════════════════════════════════════════════════════════╗';
PRINT '║  ⚠️  SCRIPT DE DROP DE TODAS AS TABELAS - schema dbo  ⚠️  ║';
PRINT '║                                                            ║';
PRINT '║  Este script vai DELETAR PERMANENTEMENTE:                 ║';
PRINT '║  • Todas as Foreign Keys                                  ║';
PRINT '║  • Todas as Tabelas                                       ║';
PRINT '║  • Todos os Dados                                         ║';
PRINT '╚════════════════════════════════════════════════════════════╝';
PRINT '';

-- ============================
-- SEÇÃO 1: Listar todas as tabelas que serão dropadas
-- ============================
PRINT '=== SEÇÃO 1: Tabelas que serão DROPADAS ===';
PRINT '';

SELECT 
    t.name AS table_name,
    SCHEMA_NAME(t.schema_id) AS schema_name,
    SUM(p.rows) AS approximate_rows
FROM sys.tables t
LEFT JOIN sys.partitions p ON t.object_id = p.object_id
WHERE t.is_ms_shipped = 0
  AND SCHEMA_NAME(t.schema_id) = 'dbo'
  AND p.index_id IN (0, 1)
GROUP BY t.name, t.schema_id
ORDER BY t.name;

DECLARE @table_count INT;
SELECT @table_count = COUNT(*) 
FROM sys.tables t
WHERE t.is_ms_shipped = 0
  AND SCHEMA_NAME(t.schema_id) = 'dbo';

PRINT '';
PRINT 'Total de tabelas que serão dropadas: ' + CAST(@table_count AS VARCHAR);
PRINT '';
PRINT '=== FIM SEÇÃO 1 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 2: Listar todas as Foreign Keys que serão dropadas
-- ============================
PRINT '=== SEÇÃO 2: Foreign Keys que serão DROPADAS ===';
PRINT '';

SELECT 
    fk.name AS fk_name,
    SCHEMA_NAME(tp.schema_id) + '.' + tp.name AS parent_table,
    SCHEMA_NAME(tr.schema_id) + '.' + tr.name AS referenced_table
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
WHERE SCHEMA_NAME(tp.schema_id) = 'dbo'
ORDER BY tp.name, fk.name;

DECLARE @fk_count INT;
SELECT @fk_count = COUNT(*) 
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
WHERE SCHEMA_NAME(tp.schema_id) = 'dbo';

PRINT '';
PRINT 'Total de FKs que serão dropadas: ' + CAST(@fk_count AS VARCHAR);
PRINT '';
PRINT '=== FIM SEÇÃO 2 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 3: Gerar comandos DROP para todas as Foreign Keys
-- ============================
PRINT '=== SEÇÃO 3: Comandos DROP para Foreign Keys ===';
PRINT '';

SELECT 
    fk.name AS fk_name,
    'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) +
    ' DROP CONSTRAINT ' + QUOTENAME(fk.name) + ';' AS drop_fk_statement
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
WHERE SCHEMA_NAME(tp.schema_id) = 'dbo'
ORDER BY tp.name, fk.name;

PRINT '';
PRINT '=== FIM SEÇÃO 3 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 4: Gerar comandos DROP para todas as tabelas
-- ============================
PRINT '=== SEÇÃO 4: Comandos DROP para Tabelas ===';
PRINT '';

SELECT 
    t.name AS table_name,
    'DROP TABLE ' + QUOTENAME(SCHEMA_NAME(t.schema_id)) + '.' + QUOTENAME(t.name) + ';' AS drop_table_statement
FROM sys.tables t
WHERE t.is_ms_shipped = 0
  AND SCHEMA_NAME(t.schema_id) = 'dbo'
ORDER BY t.name;

PRINT '';
PRINT '=== FIM SEÇÃO 4 ===';
PRINT '';
GO

-- ============================
-- SEÇÃO 5 (OPCIONAL): Executar todos os DROPs
-- ⚠️ DESCOMENTE ESTE BLOCO APENAS SE TIVER CERTEZA ABSOLUTA
-- ⚠️ TODOS OS DADOS SERÃO PERDIDOS PERMANENTEMENTE
-- ============================
/*
PRINT '=== SEÇÃO 5: EXECUTANDO DROPS (IRREVERSÍVEL!) ===';
PRINT '';

-- Confirmação adicional
DECLARE @confirmation VARCHAR(100);
PRINT '╔════════════════════════════════════════════════════════════╗';
PRINT '║                    ⚠️  ÚLTIMA CHANCE  ⚠️                    ║';
PRINT '║                                                            ║';
PRINT '║  Você está prestes a DROPAR TODAS AS TABELAS!             ║';
PRINT '║  Esta ação é IRREVERSÍVEL!                                ║';
PRINT '║                                                            ║';
PRINT '║  Se tiver certeza, descomente este bloco e execute.       ║';
PRINT '╚════════════════════════════════════════════════════════════╝';
PRINT '';

SET XACT_ABORT ON;
BEGIN TRANSACTION DropAllTables;

BEGIN TRY
    PRINT 'Iniciando processo de DROP...';
    PRINT '';

    -- Passo 1: Dropar todas as Foreign Keys
    PRINT 'Passo 1: Dropando Foreign Keys...';

    DECLARE @drop_fk_sql NVARCHAR(MAX);
    DECLARE fk_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT 
        'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) +
        ' DROP CONSTRAINT ' + QUOTENAME(fk.name) + ';'
    FROM sys.foreign_keys fk
    JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
    WHERE SCHEMA_NAME(tp.schema_id) = 'dbo'
    ORDER BY tp.name, fk.name;

    OPEN fk_cursor;
    FETCH NEXT FROM fk_cursor INTO @drop_fk_sql;

    DECLARE @fk_dropped INT = 0;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        PRINT '  Executando: ' + @drop_fk_sql;
        EXEC sp_executesql @drop_fk_sql;
        SET @fk_dropped = @fk_dropped + 1;
        FETCH NEXT FROM fk_cursor INTO @drop_fk_sql;
    END

    CLOSE fk_cursor;
    DEALLOCATE fk_cursor;

    PRINT '';
    PRINT 'Foreign Keys dropadas: ' + CAST(@fk_dropped AS VARCHAR);
    PRINT '';

    -- Passo 2: Dropar todas as tabelas
    PRINT 'Passo 2: Dropando Tabelas...';

    DECLARE @drop_table_sql NVARCHAR(MAX);
    DECLARE table_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT 
        'DROP TABLE ' + QUOTENAME(SCHEMA_NAME(t.schema_id)) + '.' + QUOTENAME(t.name) + ';'
    FROM sys.tables t
    WHERE t.is_ms_shipped = 0
      AND SCHEMA_NAME(t.schema_id) = 'dbo'
    ORDER BY t.name;

    OPEN table_cursor;
    FETCH NEXT FROM table_cursor INTO @drop_table_sql;

    DECLARE @tables_dropped INT = 0;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        PRINT '  Executando: ' + @drop_table_sql;
        EXEC sp_executesql @drop_table_sql;
        SET @tables_dropped = @tables_dropped + 1;
        FETCH NEXT FROM table_cursor INTO @drop_table_sql;
    END

    CLOSE table_cursor;
    DEALLOCATE table_cursor;

    PRINT '';
    PRINT 'Tabelas dropadas: ' + CAST(@tables_dropped AS VARCHAR);
    PRINT '';

    -- Commit da transação
    PRINT '╔════════════════════════════════════════════════════════════╗';
    PRINT '║  Commitando transação...                                  ║';
    PRINT '╚════════════════════════════════════════════════════════════╝';

    COMMIT TRANSACTION DropAllTables;

    PRINT '';
    PRINT '✓ SUCESSO: Todas as tabelas foram dropadas!';
    PRINT '';
    PRINT 'Resumo:';
    PRINT '  • Foreign Keys dropadas: ' + CAST(@fk_dropped AS VARCHAR);
    PRINT '  • Tabelas dropadas: ' + CAST(@tables_dropped AS VARCHAR);
    PRINT '';

END TRY
BEGIN CATCH
    PRINT '';
    PRINT '╔════════════════════════════════════════════════════════════╗';
    PRINT '║  ❌ ERRO DETECTADO! Fazendo ROLLBACK...                   ║';
    PRINT '╚════════════════════════════════════════════════════════════╝';
    PRINT '';
    PRINT 'Erro: ' + ERROR_MESSAGE();
    PRINT 'Linha: ' + CAST(ERROR_LINE() AS VARCHAR);
    PRINT '';

    IF @@TRANCOUNT > 0
    BEGIN
        ROLLBACK TRANSACTION DropAllTables;
        PRINT 'Transação revertida. Nenhuma tabela foi dropada.';
    END
END CATCH;

PRINT '';
PRINT '=== FIM SEÇÃO 5 ===';
*/
GO

-- ============================
-- Verificação final: Listar tabelas restantes
-- ============================
PRINT '=== Verificação: Tabelas existentes no schema dbo ===';
PRINT '';

SELECT 
    t.name AS table_name,
    SCHEMA_NAME(t.schema_id) AS schema_name
FROM sys.tables t
WHERE t.is_ms_shipped = 0
  AND SCHEMA_NAME(t.schema_id) = 'dbo'
ORDER BY t.name;

DECLARE @remaining_tables INT;
SELECT @remaining_tables = COUNT(*) 
FROM sys.tables t
WHERE t.is_ms_shipped = 0
  AND SCHEMA_NAME(t.schema_id) = 'dbo';

PRINT '';
PRINT 'Total de tabelas restantes: ' + CAST(@remaining_tables AS VARCHAR);
PRINT '';

-- ============================
-- FIM DO SCRIPT
-- ============================
PRINT '';
PRINT '=================================================';
PRINT 'Script de DROP carregado com sucesso.';
PRINT '';
PRINT 'Para executar:';
PRINT '  1. SEÇÃO 1: Ver tabelas que serão dropadas';
PRINT '  2. SEÇÃO 2: Ver FKs que serão dropadas';
PRINT '  3. SEÇÃO 3: Gerar comandos DROP para FKs';
PRINT '  4. SEÇÃO 4: Gerar comandos DROP para tabelas';
PRINT '  5. SEÇÃO 5: Executar tudo (DESCOMENTE PRIMEIRO)';
PRINT '';
PRINT '⚠️  LEMBRE-SE: Faça backup antes de executar!';
PRINT '=================================================';
PRINT '';
