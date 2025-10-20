-- 1) Encontre a maior tabela (por linhas) no schema 'dbo' - retorna todas ordenadas (use TOP 1 para só a maior)
SELECT
  s.name AS schema_name,
  t.name AS table_name,
  SUM(p.row_count) AS row_count
FROM sys.schemas s
JOIN sys.tables t ON t.schema_id = s.schema_id
JOIN sys.dm_db_partition_stats p ON p.object_id = t.object_id
WHERE p.index_id IN (0,1) -- heap ou índice clusterizado
  AND s.name = 'dbo'
GROUP BY s.name, t.name
ORDER BY SUM(p.row_count) DESC;
-- console.sql
-- Consultas para identificar a MAIOR tabela de um schema.
-- 1) Defina o NOME_DO_SCHEMA abaixo conforme seu ambiente.
-- 2) Rode apenas a consulta correspondente ao seu SGBD (PostgreSQL, MySQL/MariaDB, SQL Server, Azure SQL ou Oracle).
-- 3) "Maior" está disponível por tamanho (dados + índices) e por número de linhas (estimado ou real conforme o SGBD).

-- ======== PostgreSQL (por tamanho: tabela + índices) ========
-- Substitua 'NOME_DO_SCHEMA' pelo schema desejado.
SELECT
  ns.nspname AS schema_name,
  c.relname AS table_name,
  pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
  pg_total_relation_size(c.oid) AS total_size_bytes,
  pg_size_pretty(pg_relation_size(c.oid)) AS table_only_size,
  pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) AS indexes_size,
  c.reltuples::bigint AS estimated_row_count
FROM pg_class c
JOIN pg_namespace ns ON ns.oid = c.relnamespace
WHERE c.relkind = 'r' -- somente tabelas regulares
  AND ns.nspname = 'NOME_DO_SCHEMA'
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 1;

-- ======== PostgreSQL (por número estimado de linhas) ========
SELECT
  ns.nspname AS schema_name,
  c.relname AS table_name,
  c.reltuples::bigint AS estimated_row_count
FROM pg_class c
JOIN pg_namespace ns ON ns.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND ns.nspname = 'NOME_DO_SCHEMA'
ORDER BY c.reltuples DESC
LIMIT 1;

-- ====================
-- Azure SQL / SQL Server: MAIOR tabela por número de linhas (schema = dbo)
-- Observações específicas para Azure SQL:
-- - No Azure SQL Single Database não é possível consultar outra database a partir da conexão atual.
--   Conecte-se diretamente ao banco 'db-ai-geo-hml' no seu cliente (Azure Data Studio, SSMS, Query Editor do portal Azure).
-- - A consulta abaixo usa sys.dm_db_partition_stats.row_count que reflete a contagem de linhas por partição e é adequada para obter o número de linhas por tabela.
-- - Para obter contagens exatas usando COUNT(*) em todas as tabelas, avalie o custo (pode ser lento em tabelas grandes).
-- ====================

-- 1) Encontre a maior tabela (por linhas) no schema 'dbo' - retorna todas ordenadas (use TOP 1 para só a maior)
SELECT
  s.name AS schema_name,
  t.name AS table_name,
  SUM(p.row_count) AS row_count
FROM sys.schemas s
JOIN sys.tables t ON t.schema_id = s.schema_id
JOIN sys.dm_db_partition_stats p ON p.object_id = t.object_id
WHERE p.index_id IN (0,1) -- heap ou índice clusterizado
  AND s.name = 'dbo'
GROUP BY s.name, t.name
ORDER BY SUM(p.row_count) DESC;

-- 2) Só a maior tabela (TOP 1)
SELECT TOP 1
  s.name AS schema_name,
  t.name AS table_name,
  SUM(p.row_count) AS row_count
FROM sys.schemas s
JOIN sys.tables t ON t.schema_id = s.schema_id
JOIN sys.dm_db_partition_stats p ON p.object_id = t.object_id
WHERE p.index_id IN (0,1)
  AND s.name = 'dbo'
