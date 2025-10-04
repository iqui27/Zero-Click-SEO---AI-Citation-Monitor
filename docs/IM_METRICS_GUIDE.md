# Guia de Métricas IM-SEO e IM-SEOIA

## 📊 Visão Geral

Este documento descreve o sistema de métricas **IM-SEO** (Índice de Maturidade SEO) e **IM-SEOIA** (Índice de Maturidade SEO para IA) implementado no Zero-Click SEO Monitor.

## 🎯 Índices Principais

### IM-SEO (Índice de Maturidade SEO)

**Fórmula:**
```
IM-SEO = (Autoridade + Lighthouse + Share de Tráfego + Engajamento) / 4
```

**Componentes:**
- **Autoridade** (0-100): Presença em citações (AMR + DCR)
- **Lighthouse** (0-100): Core Web Vitals score
- **Share de Tráfego** (0-100): Presença em SERP features
- **Engajamento** (0-100): ZCRS (Zero-Click Response Score)

**Interpretação:**
- **80-100**: Excelente - Forte presença e autoridade
- **60-79**: Bom - Performance sólida com espaço para melhorias
- **40-59**: Regular - Necessita otimizações
- **0-39**: Ruim - Requer atenção urgente

---

### IM-SEOIA (Índice de Maturidade SEO para IA)

**Fórmula:**
```
IM-SEOIA = Média ponderada de 8 sub-índices
```

**Sub-índices e Pesos:**
1. **Performance (CWV)** - 10%
2. **Share de Tráfego** - 15%
3. **IA - Recursos SERP** - 15%
4. **IA - Long Tail** - 15%
5. **IA - E-E-A-T** - 15%
6. **IA - Entidades** - 10%
7. **IA - Dados Estruturados** - 10%
8. **IA - Blocos IA-Ready** - 10%

---

## 📈 Métricas Detalhadas

### Core Web Vitals (Performance)

Métricas de performance do Google:

- **LCP** (Largest Contentful Paint): < 2.5s é bom
- **FID** (First Input Delay): < 100ms é bom
- **CLS** (Cumulative Layout Shift): < 0.1 é bom

**Score Geral**: 0-100 (agregado das três métricas)

---

### E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)

Avalia a qualidade e confiabilidade do conteúdo:

- **Expertise**: Demonstração de conhecimento técnico
  - Detecta: termos técnicos, dados estatísticos, números
  
- **Experience**: Relatos de experiência prática
  - Detecta: uso de primeira pessoa, relatos pessoais
  
- **Authoritativeness**: Citações de autoridade
  - Detecta: links externos, fontes, referências
  
- **Trustworthiness**: Transparência e fontes verificáveis
  - Avalia: clareza da linguagem, tamanho adequado do conteúdo

**Score Geral**: Média dos 4 componentes (0-100)

---

### Blocos IA-Ready

Detecta estruturas de conteúdo otimizadas para IA:

- **Listas**: Bullets ou numeradas
- **FAQs**: Perguntas e respostas
- **Tabelas**: Dados estruturados
- **Passo-a-passo**: Instruções sequenciais

**Score**: (Blocos detectados / 4) × 100

---

### IRZC (Índice de Risco de Zero-Click)

Mede o risco de perder cliques para features zero-click:

**Fórmula simplificada:**
```
IRZC = 100 - (número_citações × 10)
```

**Interpretação:**
- **< 30**: Baixo risco - Boa presença e autoridade
- **30-60**: Risco médio - Monitorar e otimizar
- **> 60**: Alto risco - Ação urgente necessária

**CTR Esperado**: Baseado em benchmarks do setor (Sistrix CTR curve)

---

### Entidades

Detecta e analisa entidades mencionadas no conteúdo:

- **Detected**: Número de entidades únicas identificadas
- **Relevance Score**: Frequência média de menções (0-1)
- **Connection Score**: Força da conexão com entidades (0-100)

---

## 🔌 API Endpoints

### Obter métricas de uma run específica

```bash
GET /api/runs/{run_id}/metrics
```

**Resposta:**
```json
{
  "run_id": "run_abc123",
  "im_seo_score": 75.5,
  "im_seoia_score": 68.2,
  "core_web_vitals": {
    "lcp": 2.3,
    "fid": 85,
    "cls": 0.08,
    "score": 82
  },
  "eeat": {
    "overall": 70.5,
    "expertise": 75,
    "experience": 60,
    "authoritativeness": 80,
    "trustworthiness": 85
  },
  "ia_ready": {
    "score": 75,
    "blocks_count": 3,
    "has_lists": true,
    "has_faqs": true,
    "has_tables": false,
    "has_step_by_step": true
  },
  "irzc": {
    "score": 40,
    "ctr_expected": 8.0
  }
}
```

---

### Dashboard agregado

```bash
GET /api/analytics/im-metrics/overview?project_id=xxx&days=30
```

**Parâmetros:**
- `project_id` (opcional): Filtrar por projeto
- `subproject_id` (opcional): Filtrar por subprojeto
- `days` (padrão: 30): Período em dias

