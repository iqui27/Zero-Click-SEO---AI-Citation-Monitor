# 📊 Dashboard & Data Explorer - Plano de Implementação

## 🎯 **Objetivos**

1. **Dashboard Melhorado** - Visualização completa das métricas IM-SEO/IM-SEOIA
2. **Filtros Avançados** - Por projeto, tema, prompt, run, data
3. **Data Explorer** - Análise de dados estilo Databricks/Metabase
4. **Exportação** - CSV, JSON, Excel

---

## 📋 **Fase 1: Dashboard Melhorado**

### **1.1 Visão Geral - Cards de Métricas**

```tsx
// components/Dashboard/MetricsOverview.tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* IM-SEO */}
  <MetricCard
    title="IM-SEO Médio"
    value={avgIMSEO}
    trend={trendIMSEO}
    icon={<TrendingUp />}
    color="blue"
  />
  
  {/* IM-SEOIA */}
  <MetricCard
    title="IM-SEOIA Médio"
    value={avgIMSEOIA}
    trend={trendIMSEOIA}
    icon={<Zap />}
    color="purple"
  />
  
  {/* E-E-A-T */}
  <MetricCard
    title="E-E-A-T Médio"
    value={avgEEAT}
    trend={trendEEAT}
    icon={<Award />}
    color="green"
  />
  
  {/* IRZC */}
  <MetricCard
    title="IRZC Médio"
    value={avgIRZC}
    trend={trendIRZC}
    icon={<Shield />}
    color="orange"
  />
</div>
```

### **1.2 Gráficos de Evolução Temporal**

```tsx
// components/Dashboard/TimeSeriesCharts.tsx
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  {/* Evolução IM-SEO/IM-SEOIA */}
  <Card>
    <CardHeader>
      <CardTitle>Evolução IM-SEO & IM-SEOIA</CardTitle>
    </CardHeader>
    <CardContent>
      <LineChart data={timeSeriesData}>
        <Line dataKey="im_seo_score" stroke="#3b82f6" />
        <Line dataKey="im_seoia_score" stroke="#8b5cf6" />
      </LineChart>
    </CardContent>
  </Card>
  
  {/* Distribuição de Scores */}
  <Card>
    <CardHeader>
      <CardTitle>Distribuição de Scores</CardTitle>
    </CardHeader>
    <CardContent>
      <BarChart data={distributionData}>
        <Bar dataKey="count" fill="#3b82f6" />
      </BarChart>
    </CardContent>
  </Card>
</div>
```

### **1.3 Métricas Detalhadas**

```tsx
// components/Dashboard/DetailedMetrics.tsx
<Tabs defaultValue="performance">
  <TabsList>
    <TabsTrigger value="performance">Performance</TabsTrigger>
    <TabsTrigger value="content">Conteúdo</TabsTrigger>
    <TabsTrigger value="serp">SERP</TabsTrigger>
    <TabsTrigger value="ia">IA-Ready</TabsTrigger>
  </TabsList>
  
  <TabsContent value="performance">
    <div className="grid grid-cols-3 gap-4">
      <MetricDetail
        label="Core Web Vitals"
        value={avgCWV}
        breakdown={{
          LCP: avgLCP,
          FID: avgFID,
          CLS: avgCLS
        }}
      />
      <MetricDetail
        label="Share of Voice"
        value={avgSoV}
        chart={<SparklineChart data={sovData} />}
      />
      <MetricDetail
        label="Organic Position"
        value={avgPosition}
        distribution={positionDistribution}
      />
    </div>
  </TabsContent>
  
  <TabsContent value="content">
    <div className="grid grid-cols-3 gap-4">
      <MetricDetail
        label="E-E-A-T"
        value={avgEEAT}
        breakdown={{
          Expertise: avgExpertise,
          Experience: avgExperience,
          Authoritativeness: avgAuthoritativeness,
          Trustworthiness: avgTrustworthiness
        }}
      />
      <MetricDetail
        label="Entidades"
        value={avgEntities}
        chart={<BarChart data={entitiesData} />}
      />
      <MetricDetail
        label="IA-Ready Blocks"
        value={avgIAReady}
        breakdown={{
          Lists: countLists,
          FAQs: countFAQs,
          Tables: countTables,
          StepByStep: countSteps
        }}
      />
    </div>
  </TabsContent>
</Tabs>
```