GROUP BY s.name, t.name
ORDER BY SUM(p.row_count) DESC;

-- 3) Listar as top N maiores tabelas por linhas (substitua 10 por N)
SELECT TOP 10
  s.name AS schema_name,
  t.name AS table_name,
  SUM(p.row_count) AS row_count
FROM sys.schemas s
JOIN sys.tables t ON t.schema_id = s.schema_id
JOIN sys.dm_db_partition_stats p ON p.object_id = t.object_id
WHERE p.index_id IN (0,1)
  AND s.name = 'dbo'
GROUP BY s.name, t.name
ORDER BY SUM(p.row_count) DESC;

-- 4) Para obter contagem exata de uma tabela específica (custo elevado em tabelas grandes):
-- Substitua schema and table abaixo, por ex: dbo.my_big_table
-- Você geralmente deve rodar isso apenas na(s) tabela(s) candidata(s).
SELECT COUNT(*) AS exact_row_count FROM dbo.SUA_TABELA_AQUI;

-- ====================
-- Notas sobre execução remota / cross-db:
-- - Em Azure SQL Single Database não é permitido usar consultas cross-database como "otherdb.sys.tables" diretamente.
-- - Se precisar automatizar a checagem de múltiplos bancos em Azure, use mecanismos como Elastic Query, Data Factory, ou conecte-se a cada DB separadamente.
-- ====================

-- ======== MySQL / MariaDB (por tamanho: data + indexes) ========
-- Substitua 'NOME_DO_SCHEMA' pelo schema desejado.
SELECT
  table_schema AS schema_name,
  table_name,
  CONCAT(ROUND(((data_length + index_length) / 1024 / 1024), 2), ' MB') AS total_size,
  (data_length + index_length) AS total_bytes,
  table_rows
FROM information_schema.tables
WHERE table_schema = 'NOME_DO_SCHEMA'
ORDER BY (data_length + index_length) DESC
LIMIT 1;

-- ======== MySQL / MariaDB (por número de linhas - note que table_rows pode ser aproximado) ========
SELECT
  table_schema AS schema_name,
  table_name,
  table_rows
FROM information_schema.tables
WHERE table_schema = 'NOME_DO_SCHEMA'
ORDER BY table_rows DESC
LIMIT 1;

-- ======== SQL Server (por tamanho em MB: dados + índices) ========
-- Rode no contexto do banco (ex.: conecte-se ao banco desejado)
SELECT TOP 1
  s.name AS schema_name,
  t.name AS table_name,
  SUM(a.total_pages) * 8.0 / 1024 AS total_size_mb,
  SUM(a.used_pages) * 8.0 / 1024 AS used_size_mb,
  SUM(a.data_pages) * 8.0 / 1024 AS data_size_mb
FROM sys.tables t
JOIN sys.indexes i ON t.object_id = i.object_id
JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE s.name = 'NOME_DO_SCHEMA'
GROUP BY s.name, t.name
ORDER BY total_size_mb DESC;

-- ======== Oracle (por bytes - usa DBA_SEGMENTS se você tiver privilégios) ========
-- Substitua 'NOME_DO_SCHEMA' e rode como usuário com acesso a DBA_SEGMENTS, ou use USER_SEGMENTS para seu próprio schema.
SELECT
  owner AS schema_name,
  segment_name AS table_name,
  SUM(bytes) / 1024 / 1024 AS size_mb
FROM dba_segments
WHERE segment_type = 'TABLE'
  AND owner = 'NOME_DO_SCHEMA'
GROUP BY owner, segment_name
ORDER BY size_mb DESC
FETCH FIRST 1 ROW ONLY;

-- ======== Observações:
-- - Substitua 'NOME_DO_SCHEMA' pelo nome do schema que você quer inspecionar.
-- - Para PostgreSQL, as contagens de linhas (reltuples) são estimativas; rode VACUUM ANALYZE se precisar de estimativas mais recentes.
-- - Para MySQL, table_rows pode ser aproximado dependendo do engine; para InnoDB considere rodar COUNT(*) em tabelas específicas se precisar do número exato (custo elevado).
-- - Em Azure SQL Single DB, conecte-se ao banco alvo para executar as consultas de sys.*; não use cross-db direto.
-- - Se quiser que eu gere apenas a consulta para um SGBD/ schema específico já com os nomes preenchidos, diga qual e eu adapto.