**Resposta:**
```json
{
  "total_runs": 150,
  "date_range": {
    "start": "2025-01-01T00:00:00",
    "end": "2025-01-30T23:59:59"
  },
  "im_seo": {
    "average": 72.5,
    "min": 45.0,
    "max": 95.0
  },
  "im_seoia": {
    "average": 68.3,
    "min": 40.0,
    "max": 88.0
  },
  "distribution": {
    "im_seo_ranges": {
      "excellent (80-100)": 45,
      "good (60-79)": 80,
      "fair (40-59)": 20,
      "poor (0-39)": 5
    }
  }
}
```

---

### Série temporal para gráficos

```bash
GET /api/analytics/im-metrics/series?project_id=xxx&days=30
```

**Resposta:**
```json
{
  "series": [
    {
      "date": "2025-01-01",
      "im_seo": 70.5,
      "im_seoia": 65.2,
      "irzc": 45.0,
      "eeat": 68.0
    },
    {
      "date": "2025-01-02",
      "im_seo": 72.0,
      "im_seoia": 67.5,
      "irzc": 42.0,
      "eeat": 70.0
    }
  ]
}
```

---

### Recalcular métricas de uma run

```bash
POST /api/runs/{run_id}/recalculate-metrics
```

**Resposta:**
```json
{
  "run_id": "run_abc123",
  "im_seo_score": 75.5,
  "im_seoia_score": 68.2,
  "recalculated_at": "2025-01-30T15:30:00"
}
```

---

## 🛠️ Scripts Úteis

### Validar métricas

```bash
# Verificar status das métricas IM
python backend/scripts/validate_im_metrics.py
```

**Saída:**
```
📊 VALIDAÇÃO DE MÉTRICAS IM-SEO E IM-SEOIA
============================================================

✅ Total de runs completadas: 150

📈 Cobertura de Métricas:
   IM-SEO:     150/150 (100.0%)
   IM-SEOIA:   150/150 (100.0%)
   E-E-A-T:    150/150 (100.0%)
   IA-Ready:   150/150 (100.0%)
   IRZC:       150/150 (100.0%)

📊 Estatísticas Gerais:
   IM-SEO médio:   72.50
   IM-SEOIA médio: 68.30
```

---

### Recalcular métricas em runs existentes

```bash
# Recalcular todas as runs
python backend/scripts/recalculate_im_metrics.py

# Recalcular apenas 100 runs
python backend/scripts/recalculate_im_metrics.py --limit 100

# Recalcular apenas de um projeto específico
python backend/scripts/recalculate_im_metrics.py --project-id prj_abc123
```

---

## 🚀 Roadmap

### Fase 1 (MVP) - ✅ Concluído
- [x] Modelos de dados expandidos
- [x] Cálculo de métricas simplificado (sem APIs externas)
- [x] Endpoints básicos
- [x] Integração no fluxo de execução

### Fase 2 (Integrações Externas) - 🔄 Planejado
- [ ] SerpAPI - SERP Features reais
- [ ] Google NLP - Extração de entidades avançada
- [ ] Lighthouse API - Core Web Vitals reais
- [ ] Schema Validator - Validação de dados estruturados

### Fase 3 (Automação Avançada) - ⏳ Futuro
- [ ] Sistrix Integration - Long-tail e CTR benchmarks
- [ ] Clearscope/MarketMuse - E-E-A-T automation
- [ ] Alertas automáticos - Notificações de IRZC alto
- [ ] Relatórios PDF

---

## ❓ FAQ

### Por que meu IM-SEOIA está baixo?

Verifique os sub-índices individualmente no endpoint `/api/runs/{run_id}/metrics`. Geralmente, E-E-A-T e blocos IA-ready são os principais limitadores.

**Ações recomendadas:**
1. Adicione mais estrutura ao conteúdo (listas, FAQs, tabelas)
2. Inclua dados e estatísticas (aumenta Expertise)
3. Cite fontes e autoridades (aumenta Authoritativeness)

---

### Como melhorar meu IRZC?

O IRZC alto indica risco de zero-click. Para reduzir:

1. **Aumente citações**: Mais menções = mais autoridade
2. **Melhore posição orgânica**: Otimize SEO tradicional
3. **Conquiste featured snippets**: Estruture conteúdo para snippets
4. **Otimize para AI Overviews**: Use blocos IA-ready

---

### Qual a diferença entre IM-SEO e IM-SEOIA?

- **IM-SEO**: Mede SEO tradicional (autoridade, performance, tráfego)
- **IM-SEOIA**: Adiciona métricas específicas para IA e zero-click (E-E-A-T, entidades, blocos estruturados, IRZC)

Use ambos para uma visão completa da sua presença digital.

---

### As métricas são calculadas automaticamente?

✅ **Sim!** Todas as novas runs calculam as métricas IM automaticamente.

Para runs antigas (antes da implementação), use:
```bash
python backend/scripts/recalculate_im_metrics.py
```

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs: `docker compose logs -f backend`
2. Execute validação: `python backend/scripts/validate_im_metrics.py`
3. Consulte a documentação técnica em `/docs`

---

**Última atualização**: 2025-01-30  
**Versão**: 1.0 (MVP)