---

## 🔍 **Fase 2: Filtros Avançados**

### **2.1 Componente de Filtros**

```tsx
// components/Filters/AdvancedFilters.tsx
interface FilterState {
  projects: string[];
  dateRange: { start: Date; end: Date };
  engines: number[];
  status: string[];
  metrics: {
    im_seo_min?: number;
    im_seo_max?: number;
    im_seoia_min?: number;
    im_seoia_max?: number;
  };
  classification: {
    response_type?: string[];
    brand_positioning?: string[];
  };
}

<Card>
  <CardHeader>
    <CardTitle>Filtros Avançados</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      {/* Projeto */}
      <div>
        <Label>Projetos</Label>
        <MultiSelect
          options={projects}
          value={filters.projects}
          onChange={(val) => setFilters({...filters, projects: val})}
        />
      </div>
      
      {/* Data Range */}
      <div>
        <Label>Período</Label>
        <DateRangePicker
          value={filters.dateRange}
          onChange={(val) => setFilters({...filters, dateRange: val})}
        />
      </div>
      
      {/* Engines */}
      <div>
        <Label>Engines</Label>
        <MultiSelect
          options={engines}
          value={filters.engines}
          onChange={(val) => setFilters({...filters, engines: val})}
        />
      </div>
      
      {/* Métricas (Range Sliders) */}
      <div>
        <Label>IM-SEO Score</Label>
        <RangeSlider
          min={0}
          max={100}
          value={[filters.metrics.im_seo_min, filters.metrics.im_seo_max]}
          onChange={(val) => setFilters({
            ...filters,
            metrics: {
              ...filters.metrics,
              im_seo_min: val[0],
              im_seo_max: val[1]
            }
          })}
        />
      </div>
      
      {/* Classificação */}
      <div>
        <Label>Tipo de Resposta</Label>
        <MultiSelect
          options={responseTypes}
          value={filters.classification.response_type}
          onChange={(val) => setFilters({
            ...filters,
            classification: {
              ...filters.classification,
              response_type: val
            }
          })}
        />
      </div>
      
      {/* Botões */}
      <div className="flex gap-2">
        <Button onClick={applyFilters}>Aplicar Filtros</Button>
        <Button variant="outline" onClick={clearFilters}>Limpar</Button>
        <Button variant="ghost" onClick={saveFilter}>Salvar Filtro</Button>
      </div>
    </div>
  </CardContent>
</Card>
```

### **2.2 API Endpoint para Filtros**

```python
# backend/app/api/routes.py

@api_router.post("/runs/filter")
def filter_runs(
    filters: RunFilters,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    Filtra runs com múltiplos critérios.
    """
    query = db.query(Run)
    
    # Filtrar por projetos
    if filters.projects:
        query = query.filter(Run.project_id.in_(filters.projects))
    
    # Filtrar por data
    if filters.date_range:
        query = query.filter(
            Run.started_at >= filters.date_range.start,
            Run.started_at <= filters.date_range.end
        )
    
    # Filtrar por engines
    if filters.engines:
        query = query.filter(Run.engine_id.in_(filters.engines))
    
    # Filtrar por métricas
    if filters.metrics.im_seo_min is not None:
        query = query.filter(Run.im_seo_score >= filters.metrics.im_seo_min)
    if filters.metrics.im_seo_max is not None:
        query = query.filter(Run.im_seo_score <= filters.metrics.im_seo_max)
    
    # Filtrar por classificação
    if filters.classification.response_type:
        query = query.filter(Run.response_type.in_(filters.classification.response_type))
    
    # Paginação
    total = query.count()
    runs = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "runs": runs
    }
```

---

## 📊 **Fase 3: Data Explorer (Estilo Databricks)**

### **3.1 Estrutura da Página**