-- ============================
-- AZURE SQL: script para dropar FKs que referenciam tabelas "run-related",
-- gerar statements para recriar com ON DELETE CASCADE e executar a sequência de DELETE.
-- Uso seguro:
-- 1) Conecte-se ao banco alvo (db-ai-geo-hml).
-- 2) Rode a seção "Gerar CREATE..." e salve o output (arquivo) — isso contém os comandos para recriar FKs.
-- 3) Rode a seção "Gerar DROP..." e revise os drops.
-- 4) Se estiver confortável, rode a seção "Executar (opcional)" para dropar, apagar dados (na ordem) e recriar as FKs.
-- IMPORTANTE: Teste em um ambiente de staging antes de rodar em produção.
-- ============================

-- Defina aqui as tabelas alvo (run-related) e o schema (dbo)
DECLARE @target_schema SYSNAME = N'dbo';

-- lista de tabelas relacionadas a run que devem ser alvo de análise
-- ajuste se necessário
DECLARE @target_tables TABLE (name SYSNAME);
INSERT INTO @target_tables (name) VALUES
('runs'),('projects'),('prompt_versions'),('prompts'),('engines'),('domains'),('subprojects');

-- ----------------------------
-- 1) Gerar statements para RECRIAÇÃO (com ON DELETE CASCADE) - SALVE estes antes de dropar
-- ----------------------------
SELECT
  fk.name AS fk_name,
  QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) AS parent_table,
  QUOTENAME(SCHEMA_NAME(tr.schema_id)) + '.' + QUOTENAME(tr.name) AS referenced_table,
  'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name)
    + ' ADD CONSTRAINT ' + QUOTENAME(fk.name) + ' FOREIGN KEY (' 
    + parent_cols.cols + ') REFERENCES ' + QUOTENAME(SCHEMA_NAME(tr.schema_id)) + '.' + QUOTENAME(tr.name) 
    + ' (' + ref_cols.cols + ') ON DELETE CASCADE;' AS create_statement
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
CROSS APPLY (
  SELECT STRING_AGG(QUOTENAME(cp.name), ',') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
  FROM sys.foreign_key_columns fkc
  JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
  WHERE fkc.constraint_object_id = fk.object_id
) parent_cols
CROSS APPLY (
  SELECT STRING_AGG(QUOTENAME(cr.name), ',') WITHIN GROUP (ORDER BY fkc.constraint_column_id) AS cols
  FROM sys.foreign_key_columns fkc
  JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
  WHERE fkc.constraint_object_id = fk.object_id
) ref_cols
WHERE tr.name IN (SELECT name FROM @target_tables)
  AND SCHEMA_NAME(tr.schema_id) = @target_schema
ORDER BY fk.name;

-- ----------------------------
-- 2) Gerar statements para DROP (revise antes de executar)
-- ----------------------------
SELECT
  fk.name AS fk_name,
  QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name) AS parent_table,
  'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name)
    + ' DROP CONSTRAINT ' + QUOTENAME(fk.name) + ';' AS drop_statement
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
WHERE tr.name IN (SELECT name FROM @target_tables)
  AND SCHEMA_NAME(tr.schema_id) = @target_schema
ORDER BY fk.name;

-- ----------------------------
-- 3) Sequência de DELETE (ordem de dependência) - ajuste se necessário
-- Execute manualmente ou use o bloco abaixo (opcional) para executar automaticamente.
-- ----------------------------
-- delete order suggested:
-- run_events, run_semantic_insights, evidences, citations, reasons, entities, serp_features, insights,
-- competitor_scores, runs, prompt_versions, prompts, engines, domains, prompt_templates, monitors, subprojects, projects

