# 🧪 PageSpeed Insights - Guia de Testes

## 📊 Como Funciona

O PageSpeed Insights API é chamado **automaticamente** durante o cálculo de métricas IM, mas **apenas quando há uma URL do projeto disponível**.

### **Fluxo de Execução**

```
1. Run é executada
2. Citações são extraídas
3. Sistema verifica se há citações de domínios do projeto
4. Se SIM: Chama PageSpeed API com a URL
5. Se NÃO: Usa valor mock (75.0)
```

---

## ✅ Pré-requisitos para PageSpeed Funcionar

### 1. **Domínios Cadastrados no Projeto**

O projeto precisa ter pelo menos um domínio cadastrado:

```bash
# Cadastrar domínio via API
curl -X POST "http://localhost:8000/api/projects/{project_id}/domains" \
  -H "Content-Type: application/json" \
  -d '{"domain": "seusite.com.br"}'
```

**Ou pelo frontend**: Projects → Seu Projeto → Adicionar Domínio

### 2. **Citações do Projeto na Resposta**

A resposta do Google precisa citar o domínio cadastrado. Exemplo:

```
Query: "Melhor banco digital 2025"
Resposta do Google: "... segundo o Nubank.com.br ..."
                              ↑
                    Citação detectada!
```

### 3. **API Key Configurada** (Opcional mas recomendado)

```bash
# No .env
PAGESPEED_API_KEY=sua_chave_aqui
```

**Sem API Key**: 25,000 requests/dia  
**Com API Key**: 400,000 requests/dia

---

## 🧪 Como Testar

### **Teste 1: Verificar se PageSpeed está configurado**

```bash
docker compose exec backend python -c "
import os
key = os.getenv('PAGESPEED_API_KEY', '')
print(f'API Key: {\"✅ Configurada\" if key else \"❌ Não configurada\"}')
"
```

### **Teste 2: Testar PageSpeed diretamente**

```bash
docker compose exec backend python /app/test_pagespeed.py
```

**Saída esperada**:
```
🧪 Testando PageSpeed Insights API...
   API Key: ✅ Configurada

🔍 Analisando: https://www.google.com

📊 Resultados:
   Performance Score: 53.0
   Core Web Vitals Score: 74.32
   LCP: 6.16s (score: 22.96)
   ...
✅ PageSpeed API funcionando perfeitamente!
```

### **Teste 3: Verificar se uma run tem URL alvo**

```bash
docker compose exec backend python -c "
from app.db.session import SessionLocal
from app.models.models import Run, Citation

db = SessionLocal()
run = db.query(Run).filter(Run.id == 'run_xxx').first()
citations = db.query(Citation).filter(Citation.run_id == run.id, Citation.is_ours == True).all()

if citations:
    print(f'✅ {len(citations)} citações do projeto')
    for c in citations:
        print(f'   - {c.url}')
else:
    print('❌ Nenhuma citação do projeto')
    print('   PageSpeed não será chamado')
db.close()
"
```

### **Teste 4: Criar run e monitorar logs**

```bash
# Terminal 1: Monitorar logs
docker compose logs worker -f | grep -E "(IM_METRICS|PageSpeed)"

# Terminal 2: Criar run pelo frontend
# Aguardar execução

# Logs esperados:
# [IM_METRICS] Buscando Core Web Vitals para URL: https://...
# [IM_METRICS] PageSpeed OK: CWV=74.32
```

---

## 📊 Interpretando os Resultados

### **Cenário 1: Core Web Vitals = 75.0 e LCP/FID/CLS = null**

```json
{
  "core_web_vitals_score": 75.0,
  "lcp_score": null,
  "fid_score": null,
  "cls_score": null
}
```

**Causa**: Valor mock (PageSpeed não foi chamado)

**Motivos possíveis**:
- ❌ Nenhum domínio cadastrado no projeto
- ❌ Nenhuma citação do projeto na resposta
- ❌ Erro ao chamar PageSpeed API

**Solução**: Verificar logs do worker

### **Cenário 2: Core Web Vitals com valores reais**

```json
{
  "core_web_vitals_score": 74.32,
  "lcp_score": 22.96,
  "fid_score": 37.67,
  "cls_score": 100.0
}
```

**Causa**: ✅ PageSpeed funcionou!

**Significado**:
- LCP, FID, CLS têm valores individuais
- Score agregado é calculado
- Dados reais do Google PageSpeed Insights

---

## 🔧 Troubleshooting

### **Problema: Sempre retorna 75.0**

**Diagnóstico**:
```bash
# 1. Verificar domínios do projeto
curl http://localhost:8000/api/projects/{project_id}/domains | jq

# 2. Verificar citações da run
curl http://localhost:8000/api/runs/{run_id}/report | jq '.citations[] | select(.is_ours == true)'

# 3. Verificar logs
docker compose logs worker | grep -A 5 "IM_METRICS"
```

**Soluções**:
1. Cadastrar domínios do projeto
2. Criar queries que resultem em citações do projeto
3. Verificar se PAGESPEED_API_KEY está configurada

### **Problema: Erro ao chamar PageSpeed**

**Logs**:
```
[IM_METRICS] Erro ao buscar Core Web Vitals: ...
```

**Causas comuns**:
- URL inválida ou inacessível
- Timeout da API (60s)
- Limite de requests excedido
- API Key inválida

**Solução**:
```bash
# Testar URL manualmente
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://exemplo.com&key=SUA_KEY"
```

### **Problema: PageSpeed muito lento**

**Causa**: PageSpeed API demora ~10-30 segundos por URL

**Solução**: Normal! O sistema aguarda a resposta. Logs mostram progresso.

---

## 📈 Métricas de Sucesso

### **Bom**
- ✅ 80%+ das runs com citações do projeto têm Core Web Vitals reais
- ✅ PageSpeed responde em < 30s
- ✅ Scores individuais (LCP, FID, CLS) preenchidos

### **Atenção**
- ⚠️ 50-80% das runs com Core Web Vitals reais
- ⚠️ Alguns timeouts ocasionais
- ⚠️ Alguns scores individuais null

### **Problema**
- ❌ < 50% das runs com Core Web Vitals reais
- ❌ Timeouts frequentes
- ❌ Sempre retorna 75.0

---

## 🎯 Próximos Passos

### **Para Melhorar Taxa de Sucesso**

1. **Cadastrar mais domínios** do projeto
2. **Criar queries específicas** que mencionem o projeto
3. **Monitorar logs** para identificar problemas
4. **Aumentar timeout** se necessário (atualmente 60s)

### **Para Otimizar Performance**

1. **Cache de resultados** PageSpeed por URL (24h)
2. **Fila assíncrona** para não bloquear execução
3. **Batch requests** para múltiplas URLs

---

## 📞 Suporte

**Logs úteis**:
```bash
# Worker
docker compose logs worker -f | grep IM_METRICS

# Backend
docker compose logs backend -f | grep PageSpeed
```

**Verificar health**:
```bash
curl http://localhost:8000/health
```

**Testar PageSpeed diretamente**:
```bash
docker compose exec backend python /app/test_pagespeed.py
```