```tsx
// pages/DataExplorer.tsx
<div className="flex h-screen">
  {/* Sidebar - Tabelas e Campos */}
  <aside className="w-64 border-r bg-gray-50">
    <div className="p-4">
      <h2 className="font-bold mb-4">Tabelas</h2>
      <Accordion type="single" collapsible>
        <AccordionItem value="runs">
          <AccordionTrigger>Runs</AccordionTrigger>
          <AccordionContent>
            <div className="space-y-1">
              {runColumns.map(col => (
                <div
                  key={col.name}
                  className="flex items-center gap-2 p-2 hover:bg-gray-100 cursor-pointer"
                  onClick={() => addColumn(col)}
                >
                  <Database className="w-4 h-4" />
                  <span className="text-sm">{col.name}</span>
                  <Badge variant="outline">{col.type}</Badge>
                </div>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>
        
        <AccordionItem value="citations">
          <AccordionTrigger>Citations</AccordionTrigger>
          <AccordionContent>
            {/* Similar structure */}
          </AccordionContent>
        </AccordionItem>
        
        <AccordionItem value="projects">
          <AccordionTrigger>Projects</AccordionTrigger>
          <AccordionContent>
            {/* Similar structure */}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  </aside>
  
  {/* Main Content */}
  <main className="flex-1 flex flex-col">
    {/* Query Builder */}
    <div className="border-b p-4">
      <Tabs defaultValue="visual">
        <TabsList>
          <TabsTrigger value="visual">Visual Query Builder</TabsTrigger>
          <TabsTrigger value="sql">SQL Query</TabsTrigger>
        </TabsList>
        
        <TabsContent value="visual">
          <VisualQueryBuilder
            selectedColumns={selectedColumns}
            filters={queryFilters}
            groupBy={groupBy}
            orderBy={orderBy}
            onUpdate={updateQuery}
          />
        </TabsContent>
        
        <TabsContent value="sql">
          <CodeEditor
            language="sql"
            value={sqlQuery}
            onChange={setSqlQuery}
            height="200px"
          />
        </TabsContent>
      </Tabs>
      
      <div className="flex gap-2 mt-4">
        <Button onClick={executeQuery}>
          <Play className="w-4 h-4 mr-2" />
          Executar Query
        </Button>
        <Button variant="outline" onClick={saveQuery}>
          <Save className="w-4 h-4 mr-2" />
          Salvar Query
        </Button>
        <Button variant="outline" onClick={exportData}>
          <Download className="w-4 h-4 mr-2" />
          Exportar
        </Button>
      </div>
    </div>
    
    {/* Results */}
    <div className="flex-1 overflow-auto p-4">
      {loading ? (
        <div className="flex items-center justify-center h-full">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="mb-4 flex items-center gap-4 text-sm text-gray-600">
            <span>{results.length} rows</span>
            <span>•</span>
            <span>{selectedColumns.length} columns</span>
            <span>•</span>
            <span>Query time: {queryTime}ms</span>
          </div>
          
          {/* Data Table */}
          <DataTable
            columns={selectedColumns}
            data={results}
            sortable
            filterable
            exportable
          />
          
          {/* Visualizations */}
          {showViz && (
            <div className="mt-6">
              <h3 className="font-bold mb-4">Visualizações</h3>
              <div className="grid grid-cols-2 gap-4">
                <ChartBuilder data={results} />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  </main>
</div>
```

### **3.2 Visual Query Builder**

