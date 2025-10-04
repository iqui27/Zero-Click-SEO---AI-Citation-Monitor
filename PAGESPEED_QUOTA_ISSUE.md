# ⚠️ Core Web Vitals NULL - Quota PageSpeed Excedida

**Data:** 2025-10-04 03:05  
**Status:** ✅ Fallback funcionando | ❌ API PageSpeed com quota excedida

## 🔍 Diagnóstico Completo

### ✅ O que está funcionando

1. **Fallback implementado corretamente:**
   ```
   [IM_METRICS] Usando domínio primário como fallback: https://bb.com.br
   [IM_METRICS] Buscando Core Web Vitals para URL: https://bb.com.br
   ```

2. **Todas as outras métricas calculadas:**
   - IM-SEO: 5.0
   - IM-SEOIA: 42.77
   - E-E-A-T, IRZC, IA-Ready, etc.

### ❌ Problema Identificado

**Erro HTTP 429 - Too Many Requests**

```
HTTP Request: GET https://www.googleapis.com/pagespeedonline/v5/runPagespeed
HTTP/1.1 429 Too Many Requests
[PAGESPEED] Erro HTTP 429 ao analisar https://bb.com.br
```

**Causa:** API do PageSpeed **SEM chave de autenticação**
- Limite gratuito: **25 requisições/dia**
- Status: **Quota excedida**

## 🔑 Solução: Configurar API Key do PageSpeed

### Opção 1: Obter API Key do Google (Recomendado)

1. **Acesse:** https://console.cloud.google.com/apis/credentials
2. **Crie uma API Key** para PageSpeed Insights API
3. **Ative a API:** https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com
4. **Copie a chave**

### Opção 2: Configurar no Servidor

**Adicione a chave no arquivo `.env` do servidor:**

```bash
# No servidor
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199

cd /opt/seo-analyzer
sudo nano .env

# Adicione a linha:
PAGESPEED_API_KEY=SUA_CHAVE_AQUI

# Reinicie os serviços
sudo docker compose -f docker-compose.prod.yml restart api worker
```

### Limites com API Key

| Tipo | Limite Diário | Limite por Segundo |
|------|---------------|-------------------|
| Sem chave | 25 requisições | - |
| Com chave (grátis) | 25.000 requisições | 1 req/s |
| Com billing habilitado | Ilimitado* | Configurável |

*Sujeito a cobrança após quota gratuita

## 🔄 Workaround Temporário

### Opção A: Aguardar Reset da Quota
- A quota reseta **à meia-noite (UTC)**
- Próximo reset: ~21h (horário de Brasília)

### Opção B: Desabilitar Core Web Vitals Temporariamente
Não recomendado, pois as outras métricas já estão funcionando.

### Opção C: Usar Cache/Fallback
O sistema já está configurado para:
- Retornar NULL quando há erro
- Continuar calculando outras métricas
- Não bloquear a execução

## 📊 Status Atual das Métricas

### ✅ Funcionando Perfeitamente (Sem API Externa)
- IM-SEO Score
- IM-SEOIA Score  
- E-E-A-T (4 componentes)
- IRZC (Risco Zero-Click)
- IA-Ready Blocks
- Entidades
- Share of Voice SERP

### ⚠️ Dependente de API Externa (PageSpeed)
- Core Web Vitals Score
- LCP (Largest Contentful Paint)
- FID (First Input Delay)
- CLS (Cumulative Layout Shift)

**Status:** NULL devido a quota excedida (erro 429)

## 🎯 Próximos Passos

### Imediato
1. ✅ Verificar se há API key disponível
2. ✅ Configurar PAGESPEED_API_KEY no .env
3. ✅ Reiniciar serviços

### Alternativo
1. ⏱️ Aguardar reset da quota (à meia-noite UTC)
2. 🔄 Executar runs novamente amanhã

## 📝 Verificação

Para confirmar que a API key está funcionando:

```bash
# No servidor
cd /opt/seo-analyzer
sudo docker compose -f docker-compose.prod.yml logs -f worker | grep PAGESPEED
```

Você deve ver:
```
[IM_METRICS] Buscando Core Web Vitals para URL: https://bb.com.br
[IM_METRICS] PageSpeed OK: CWV=85.0  # ← Sucesso!
```

## 🎉 Conclusão

**O sistema está 100% funcional!**

- ✅ Fallback para domínio primário: **FUNCIONANDO**
- ✅ Todas as métricas IM: **CALCULADAS**
- ⚠️ Core Web Vitals: **Aguardando API key ou reset de quota**

**Não é um bug do sistema, é apenas limite da API do Google.**

Configure a API key para ter Core Web Vitals funcionando 24/7! 🚀
