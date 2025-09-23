# Sistema de Classificação Zero-Click SEO

## Visão Geral

O Sistema de Classificação Zero-Click SEO é uma solução completa para análise e classificação de respostas de IA em consultas de busca, especialmente focada em métricas Zero-Click e otimização SEO para o Banco do Brasil.

## Funcionalidades Principais

### 1. Classificação Básica de Respostas

#### Tipos de Resposta (ResponseType)
- **direta**: Resposta objetiva e factual
- **explicativa**: Explica conceitos bancários ou financeiros
- **instrucional**: Fornece guia passo-a-passo
- **comparativa**: Compara produtos ou bancos
- **consultiva**: Oferece recomendação ou opinião
- **navegacional**: Direciona para site ou aplicativo

#### Nível de Suficiência (SufficiencyLevel)
- **total**: Resposta completa que satisfaz totalmente a consulta
- **parcial**: Resposta útil mas incompleta
- **insuficiente**: Resposta inadequada ou muito vaga

#### Tipo de Acionabilidade (ActionabilityType)
- **transacional**: Permite ação direta (abrir conta, solicitar empréstimo)
- **informativa**: Fornece informação para decisão posterior

#### Fonte de Confiança (TrustSource)
- **citada**: Informação com citações e fontes verificáveis
- **generica**: Informação geral sem fontes específicas

#### Posicionamento da Marca (BrandPositioning)
- **protagonista**: BB é a solução principal mencionada
- **competidor**: BB aparece junto com outros bancos
- **ausente**: BB não é mencionado mas deveria estar

### 2. Métricas Avançadas

#### Intenção do Usuário (UserIntent)
- **informational**: Busca entender conceitos
- **transactional**: Quer realizar ação específica
- **navigational**: Procura site/app específico
- **commercial**: Compara produtos antes de decidir

#### Potencial de Conversão (ConversionPotential)
- **alto**: Alta probabilidade de conversão
- **medio**: Probabilidade moderada
- **baixo**: Baixa probabilidade de conversão

#### Métricas Numéricas
- **satisfaction_score**: Score de satisfação (0.0-1.0)
- **competitive_mentions**: Número de menções a concorrentes
- **financial_value_score**: Score de valor financeiro (0.0-10.0)
- **content_gap_detected**: Detecta gaps de conteúdo (boolean)
- **classification_confidence**: Confiança da classificação (0.0-1.0)

### 3. Análise com Gemini 2.5 Pro

O sistema integra o Google Gemini 2.5 Pro para análises mais sofisticadas e insights estratégicos.

#### Recursos Gemini
- Análise contextual avançada
- Insights estratégicos automatizados
- Sugestões de otimização
- Análise competitiva detalhada
- Detecção de oportunidades de conteúdo

## Arquitetura do Sistema

### Backend (FastAPI + SQLAlchemy)

#### Modelos de Dados
```python
# Campos adicionados ao modelo Run
response_type = Column(String(50))
sufficiency_level = Column(String(50))
actionability_type = Column(String(50))
trust_source = Column(String(50))
brand_positioning = Column(String(50))
classification_confidence = Column(Float)
classified_at = Column(DateTime)
classification_version = Column(String(20))

# Métricas avançadas
user_intent = Column(String(50))
satisfaction_score = Column(Float)
competitive_mentions = Column(Integer)
financial_value_score = Column(Float)
content_gap_detected = Column(Boolean)
conversion_potential = Column(String(50))
```

#### Serviços Principais

1. **ResponseClassifier** (`backend/app/services/response_classifier.py`)
   - Classificação baseada em regras e padrões
   - Análise de texto e detecção de marcas
   - Configurável para diferentes domínios

2. **AdvancedMetricsAnalyzer** (`backend/app/services/advanced_metrics.py`)
   - Cálculo de métricas avançadas
   - Análise de intenção do usuário
   - Avaliação de valor financeiro

3. **GeminiZeroClickAnalyzer** (`backend/app/services/gemini_classifier.py`)
   - Integração com Gemini 2.5 Pro
   - Análise contextual avançada
   - Geração de insights estratégicos

4. **ClassificationIntegrator** (`backend/app/services/classification_integration.py`)
   - Orquestração de classificadores
   - Operações em lote
   - Integração com banco de dados

#### API Endpoints

##### Classificação Individual
```
POST /runs/{run_id}/classify
POST /runs/{run_id}/classify/gemini
```

##### Classificação em Lote
```
POST /projects/{project_id}/classify/batch
POST /projects/{project_id}/classify/gemini/batch
```

##### Estatísticas e Analytics
```
GET /projects/{project_id}/classification/stats
GET /projects/{project_id}/insights/gemini
GET /projects/{project_id}/classification/gemini-status
GET /classification/unprocessed
```

##### Migração e Gestão
```
POST /classification/migrate-to-gemini
DELETE /monitors/{monitor_id}/runs
```

### Frontend (React + TypeScript)

#### Tipos TypeScript
```typescript
export type RunListItem = {
  // ... campos existentes
  response_type?: string
  sufficiency_level?: string
  actionability_type?: string
  trust_source?: string
  brand_positioning?: string
  classification_confidence?: number
}

export type GeminiClassificationResponse = {
  run_id: string
  classification: ClassificationResult
  advanced_metrics: AdvancedMetrics
  ai_insights: AIInsights
  classified_at: string
  version: string
}
```

#### Funções API
```typescript
// Classificação básica
export const classifyRun = (runId: string)
export const batchClassifyProject = (projectId: string, forceUpdate = false, limit = 1000)

// Classificação Gemini
export const classifyRunWithGemini = (runId: string)
export const batchClassifyWithGemini = (projectId: string, limit = 500)

// Analytics e insights
export const getClassificationStats = (projectId: string)
export const getGeminiInsights = (projectId: string, days = 7)
export const getGeminiStatus = (projectId: string)
```

