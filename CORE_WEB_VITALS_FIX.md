# 🚀 Correção Core Web Vitals - Fallback para Domínio Primário

**Data:** 2025-10-04 02:36  
**Problema:** Core Web Vitals sempre NULL mesmo com domínio configurado

## 🐛 Problema Identificado

### Comportamento Anterior
O sistema **só** calculava Core Web Vitals quando:
1. A resposta da IA citava o site do projeto
2. Havia uma URL "nossa" nas citações

**Problema:** Se a IA não menciona o site do projeto, não há URL para testar no PageSpeed.

### Exemplo Real
- Projeto: Banco do Brasil
- Domínio configurado: `bb.com.br` ⭐ PRIMARY
- Citações da run: 10 citações, **NENHUMA do BB**
- Resultado: Core Web Vitals = NULL

## ✅ Solução Implementada

### Fallback Inteligente

Agora o sistema usa uma **hierarquia de prioridades** para definir a URL alvo:

1. **Primeira prioridade:** URL de citação "nossa" (comportamento original)
2. **Segunda prioridade:** Domínio PRIMARY do projeto (NOVO)
3. **Terceira prioridade:** Primeiro domínio do projeto (NOVO)

### Código Adicionado

```python
# Se não houver citação nossa, usar domínio primário do projeto como fallback
if not target_url and project_domains:
    primary_domain = db.query(Domain).filter(
        Domain.project_id == project.id,
        Domain.is_primary == True
    ).first()
    if primary_domain:
        target_url = f"https://{primary_domain.domain}"
        print(f"[IM_METRICS] Usando domínio primário como fallback: {target_url}")
    elif project_domains:
        # Se não tiver primário, usar o primeiro domínio
        target_url = f"https://{project_domains[0]}"
        print(f"[IM_METRICS] Usando primeiro domínio como fallback: {target_url}")
```

### Arquivos Modificados

1. ✅ `backend/app/services/tasks.py` - Cálculo em novas runs
2. ✅ `backend/scripts/recalculate_im_metrics.py` - Recálculo de runs antigas

## 📊 Resultado Esperado

### Antes da Correção
```
Core Web Vitals: NULL (sem citação do projeto)
```

### Depois da Correção
```
Core Web Vitals: [valor calculado via PageSpeed]
LCP: [valor]
FID: [valor]  
CLS: [valor]
```

**URL usada:** `https://bb.com.br` (domínio primário)

## 🧪 Como Testar

### 1. Execute uma nova run
- Qualquer projeto com domínio configurado
- Mesmo que a IA não cite o site

### 2. Verifique os logs
Você verá no worker:
```
[IM_METRICS] Usando domínio primário como fallback: https://bb.com.br
[IM_METRICS] Buscando Core Web Vitals para URL: https://bb.com.br
[IM_METRICS] PageSpeed OK: CWV=XX.X
```

### 3. Verifique as métricas
```bash
curl http://129.148.63.199/api/runs/{run_id}/metrics
```

Deve retornar:
```json
{
  "core_web_vitals": {
    "lcp": 2.5,
    "fid": 100,
    "cls": 0.1,
    "score": 85.0
  }
}
```

## 🎯 Benefícios

1. ✅ **Core Web Vitals sempre calculado** quando há domínio configurado
2. ✅ **Não depende** de citação da IA
3. ✅ **Usa domínio primário** como referência padrão
4. ✅ **Mantém prioridade** para URL citada (mais específica)

## 📝 Observações

### Quando Core Web Vitals ainda será NULL

- ❌ Projeto sem domínios configurados
- ❌ Erro na API do PageSpeed (timeout, quota excedida)
- ❌ URL inacessível ou com erro

### Configuração Recomendada

Para melhores resultados:
1. Configure o domínio principal como **PRIMARY**
2. Use URL completa e acessível (https://dominio.com)
3. Certifique-se que o site está online e acessível

## 🚀 Deploy Realizado

1. ✅ Código commitado no branch POC
2. ✅ Arquivo tasks.py copiado para servidor
3. ✅ Worker reiniciado
4. ✅ Pronto para testar

**Execute uma nova run agora para ver Core Web Vitals calculado!** 🎉
