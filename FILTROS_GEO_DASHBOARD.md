# Correção dos Filtros do GEO Dashboard

## Mapeamento Correto dos Filtros

### Backend (`backend/app/services/geo_dashboard.py`)

| Filtro Frontend | Parâmetro Backend | Campo do Banco | Descrição |
|----------------|-------------------|----------------|-----------|
| **Marcas** | `brand` (client-side) | - | Filtro local no frontend (com/sem marca) |
| **LLM** | `llm_model` | `Run.model_name` | Nome do modelo LLM (gpt, claude, gemini, etc.) |
| **Projeto** | `project_id` | `Run.project_id` | ID do projeto (já existente) |
| **Tema** | `subproject_id` | `Run.subproject_id` | ID do subprojeto (tema) |
| **Categoria** | `prompt_category` | `Prompt.name` ou `Prompt.text` | Busca parcial no nome/texto do prompt |
| **Prompt** | `prompt_text` | `Prompt.text` ou `Prompt.name` | Busca parcial no texto/nome do prompt |

### Estrutura de Dados

```
Run
├── prompt_version_id → PromptVersion
│   └── prompt_id → Prompt
│       ├── name (usado para categoria)
│       └── text (usado para busca de prompt)
├── subproject_id → SubProject (TEMA)
├── model_name (LLM)
└── project_id → Project
```

**Nota**: `PromptTemplate` é uma tabela separada com `category`, mas não está linkada aos `Run`. Os runs usam `Prompt` via `PromptVersion`.

## Mudanças Implementadas

### Backend

1. **`backend/app/services/geo_dashboard.py`**
   - Adicionado parâmetro `prompt_category` (substitui `category`)
   - Adicionado parâmetro `prompt_text` (substitui `theme`)
   - Removido parâmetro `theme` (agora é `subproject_id`)
   - Implementado JOIN com `PromptVersion` → `Prompt` para filtrar por categoria/texto
   - Filtro `llm_model` usa `Run.model_name`
   - Filtro `subproject_id` usa `Run.subproject_id` (tema)

2. **`backend/app/api/routes.py`**
   - Endpoint `/projects/{project_id}/geo-dashboard` aceita:
     - `llm_model`: filtro por modelo LLM
     - `prompt_category`: busca parcial em `Prompt.name` ou `Prompt.text`
     - `prompt_text`: busca parcial em `Prompt.text` ou `Prompt.name`
     - `subproject_id`: filtro por tema (subprojeto)

### Frontend

1. **`frontend/src/lib/api.ts`**
   - `getGeoDashboard()` aceita `prompt_category` e `prompt_text`
   - Removido `theme` e `category` (substituídos)

2. **`frontend/src/components/geo/UnifiedGeoDashboard.tsx`**
   - Labels atualizados:
     - "Tema (Subprojeto)" → usa `subproject_id`
     - "Categoria (Prompt)" → usa `prompt_category`
     - "Prompt (Texto)" → usa `prompt_text`
   - TODOs adicionados para carregar opções dinamicamente

## Como Testar

### 1. Rebuild e Start dos Containers

```bash
cd /Users/hrocha/Documents/Projetos/SEO\ Analyzer
docker compose build --no-cache
docker compose up -d
```

### 2. Verificar Logs do Backend

```bash
docker compose logs -f seoanalyzer-backend
```

Procure por erros de importação ou SQL.

### 3. Testar Filtros via API

```bash
# Filtro por LLM
curl "http://localhost:8000/api/projects/{project_id}/geo-dashboard?llm_model=gpt"

# Filtro por Subprojeto (Tema)
curl "http://localhost:8000/api/projects/{project_id}/geo-dashboard?subproject_id={subproject_id}"

# Filtro por Categoria de Prompt
curl "http://localhost:8000/api/projects/{project_id}/geo-dashboard?prompt_category=abertura"

# Filtro por Texto de Prompt
curl "http://localhost:8000/api/projects/{project_id}/geo-dashboard?prompt_text=conta"

# Múltiplos filtros
curl "http://localhost:8000/api/projects/{project_id}/geo-dashboard?llm_model=gpt&subproject_id={subproject_id}&prompt_category=abertura"
```

### 4. Testar no Frontend

1. Acesse `http://localhost:5173` (ou IP do servidor)
2. Navegue para o Dashboard GEO
3. Teste cada filtro:
   - **LLM**: Selecione "OpenAI GPT", "Claude", etc.
   - **Tema**: Selecione um subprojeto (quando implementado dinamicamente)
   - **Categoria**: Digite parte do nome do prompt
   - **Prompt**: Digite parte do texto do prompt

### 5. Validar Dados Retornados

Verifique se:
- `total_runs` diminui ao aplicar filtros
- `cocitation_breakdown` retorna dados reais (não mock)
- `context_insights` retorna performance por contexto
- `exclusive_citations_count` retorna número inteiro

## Próximos Passos

1. **Carregar Opções Dinamicamente**
   - Criar endpoints para listar:
     - Subprojects do projeto
     - Categorias de prompts únicas
     - Prompts do projeto
   - Atualizar `filterConfigs` no frontend para usar dados reais

2. **Melhorar UX dos Filtros**
   - Substituir select de "Prompt" por input de busca
   - Adicionar autocomplete para categorias
   - Mostrar contador de resultados ao aplicar filtros

3. **Validar Dados de Ingestão**
   - Garantir que `Run.model_name` está preenchido
   - Garantir que `Run.subproject_id` está preenchido quando aplicável
   - Garantir que `Run.cocitation_competitors` está em formato JSON válido

## Troubleshooting

### Erro: "Cannot import name 'PromptVersion'"

**Causa**: Modelo não existe ou nome incorreto.

**Solução**: Verificar `backend/app/models/models.py` e confirmar nome exato da classe.

### Filtros não retornam resultados

**Causa**: Dados não estão preenchidos ou filtro muito restritivo.

**Solução**:
1. Verificar no banco se `Run.model_name`, `Run.subproject_id` estão populados
2. Testar sem filtros primeiro
3. Adicionar logs no backend para debug

### Frontend não envia filtros

**Causa**: Estado local não está sendo propagado para API.

**Solução**: Adicionar `console.log(filters)` antes de chamar `getGeoDashboard()` e verificar valores.