```tsx
// components/DataExplorer/VisualQueryBuilder.tsx
<div className="space-y-4">
  {/* SELECT - Colunas */}
  <div>
    <Label>Colunas Selecionadas</Label>
    <div className="flex flex-wrap gap-2 mt-2">
      {selectedColumns.map(col => (
        <Badge key={col.name} variant="secondary">
          {col.name}
          <X
            className="w-3 h-3 ml-1 cursor-pointer"
            onClick={() => removeColumn(col)}
          />
        </Badge>
      ))}
    </div>
  </div>
  
  {/* WHERE - Filtros */}
  <div>
    <Label>Filtros</Label>
    <div className="space-y-2 mt-2">
      {filters.map((filter, idx) => (
        <div key={idx} className="flex gap-2 items-center">
          <Select value={filter.column} onValueChange={(val) => updateFilter(idx, 'column', val)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {availableColumns.map(col => (
                <SelectItem key={col.name} value={col.name}>
                  {col.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={filter.operator} onValueChange={(val) => updateFilter(idx, 'operator', val)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="=">=</SelectItem>
              <SelectItem value="!=">!=</SelectItem>
              <SelectItem value=">">></SelectItem>
              <SelectItem value="<"><</SelectItem>
              <SelectItem value=">=">>=</SelectItem>
              <SelectItem value="<="><=</SelectItem>
              <SelectItem value="LIKE">LIKE</SelectItem>
              <SelectItem value="IN">IN</SelectItem>
            </SelectContent>
          </Select>
          
          <Input
            value={filter.value}
            onChange={(e) => updateFilter(idx, 'value', e.target.value)}
            placeholder="Valor"
          />
          
          <Button
            variant="ghost"
            size="icon"
            onClick={() => removeFilter(idx)}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      ))}
      
      <Button variant="outline" size="sm" onClick={addFilter}>
        <Plus className="w-4 h-4 mr-2" />
        Adicionar Filtro
      </Button>
    </div>
  </div>
  
  {/* GROUP BY */}
  <div>
    <Label>Agrupar Por</Label>
    <MultiSelect
      options={availableColumns}
      value={groupBy}
      onChange={setGroupBy}
    />
  </div>
  
  {/* ORDER BY */}
  <div>
    <Label>Ordenar Por</Label>
    <div className="flex gap-2">
      <Select value={orderBy.column} onValueChange={(val) => setOrderBy({...orderBy, column: val})}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {availableColumns.map(col => (
            <SelectItem key={col.name} value={col.name}>
              {col.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      
      <Select value={orderBy.direction} onValueChange={(val) => setOrderBy({...orderBy, direction: val})}>
        <SelectTrigger className="w-32">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ASC">Crescente</SelectItem>
          <SelectItem value="DESC">Decrescente</SelectItem>
        </SelectContent>
      </Select>
    </div>
  </div>
  
  {/* LIMIT */}
  <div>
    <Label>Limite de Resultados</Label>
    <Input
      type="number"
      value={limit}
      onChange={(e) => setLimit(parseInt(e.target.value))}
      min={1}
      max={10000}
    />
  </div>
</div>
```

### **3.3 API Endpoint para Query Dinâmica**

```python
# backend/app/api/data_explorer.py

@router.post("/data-explorer/query")
def execute_query(
    query: DataExplorerQuery,
    db: Session = Depends(get_db)
):
    """
    Executa query dinâmica no banco de dados.
    """
    # Validar e sanitizar query
    allowed_tables = ['runs', 'citations', 'projects', 'engines']
    if query.table not in allowed_tables:
        raise HTTPException(400, "Invalid table")
    
    # Construir query SQL
    sql_parts = []
    
    # SELECT
    if query.columns:
        columns_str = ", ".join(query.columns)
    else:
        columns_str = "*"
    sql_parts.append(f"SELECT {columns_str}")
    
    # FROM
    sql_parts.append(f"FROM {query.table}")
    
    # WHERE
    if query.filters:
        where_clauses = []
        for f in query.filters:
            where_clauses.append(f"{f.column} {f.operator} :{f.column}")
        sql_parts.append(f"WHERE {' AND '.join(where_clauses)}")
    
    # GROUP BY
    if query.group_by:
        sql_parts.append(f"GROUP BY {', '.join(query.group_by)}")
    
    # ORDER BY
    if query.order_by:
        sql_parts.append(f"ORDER BY {query.order_by.column} {query.order_by.direction}")
    
    # LIMIT
    if query.limit:
        sql_parts.append(f"LIMIT {query.limit}")
    
    # Executar query
    sql = " ".join(sql_parts)
    params = {f.column: f.value for f in query.filters}
    
    start_time = time.time()
    result = db.execute(text(sql), params).fetchall()
    query_time = (time.time() - start_time) * 1000
    
    return {
        "sql": sql,
        "query_time_ms": query_time,
        "row_count": len(result),
        "data": [dict(row) for row in result]
    }
```

---

## 📤 **Fase 4: Exportação de Dados**

### **4.1 Componente de Exportação**