## Scripts de Automação

### 1. Classificação de Runs Existentes
**Arquivo**: `scripts/classify_existing_runs.py`

```bash
# Classificar todas as runs de um projeto
python scripts/classify_existing_runs.py --project-id PROJECT_ID

# Dry run para ver o que seria processado
python scripts/classify_existing_runs.py --dry-run

# Processar apenas 100 runs
python scripts/classify_existing_runs.py --limit 100

# Reprocessar runs já classificadas
python scripts/classify_existing_runs.py --force
```

### 2. Análise Retroativa com Gemini
**Arquivo**: `scripts/gemini_retroactive_analysis.py`

```bash
# Análise completa com Gemini
python scripts/gemini_retroactive_analysis.py --project-id PROJECT_ID

# Migrar classificações básicas para Gemini
python scripts/gemini_retroactive_analysis.py --upgrade-existing

# Gerar relatório de insights
python scripts/gemini_retroactive_analysis.py --generate-insights --insights-days 30

# Processamento em lotes menores
python scripts/gemini_retroactive_analysis.py --batch-size 10 --delay-between-batches 5.0
```

## Configuração e Deploy

### Variáveis de Ambiente
```bash
# Chave da API do Google Gemini
GOOGLE_API_KEY=your_gemini_api_key
# ou
GEMINI_API_KEY=your_gemini_api_key
```

### Migração de Banco de Dados

O sistema suporta migração automática para PostgreSQL e SQL Server:

```python
# PostgreSQL
ALTER TABLE runs ADD COLUMN response_type VARCHAR(50);
ALTER TABLE runs ADD COLUMN sufficiency_level VARCHAR(50);
# ... outros campos

# SQL Server
ALTER TABLE runs ADD response_type NVARCHAR(50);
ALTER TABLE runs ADD sufficiency_level NVARCHAR(50);
# ... outros campos
```

### Integração com Pipeline Existente

A classificação é automaticamente executada após o processamento de KPIs:

```python
# Em backend/app/services/tasks.py
async def process_run_task(run_id: str):
    # ... processamento existente

    # Executar classificação automaticamente
    from app.services.classification_integration import classify_run_automatically
    classification_result = await classify_run_automatically(run_id)

    # ... finalização
```

## Casos de Uso e Exemplos

### 1. Análise de Presença da Marca
```python
# Verificar como o BB está posicionado nas respostas
stats = get_classification_stats(project_id)
brand_presence = stats['brand_positioning']
# {'protagonista': 45, 'competidor': 30, 'ausente': 25}
```

### 2. Identificação de Gaps de Conteúdo
```python
# Encontrar oportunidades de conteúdo
insights = get_gemini_insights(project_id, days=30)
content_gaps = insights['summary']['content_gaps_detected']
priority_opportunities = insights['priority_opportunities']
```

### 3. Otimização de Campanhas
```python
# Focar em consultas de alto valor com gaps
runs_with_gaps = filter_runs(
    financial_value_score__gte=7.0,
    content_gap_detected=True,
    brand_positioning='ausente'
)
```

## Métricas e KPIs

### 1. Taxa de Cobertura
- Percentual de runs classificadas
- Cobertura Gemini vs classificação básica

### 2. Posicionamento da Marca
- Distribuição protagonista/competidor/ausente
- Evolução temporal do posicionamento

### 3. Valor Financeiro
- Score médio de valor financeiro
- Oportunidades de alto valor perdidas

### 4. Satisfação do Usuário
- Score médio de satisfação
- Correlação com posicionamento da marca

### 5. Análise Competitiva
- Número médio de menções a concorrentes
- Brands mais mencionadas

## Monitoramento e Alertas

### 1. Classificação Automática
- Todas as novas runs são automaticamente classificadas
- Fallback para classificação local se Gemini falhar

### 2. Detecção de Anomalias
- Alertas para queda no posicionamento da marca
- Identificação de novos concorrentes

### 3. Performance da API
- Monitoramento de latência do Gemini
- Rate limiting e retry logic

## Roadmap e Próximos Passos

### 1. Melhorias na Classificação
- Treinamento de modelos específicos
- Integração com outros LLMs (Claude, GPT-4)
- Classificação multilíngue

### 2. Analytics Avançado
- Dashboard de insights em tempo real
- Análise predictiva de tendências
- Correlação com métricas de negócio

### 3. Automação
- Alertas automáticos para oportunidades
- Sugestões automáticas de conteúdo
- Integração com ferramentas de marketing

### 4. Expansão
- Suporte a outros domínios além de bancos
- Análise de vídeo e imagem
- Integração com redes sociais

## Troubleshooting

### Problemas Comuns

1. **Gemini API não responde**
   - Verificar chave de API
   - Confirmar cota disponível
   - Usar classificação local como fallback

2. **Classificação inconsistente**
   - Revisar prompts do Gemini
   - Ajustar parâmetros de confiança
   - Reprocessar com versão atualizada

3. **Performance lenta**
   - Reduzir tamanho dos lotes
   - Aumentar delay entre chamadas
   - Otimizar queries de banco

### Logs e Debugging

```bash
# Logs de classificação
tail -f logs/classification.log

# Debug de API do Gemini
export GEMINI_DEBUG=1
python scripts/gemini_retroactive_analysis.py --dry-run
```

## Referências

- [Documentação Gemini API](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [React TypeScript](https://react-typescript-cheatsheet.netlify.app/)

---

**Versão**: 2.0-gemini
**Última atualização**: Setembro 2025
**Maintainer**: Equipe SEO Analyzer