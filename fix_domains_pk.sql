-- ============================
-- Script: Adicionar PRIMARY KEY à tabela domains
-- ============================

-- Ver estrutura atual da tabela domains
SELECT 
    c.name AS column_name,
    t.name AS data_type,
    c.max_length,
    c.is_nullable,
    CASE WHEN pk.column_id IS NOT NULL THEN 'YES' ELSE 'NO' END AS is_primary_key
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
LEFT JOIN (
    SELECT ic.object_id, ic.column_id
    FROM sys.index_columns ic
    JOIN sys.indexes i ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 1
) pk ON c.object_id = pk.object_id AND c.column_id = pk.column_id
WHERE c.object_id = OBJECT_ID('dbo.domains')
ORDER BY c.column_id;

-- Ver se já existe PRIMARY KEY
SELECT 
    i.name AS constraint_name,
    c.name AS column_name
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.object_id = OBJECT_ID('dbo.domains')
  AND i.is_primary_key = 1;

-- ============================
-- Opção 1: Se a coluna 'id' já existe mas não é PK
-- ============================
-- Verificar se há valores duplicados ou NULL antes de adicionar PK
SELECT domain, COUNT(*) as count
FROM dbo.domains
GROUP BY domain
HAVING COUNT(*) > 1;

-- Se 'domain' é a coluna que deve ser PK (ajuste se necessário)
-- Primeiro, certifique-se que não há NULLs ou duplicados
UPDATE dbo.domains SET domain = NEWID() WHERE domain IS NULL;

-- Adicionar PRIMARY KEY na coluna existente
ALTER TABLE dbo.domains
ADD CONSTRAINT pk_domains PRIMARY KEY (domain);

-- ============================
-- Opção 2: Se você quer criar uma nova coluna 'id'
-- ============================
/*
-- Adicionar coluna id se não existir
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.domains') AND name = 'id')
BEGIN
    ALTER TABLE dbo.domains ADD id VARCHAR(255) NULL;

    -- Copiar valores da coluna domain para id (ou gerar novos IDs)
    UPDATE dbo.domains SET id = domain; -- ou use NEWID() se quiser GUIDs

    -- Tornar NOT NULL
    ALTER TABLE dbo.domains ALTER COLUMN id VARCHAR(255) NOT NULL;

    -- Adicionar PRIMARY KEY
    ALTER TABLE dbo.domains ADD CONSTRAINT pk_domains PRIMARY KEY (id);
END
*/

-- ============================
-- Opção 3: Se 'domain' deve ser renomeada para 'id'
-- ============================
/*
-- Renomear coluna (SQL Server não suporta RENAME COLUMN diretamente)
EXEC sp_rename 'dbo.domains.domain', 'id', 'COLUMN';

-- Adicionar PRIMARY KEY
ALTER TABLE dbo.domains
ADD CONSTRAINT pk_domains PRIMARY KEY (id);
*/

-- Verificar resultado
SELECT 
    i.name AS constraint_name,
    c.name AS column_name,
    i.is_primary_key
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.object_id = OBJECT_ID('dbo.domains')
  AND i.is_primary_key = 1;

PRINT 'PRIMARY KEY adicionada com sucesso à tabela domains!';