```tsx
// components/DataExplorer/ExportDialog.tsx
<Dialog>
  <DialogTrigger asChild>
    <Button variant="outline">
      <Download className="w-4 h-4 mr-2" />
      Exportar
    </Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Exportar Dados</DialogTitle>
    </DialogHeader>
    <div className="space-y-4">
      <div>
        <Label>Formato</Label>
        <RadioGroup value={format} onValueChange={setFormat}>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="csv" id="csv" />
            <Label htmlFor="csv">CSV</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="json" id="json" />
            <Label htmlFor="json">JSON</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="excel" id="excel" />
            <Label htmlFor="excel">Excel</Label>
          </div>
        </RadioGroup>
      </div>
      
      <div>
        <Label>Incluir</Label>
        <div className="space-y-2">
          <Checkbox checked={includeHeaders} onCheckedChange={setIncludeHeaders}>
            Cabeçalhos
          </Checkbox>
          <Checkbox checked={includeMetadata} onCheckedChange={setIncludeMetadata}>
            Metadados (data, filtros, etc)
          </Checkbox>
        </div>
      </div>
      
      <Button onClick={handleExport} className="w-full">
        Exportar {results.length} linhas
      </Button>
    </div>
  </DialogContent>
</Dialog>
```

### **4.2 API Endpoint para Exportação**

```python
# backend/app/api/export.py

@router.post("/export/{format}")
def export_data(
    format: str,
    query: DataExplorerQuery,
    db: Session = Depends(get_db)
):
    """
    Exporta dados em diferentes formatos.
    """
    # Executar query
    results = execute_query_internal(query, db)
    
    if format == "csv":
        # Gerar CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"}
        )
    
    elif format == "json":
        return JSONResponse(content=results)
    
    elif format == "excel":
        # Gerar Excel
        output = io.BytesIO()
        df = pd.DataFrame(results)
        df.to_excel(output, index=False)
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=export.xlsx"}
        )
```

---

## 🎨 **Fase 5: Visualizações**

### **5.1 Chart Builder**

```tsx
// components/DataExplorer/ChartBuilder.tsx
<Card>
  <CardHeader>
    <CardTitle>Criar Visualização</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      <div>
        <Label>Tipo de Gráfico</Label>
        <Select value={chartType} onValueChange={setChartType}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="line">Linha</SelectItem>
            <SelectItem value="bar">Barra</SelectItem>
            <SelectItem value="pie">Pizza</SelectItem>
            <SelectItem value="scatter">Dispersão</SelectItem>
            <SelectItem value="heatmap">Heatmap</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      <div>
        <Label>Eixo X</Label>
        <Select value={xAxis} onValueChange={setXAxis}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {columns.map(col => (
              <SelectItem key={col} value={col}>{col}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      
      <div>
        <Label>Eixo Y</Label>
        <Select value={yAxis} onValueChange={setYAxis}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {columns.map(col => (
              <SelectItem key={col} value={col}>{col}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      
      <Button onClick={generateChart}>Gerar Gráfico</Button>
    </div>
    
    {chart && (
      <div className="mt-6">
        <ResponsiveContainer width="100%" height={300}>
          {renderChart()}
        </ResponsiveContainer>
      </div>
    )}
  </CardContent>
</Card>
```

---

## 📅 **Cronograma de Implementação**

| Fase | Tarefa | Tempo Estimado |
|------|--------|----------------|
| 1 | Dashboard Melhorado | 2-3 dias |
| 2 | Filtros Avançados | 1-2 dias |
| 3 | Data Explorer | 3-4 dias |
| 4 | Exportação | 1 dia |
| 5 | Visualizações | 2 dias |
| **Total** | | **9-12 dias** |

---

## 🚀 **Priorização**

### **Alta Prioridade**
1. ✅ Dashboard com métricas IM
2. ✅ Filtros básicos (projeto, data)
3. ✅ Tabela de dados com paginação

### **Média Prioridade**
4. Data Explorer visual
5. Exportação CSV/JSON
6. Gráficos básicos

### **Baixa Prioridade**
7. SQL Editor
8. Visualizações avançadas
9. Salvamento de queries

---

**Quer que eu comece a implementar agora? Por qual fase prefere começar?** 🚀
