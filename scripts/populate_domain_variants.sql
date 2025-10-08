-- Script SQL para popular domain_variants com dados reais
-- Substitua 'prj_xxx' pelo ID real do projeto

-- Banco do Brasil
INSERT INTO domain_variants (id, project_id, variant_domain, canonical_domain, is_active, created_at)
VALUES 
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'bancodobrasil.com.br', 'bb.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'bb.com', 'bb.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'ourocard.com.br', 'bb.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'ourocard.com', 'bb.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'bbseguros.com.br', 'bb.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'atendimento.bb.com.br', 'bb.com.br', 1, datetime('now'))
ON CONFLICT DO NOTHING;

-- Nubank (concorrente)
INSERT INTO domain_variants (id, project_id, variant_domain, canonical_domain, is_active, created_at)
VALUES 
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'nu.com.br', 'nubank.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'nubank.com', 'nubank.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'nuconta.com.br', 'nubank.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'nuinvest.com.br', 'nubank.com.br', 1, datetime('now'))
ON CONFLICT DO NOTHING;

-- Itaú (concorrente)
INSERT INTO domain_variants (id, project_id, variant_domain, canonical_domain, is_active, created_at)
VALUES 
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'itau.com', 'itau.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'itaucard.com.br', 'itau.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'itauempresarial.com.br', 'itau.com.br', 1, datetime('now'))
ON CONFLICT DO NOTHING;

-- Bradesco (concorrente)
INSERT INTO domain_variants (id, project_id, variant_domain, canonical_domain, is_active, created_at)
VALUES 
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'bradesco.com', 'bradesco.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'bradescocard.com.br', 'bradesco.com.br', 1, datetime('now'))
ON CONFLICT DO NOTHING;

-- Santander (concorrente)
INSERT INTO domain_variants (id, project_id, variant_domain, canonical_domain, is_active, created_at)
VALUES 
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'santander.com', 'santander.com.br', 1, datetime('now')),
    ('dv_' || substr(md5(random()::text), 1, 8), 'prj_xxx', 'santandercard.com.br', 'santander.com.br', 1, datetime('now'))
ON CONFLICT DO NOTHING;

-- Verificar inserções
SELECT 
    canonical_domain,
    COUNT(*) as variant_count
FROM domain_variants
WHERE project_id = 'prj_xxx'
GROUP BY canonical_domain
ORDER BY variant_count DESC;
