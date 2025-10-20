-- console.sql
-- Consultas para identificar a MAIOR tabela de um schema.
-- 1) Defina o NOME_DO_SCHEMA abaixo conforme seu ambiente.
-- 2) Rode apenas a consulta correspondente ao seu SGBD (PostgreSQL, MySQL/MariaDB, SQL Server ou Oracle).
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
-- Rode no contexto do banco (ex.: USE seu_banco;)
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
-- - Se quiser que eu gere apenas a consulta para um SGBD específico e já com o nome do schema, me informe qual SGBD e o nome do schema.