-- Comandos de DELETE prontos (substitua ou ajuste se precisar)
-- IMPORTANTE: revise e rode em ambiente de teste primeiro.
-- Você pode rodar todos de uma vez (cuidado), ou apenas os que deseja.
PRINT '-- DELETE commands (review before executing) --';
PRINT 'DELETE FROM dbo.run_events;';
PRINT 'DELETE FROM dbo.run_semantic_insights;';
PRINT 'DELETE FROM dbo.evidences;';
PRINT 'DELETE FROM dbo.citations;';
PRINT 'DELETE FROM dbo.reasons;';
PRINT 'DELETE FROM dbo.entities;';
PRINT 'DELETE FROM dbo.serp_features;';
PRINT 'DELETE FROM dbo.insights;';
PRINT 'DELETE FROM dbo.competitor_scores;';
PRINT 'DELETE FROM dbo.runs;';
PRINT 'DELETE FROM dbo.prompt_versions;';
PRINT 'DELETE FROM dbo.prompts;';
PRINT 'DELETE FROM dbo.engines;';
PRINT 'DELETE FROM dbo.domains;';
PRINT 'DELETE FROM dbo.prompt_templates;';
PRINT 'DELETE FROM dbo.monitors;';
PRINT 'DELETE FROM dbo.subprojects;';
PRINT 'DELETE FROM dbo.projects;';

-- ----------------------------
-- 4) Bloco OPCIONAL: executar DROP FKs -> DELETEs -> RECREATE FKs (comentado por segurança)
-- Use apenas se já salvou os CREATE statements e confirmou os DROP statements.
-- ============================
/*
-- ATENÇÃO: este bloco executa alterações destrutivas. Teste antes.
SET XACT_ABORT ON;
BEGIN TRAN;

-- 4.a) Executar drops (exemplo: executar cada drop_statement gerado anteriormente)
-- Exemplo usando cursor para executar drops automaticamente:
DECLARE drop_cursor CURSOR FOR
SELECT 'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(tp.schema_id)) + '.' + QUOTENAME(tp.name)
       + ' DROP CONSTRAINT ' + QUOTENAME(fk.name) + ';' AS drop_stmt
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
WHERE tr.name IN (SELECT name FROM @target_tables)
  AND SCHEMA_NAME(tr.schema_id) = @target_schema
ORDER BY fk.name;

OPEN drop_cursor;
DECLARE @drop_sql NVARCHAR(MAX);
FETCH NEXT FROM drop_cursor INTO @drop_sql;
WHILE @@FETCH_STATUS = 0
BEGIN
  PRINT 'Executing: ' + @drop_sql;
  EXEC sp_executesql @drop_sql;
  FETCH NEXT FROM drop_cursor INTO @drop_sql;
END
CLOSE drop_cursor;
DEALLOCATE drop_cursor;

-- 4.b) Executar deletes (exemplo: em sequência)
DELETE FROM dbo.run_events;
DELETE FROM dbo.run_semantic_insights;
DELETE FROM dbo.evidences;
DELETE FROM dbo.citations;
DELETE FROM dbo.reasons;
DELETE FROM dbo.entities;
DELETE FROM dbo.serp_features;
DELETE FROM dbo.insights;
DELETE FROM dbo.competitor_scores;
DELETE FROM dbo.runs;
DELETE FROM dbo.prompt_versions;
DELETE FROM dbo.prompts;
DELETE FROM dbo.engines;
DELETE FROM dbo.domains;
DELETE FROM dbo.prompt_templates;
DELETE FROM dbo.monitors;
DELETE FROM dbo.subprojects;
DELETE FROM dbo.projects;

-- 4.c) Recriar FKs com ON DELETE CASCADE (execute os CREATE statements que você salvou na etapa 1)
-- Exemplo: execute cada create_statement salvo
-- Você pode salvar os outputs da etapa 1 em um arquivo e executar aqui com sqlcmd/SSMS.

COMMIT;
*/
-- FIM do bloco opcional
-- ============================
