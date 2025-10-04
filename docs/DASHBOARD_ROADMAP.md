# 🗺️ Dashboard & Data Explorer - Roadmap de Implementação

## ✅ **Já Implementado**

### **Dashboard Básico**
- ✅ Cards de métricas com min/max
- ✅ Gráficos de evolução temporal
- ✅ Distribuição de scores
- ✅ Tabs detalhadas (Performance, Conteúdo, SERP, IA)
- ✅ Filtro por projeto
- ✅ Filtro por período (7, 30, 90, 180, 365 dias)

### **Backend**
- ✅ API de Analytics (`/im-overview`, `/timeseries`, `/projects`)
- ✅ Métricas IM-SEO/IM-SEOIA completas
- ✅ Suporte a filtro por projeto

---

## 📋 **Próximas Implementações**

### **1. Filtros Avançados** ⏳
**Prioridade**: ALTA  
**Tempo Estimado**: 2-3 dias

#### **Funcionalidades**
- [ ] Filtro por Engine (Perplexity, ChatGPT, Gemini, etc)
- [ ] Filtro por Data Range (seletor de intervalo)
- [ ] Filtro por Métricas (range sliders: IM-SEO 0-100, etc)
- [ ] Filtro por Classificação
  - Response Type (Direta, Instrucional, etc)
  - Brand Positioning (Líder, Competidor, etc)
- [ ] Salvar filtros favoritos
- [ ] Aplicar múltiplos filtros simultaneamente
- [ ] Exportar/Importar configurações de filtros

#### **Componentes**
```tsx
// AdvancedFilters.tsx
- MultiSelect (Engines, Projects)
- DateRangePicker (De/Até)
- RangeSlider (IM-SEO, IM-SEOIA, E-E-A-T, IRZC)
- Checkbox Groups (Classifications)
- SavedFilters (Lista de favoritos)
```

#### **Backend**
```python
# Endpoint atualizado
@router.get("/im-overview")
def get_im_overview(
    project_id: Optional[str] = None,
    engine_ids: Optional[List[int]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    im_seo_min: Optional[float] = None,
    im_seo_max: Optional[float] = None,
    response_types: Optional[List[str]] = None,
    brand_positions: Optional[List[str]] = None,
    ...
)
```

---

### **2. Data Explorer (Estilo Databricks)** ⏳
**Prioridade**: ALTA  
**Tempo Estimado**: 4-5 dias

#### **Estrutura da Página**

```
┌─────────────────────────────────────────────────────────┐
│  Data Explorer                                    [Export]│
├──────────┬──────────────────────────────────────────────┤
│          │  Query Builder / SQL Editor                  │
│ Schema   │  ┌────────────────────────────────────────┐ │
│          │  │ SELECT im_seo_score, im_seoia_score    │ │
│ ▼ Runs   │  │ FROM runs                              │ │
│   - id   │  │ WHERE im_seo_score > 50                │ │
│   - im_  │  │ ORDER BY created_at DESC               │ │
│   - eeat │  │ LIMIT 100                              │ │
│          │  └────────────────────────────────────────┘ │
│ ▼ Citat. │  [Execute] [Save Query] [Load Query]       │
│   - url  │                                             │
│   - type │  Results: 28 rows in 45ms                  │
│          │  ┌────────────────────────────────────────┐ │
│ ▼ Proj.  │  │ [Table with sortable columns]          │ │
│   - name │  │ [Pagination]                           │ │
│          │  └────────────────────────────────────────┘ │
│          │  [Chart Builder]                           │
└──────────┴──────────────────────────────────────────────┘
```

#### **Funcionalidades**

**Visual Query Builder**
```tsx
<QueryBuilder>
  <SelectColumns columns={availableColumns} />
  <FromTable tables={['runs', 'citations', 'projects']} />
  <WhereFilters>
    <Filter column="im_seo_score" operator=">" value="50" />
    <Filter column="created_at" operator=">" value="2025-01-01" />
  </WhereFilters>
  <GroupBy columns={['project_id']} />
  <OrderBy column="im_seo_score" direction="DESC" />
  <Limit value={100} />
</QueryBuilder>
```

**SQL Editor**
- Monaco Editor (VSCode-like)
- Syntax highlighting
- Auto-complete
- Query history
- Saved queries

**Tabela Interativa**
- Ordenação por coluna
- Filtros inline
- Paginação
- Seleção de linhas
- Copiar células

**Sidebar com Schema**
- Todas as tabelas
- Colunas com tipos
- Drag & drop para query
- Busca de campos

#### **Backend**

```python
# /api/data-explorer/query
@router.post("/data-explorer/query")
def execute_query(query: DataExplorerQuery):
    # Validar query
    # Executar com segurança
    # Retornar resultados + metadata
    return {
        "sql": "SELECT ...",
        "rows": [...],
        "row_count": 28,
        "query_time_ms": 45,
        "columns": [...]
    }

# /api/data-explorer/schema
@router.get("/data-explorer/schema")
def get_schema():
    return {
        "tables": [
            {
                "name": "runs",
                "columns": [
                    {"name": "id", "type": "VARCHAR(50)"},
                    {"name": "im_seo_score", "type": "FLOAT"},
                    ...
                ]
            },
            ...
        ]
    }

# /api/data-explorer/saved-queries
@router.get("/data-explorer/saved-queries")
def get_saved_queries():
    ...
```

---

### **3. Exportação de Dados** ⏳
**Prioridade**: MÉDIA  
**Tempo Estimado**: 1-2 dias

