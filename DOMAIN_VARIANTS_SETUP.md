# 🔗 Domain Variants - Guia de Configuração

## O que são Domain Variants?

Domain Variants são variações de domínio que devem ser consolidadas como sendo do mesmo proprietário. Isso permite calcular o **Citation Rate Corrected** de forma mais precisa.

**Exemplo:**
- Domínio canônico: `bb.com.br`
- Variantes: `bancodobrasil.com.br`, `ourocard.com.br`, `bbseguros.com.br`

Quando uma citação menciona `ourocard.com.br`, ela é contabilizada como citação do Banco do Brasil.

---

## 📊 Impacto nas Métricas GEO

### Antes (sem variantes):
```
Citation Rate Observed: 25%  (apenas bb.com.br)
Citation Rate Corrected: 25%  (igual ao observado)
```

### Depois (com variantes):
```
Citation Rate Observed: 25%  (apenas bb.com.br)
Citation Rate Corrected: 38%  (bb.com.br + ourocard + bbseguros)
Fator de Correção: +52%
```

---

## 🚀 Como Popular Domain Variants

### **Opção 1: Via API (Recomendado)**

Endpoint bulk para popular automaticamente:

```bash
# Banco do Brasil
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=bb.com.br"

# Nubank
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=nubank.com.br"

# Itaú
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=itau.com.br"

# Bradesco
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=bradesco.com.br"

# Santander
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=santander.com.br"
```

**Resposta:**
```json
{
  "canonical_domain": "bb.com.br",
  "added_count": 6,
  "skipped_count": 0,
  "added": [
    "bancodobrasil.com.br",
    "bb.com",
    "ourocard.com.br",
    "ourocard.com",
    "bbseguros.com.br",
    "atendimento.bb.com.br"
  ],
  "skipped": []
}
```

---

### **Opção 2: Via Script Python**

```bash
cd /Users/hrocha/Documents/Projetos/SEO\ Analyzer

# Listar domínios disponíveis
python scripts/populate_domain_variants.py --list

# Popular para um projeto
python scripts/populate_domain_variants.py \
  --project-id prj_xxx \
  --domain bb.com.br
```

---

### **Opção 3: Via SQL Direto**

```bash
# Editar o arquivo SQL primeiro (substituir prj_xxx pelo ID real)
nano scripts/populate_domain_variants.sql

# Executar no SQLite
sqlite3 backend/seo_monitor.db < scripts/populate_domain_variants.sql
```

---

## 📋 Domínios Suportados

| Banco | Domínio Canônico | Variantes |
|-------|------------------|-----------|
| **Banco do Brasil** | `bb.com.br` | 6 variantes |
| **Nubank** | `nubank.com.br` | 4 variantes |
| **Itaú** | `itau.com.br` | 3 variantes |
| **Bradesco** | `bradesco.com.br` | 2 variantes |
| **Santander** | `santander.com.br` | 2 variantes |
| **Caixa** | `caixa.gov.br` | 2 variantes |
| **Banco Inter** | `bancointer.com.br` | 2 variantes |
| **C6 Bank** | `c6bank.com.br` | 2 variantes |
| **PagBank** | `pagbank.com.br` | 2 variantes |

---

## 🔍 Verificar Variantes Configuradas

```bash
# Listar todas as variantes do projeto
curl "http://localhost:8000/api/projects/prj_xxx/domain-variants" | jq

# Ver agrupadas por domínio canônico
curl "http://localhost:8000/api/projects/prj_xxx/domain-variants" | \
  jq 'group_by(.canonical_domain) | map({canonical: .[0].canonical_domain, count: length})'
```

---

## ➕ Adicionar Variante Manual

Se precisar adicionar uma variante que não está no mapeamento:

```bash
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants" \
  -H "Content-Type: application/json" \
  -d '{
    "variant_domain": "meudominio.com.br",
    "canonical_domain": "bb.com.br",
    "is_active": true
  }'
```

---

## 🗑️ Remover Variante

```bash
curl -X DELETE "http://localhost:8000/api/projects/prj_xxx/domain-variants/dv_abc123"
```

---

## 📈 Ver Impacto nas Métricas

Após popular as variantes, os próximos runs calcularão automaticamente o `citation_rate_corrected`:

```bash
curl "http://localhost:8000/api/runs/run_xxx" | jq '{
  citation_rate_observed,
  citation_rate_corrected,
  improvement: ((.citation_rate_corrected - .citation_rate_observed) / .citation_rate_observed * 100)
}'
```

**Exemplo de resultado:**
```json
{
  "citation_rate_observed": 25.5,
  "citation_rate_corrected": 38.2,
  "improvement": 49.8
}
```

---

## 🎯 Recomendação

**Para o projeto Banco do Brasil:**

```bash
# 1. Popular variantes do BB
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=bb.com.br"

# 2. Popular variantes dos concorrentes (para análise competitiva)
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=nubank.com.br"
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=itau.com.br"
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=bradesco.com.br"
curl -X POST "http://localhost:8000/api/projects/prj_xxx/domain-variants/bulk?canonical_domain=santander.com.br"

# 3. Verificar
curl "http://localhost:8000/api/projects/prj_xxx/domain-variants" | jq 'length'
# Deve retornar ~19 variantes
```

---

## ✅ Checklist

- [ ] Identificar ID do projeto (`prj_xxx`)
- [ ] Popular variantes do domínio principal
- [ ] Popular variantes dos concorrentes (opcional)
- [ ] Verificar variantes criadas
- [ ] Criar novo run para testar
- [ ] Verificar `citation_rate_corrected` > `citation_rate_observed`

---

**Última atualização:** 2025-10-08  
**Versão:** GEO v1.0 - Domain Variants
