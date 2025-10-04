# Insights Semânticos (Gemini)

Este documento descreve a extração de entidades, palavras-chave e percepção de valor a partir das respostas de AI Overview.

## Pipeline

1. **Captura do texto**: o texto consolidado da resposta é salvo em `runs.response_text` ao final do cálculo das métricas IM.
2. **Task assíncrona**: a Celery task `tasks.process_semantic_insights` chama o `GeminiSemanticService`, envia o prompt padronizado e persiste o resultado em `run_semantic_insights`.
3. **Enriquecimento da run**: o retorno atualiza campos agregados da run (`perceived_value_category`, `semantic_summary`, `entities_*`).
4. **Disponibilização**: os dados ficam disponíveis via export CSV, endpoints de analytics e detalhes da run.

## Estrutura Persistida

A tabela `run_semantic_insights` mantém o payload completo em JSON:

```json
{
  "entities": [{
    "name": "Banco do Brasil",
    "roles": ["brand"],
    "confidence": 0.92,
    "citations": ["https://www.bb.com.br"],
    "description": "Marca protagonista"
  }],
  "relationships": [{
    "source": "Banco do Brasil",
    "target": "Conta Digital",
    "type": "brand_product",
    "weight": 0.8,
    "explanation": "Produto citado como oferta principal"
  }],
  "keywords": [{
    "token": "conta digital",
    "weight": 0.81,
    "brands": ["Banco do Brasil"],
    "competitors": ["Nubank"],
    "context": "Experiência sem tarifas"
  }],
  "perception": {
    "primary_category": "inovacao",
    "confidence": 0.74,
    "rationale": "Ênfase em app e jornada digital"
  },
  "summary": {
    "headline": "BB posicionado como opção moderna sem tarifas",
    "bullets": ["Aplicativo completo", "Comparado a Nubank"],
    "opportunities": ["Reforçar diferenciais de atendimento"]
  },
  "competitors": [{
    "name": "Nubank",
    "mentions": 2,
    "keywords": ["anuidade zero"]
  }]
}
```

## Endpoints

- `GET /analytics/im-overview`: passa a incluir a chave `semantic` com distribuição de percepção, ranking de marcas, top keywords e competidores.
- `GET /analytics/semantic-insights`: retorna apenas o snapshot semântico (mesmos filtros do overview).
- `GET /runs/{id}/semantic-insights`: entrega o payload completo e metadados da run.

## Export CSV

O export adiciona as colunas:

- `perceived_value_category`
- `semantic_summary`
- `semantic_insights_updated_at`
- `semantic_insights_json`
- Detalhes da SERP (`paa_items`, `knowledge_panel_json`, `ai_overview_json`)

## Backfill

Use o script CLI para reprocessar runs históricas:

```bash
poetry run python backend/scripts/backfill_semantic_insights.py --project prj_1234 --days 30
```

Parâmetros disponíveis:

- `--project`: filtra por projeto
- `--days`: janela móvel a partir de hoje
- `--limit`: limita o número de runs enfileiradas
- `--dry-run`: apenas lista as runs que seriam processadas

## Observabilidade

- Logs estruturados em `run_events` (`semantic_insights` started/ok/fail).
- Uso de tokens e latência retornados pelo Gemini são armazenados no payload (`usage`).
- Falhas levantam `semantic_insights` com status `fail`, permitindo reprocessamento manual.