#### **Funcionalidades**
- [ ] Exportar para CSV
- [ ] Exportar para JSON
- [ ] Exportar para Excel (.xlsx)
- [ ] Incluir metadados (filtros, data, usuário)
- [ ] Download em lote
- [ ] Agendamento de exports (futuro)

#### **UI**

```tsx
<ExportDialog>
  <RadioGroup label="Formato">
    <Radio value="csv">CSV</Radio>
    <Radio value="json">JSON</Radio>
    <Radio value="excel">Excel</Radio>
  </RadioGroup>
  
  <Checkbox>Incluir cabeçalhos</Checkbox>
  <Checkbox>Incluir metadados (filtros aplicados)</Checkbox>
  <Checkbox>Incluir timestamp</Checkbox>
  
  <Button>Exportar {rowCount} linhas</Button>
</ExportDialog>
```

#### **Backend**

```python
@router.post("/export/{format}")
def export_data(
    format: str,  # csv, json, excel
    query: ExportQuery,
    include_metadata: bool = True
):
    if format == "csv":
        return Response(
            content=generate_csv(data),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"}
        )
    elif format == "json":
        return JSONResponse(content=data)
    elif format == "excel":
        return Response(
            content=generate_excel(data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"}
        )
```

---

### **4. Visualizações Avançadas** ⏳
**Prioridade**: MÉDIA  
**Tempo Estimado**: 2-3 dias

#### **Chart Builder**

```tsx
<ChartBuilder data={queryResults}>
  <ChartTypeSelector>
    <Option value="line">Linha</Option>
    <Option value="bar">Barra</Option>
    <Option value="pie">Pizza</Option>
    <Option value="scatter">Dispersão</Option>
    <Option value="heatmap">Heatmap</Option>
    <Option value="area">Área</Option>
  </ChartTypeSelector>
  
  <AxisConfig>
    <Select label="Eixo X" options={columns} />
    <Select label="Eixo Y" options={numericColumns} />
    <Select label="Agrupar por" options={columns} />
  </AxisConfig>
  
  <StyleConfig>
    <ColorPicker label="Cor principal" />
    <Input label="Título" />
    <Checkbox>Mostrar legenda</Checkbox>
    <Checkbox>Mostrar grid</Checkbox>
  </StyleConfig>
  
  <Button>Salvar Visualização</Button>
</ChartBuilder>
```

#### **Tipos de Gráficos**

**Linha**
- Evolução temporal
- Múltiplas séries
- Área empilhada

**Barra**
- Comparação de categorias
- Barras empilhadas
- Barras agrupadas

**Pizza**
- Distribuição percentual
- Donut chart

**Dispersão**
- Correlação entre métricas
- Bubble chart (3 dimensões)

**Heatmap**
- Matriz de correlação
- Densidade de dados

#### **Salvamento**

```python
# Model
class SavedVisualization(Base):
    id: str
    user_id: str
    name: str
    chart_type: str
    config: dict  # JSON com configuração
    query: str  # Query SQL ou filtros
    created_at: datetime

# API
@router.post("/visualizations")
def save_visualization(viz: VisualizationCreate):
    ...

@router.get("/visualizations")
def list_visualizations():
    ...
```

---

## 📅 **Cronograma Sugerido**

### **Semana 1**
- Dia 1-2: Filtros Avançados (Engine, Date Range)
- Dia 3: Filtros Avançados (Range Sliders, Classificação)
- Dia 4: Salvar Filtros Favoritos
- Dia 5: Testes e ajustes

### **Semana 2**
- Dia 1-2: Data Explorer - Estrutura e Schema
- Dia 3: Visual Query Builder
- Dia 4: SQL Editor
- Dia 5: Tabela Interativa

### **Semana 3**
- Dia 1: Exportação (CSV, JSON)
- Dia 2: Exportação (Excel, Metadados)
- Dia 3-4: Chart Builder
- Dia 5: Salvamento de Visualizações

---

## 🎯 **Priorização**

### **Must Have** (Essencial)
1. ✅ Dashboard básico (FEITO)
2. ✅ Filtros básicos (FEITO)
3. ⏳ Filtros avançados
4. ⏳ Exportação CSV/JSON
5. ⏳ Data Explorer básico

### **Should Have** (Importante)
6. ⏳ SQL Editor
7. ⏳ Chart Builder
8. ⏳ Exportação Excel
9. ⏳ Salvar queries

### **Nice to Have** (Desejável)
10. ⏳ Heatmaps
11. ⏳ Agendamento de exports
12. ⏳ Compartilhamento de dashboards
13. ⏳ Alertas personalizados

---

## 📝 **Notas Técnicas**

### **Bibliotecas Necessárias**

**Frontend**
```json
{
  "dependencies": {
    "react-datepicker": "^4.21.0",
    "react-select": "^5.8.0",
    "@monaco-editor/react": "^4.6.0",
    "recharts": "^2.10.0",
    "xlsx": "^0.18.5",
    "file-saver": "^2.0.5"
  }
}
```

**Backend**
```txt
pandas==2.1.0
openpyxl==3.1.2
xlsxwriter==3.1.9
```

---

## 🚀 **Como Começar**

### **Próximo Passo Imediato**
Implementar **Filtros Avançados** começando por:
1. Filtro por Engine
2. Date Range Picker
3. Range Sliders para métricas

**Quer que eu comece agora?** 🎯

---

**Última atualização**: 30/01/2025  
**Status**: Roadmap Completo
