# 🎯 Core Web Vitals - Mudança de Mock para Null

## 📊 **Mudança Implementada**

### **Antes (Mock)**
```python
core_web_vitals_score = 75.0  # Sempre, mesmo sem medir
```

### **Depois (Null)** ✅
```python
core_web_vitals_score = None  # Quando não medido
core_web_vitals_score = 74.32  # Quando medido via PageSpeed API
```

---

## 🎯 **Por Que a Mudança?**

### **Problemas do Mock**
1. ❌ **Distorce métricas**: IM-SEO inflacionado artificialmente
2. ❌ **Impossível distinguir**: "Não medido" vs "Score médio"
3. ❌ **Análises erradas**: Médias incluem valores falsos
4. ❌ **Falsa sensação**: Parece que está tudo OK quando não está

### **Benefícios do Null**
1. ✅ **Honestidade**: Deixa claro que não foi medido
2. ✅ **Análises corretas**: Médias só consideram valores reais
3. ✅ **Transparência**: Frontend pode mostrar "Não disponível"
4. ✅ **Incentivo**: Motiva a cadastrar domínios para medir

---

## 📐 **Ajustes nas Fórmulas**

### **IM-SEO**

#### **Com Core Web Vitals**
```python
IM-SEO = (Autoridade + Lighthouse + Share×2 + Engajamento) / 5
```

#### **Sem Core Web Vitals** (Ajustado)
```python
IM-SEO = (Autoridade + Share×2 + Engajamento) / 4
```
**Nota**: Remove lighthouse do numerador E denominador para não distorcer

### **IM-SEOIA**

#### **Com Core Web Vitals**
```python
IM-SEOIA = 
    Lighthouse × 10% +
    Share × 15% +
    IA SERP × 15% +
    Long-tail × 15% +
    E-E-A-T × 15% +
    Entities × 10% +
    Schema × 10% +
    IA-Ready × 10%
```

#### **Sem Core Web Vitals** (Ajustado)
```python
IM-SEOIA = 
    Share × 17% (+2%) +
    IA SERP × 17% (+2%) +
    Long-tail × 17% (+2%) +
    E-E-A-T × 17% (+2%) +
    Entities × 11% (+1%) +
    Schema × 11% (+1%) +
    IA-Ready × 10%
```
**Nota**: Redistribui os 10% do Lighthouse entre outras métricas

---

## 📊 **Comportamento Esperado**

### **Cenário 1: Sem Domínios Cadastrados**
```json
{
  "core_web_vitals_score": null,
  "lcp_score": null,
  "fid_score": null,
  "cls_score": null,
  "im_seo_score": 52.5,  // Calculado sem CWV
  "im_seoia_score": 55.2  // Pesos redistribuídos
}
```

### **Cenário 2: Com Domínio mas Sem Citação**
```json
{
  "core_web_vitals_score": null,
  "lcp_score": null,
  "fid_score": null,
  "cls_score": null,
  "im_seo_score": 52.5,
  "im_seoia_score": 55.2
}
```

### **Cenário 3: Com Citação do Projeto** ✅
```json
{
  "core_web_vitals_score": 74.32,  // Real!
  "lcp_score": 22.96,
  "fid_score": 37.67,
  "cls_score": 100.0,
  "im_seo_score": 58.5,  // Com CWV real
  "im_seoia_score": 62.8  // Com CWV real
}
```

---

## 🎨 **Frontend - Como Exibir**

### **Recomendações de UI**

#### **Quando null**
```jsx
{core_web_vitals_score === null ? (
  <Badge variant="secondary">
    <AlertCircle className="w-4 h-4" />
    Não disponível
  </Badge>
) : (
  <Badge variant={getScoreBadge(core_web_vitals_score)}>
    {core_web_vitals_score}
  </Badge>
)}
```

#### **Tooltip Explicativo**
```
Core Web Vitals: Não disponível

Para medir Core Web Vitals:
1. Cadastre domínios do projeto
2. Crie queries que citem seus domínios
3. PageSpeed será chamado automaticamente
```

#### **Call-to-Action**
```jsx
{core_web_vitals_score === null && (
  <Alert>
    <Info className="w-4 h-4" />
    <AlertTitle>Melhore suas métricas</AlertTitle>
    <AlertDescription>
      Cadastre domínios do projeto para medir Core Web Vitals reais
      <Button variant="link">Cadastrar domínios</Button>
    </AlertDescription>
  </Alert>
)}
```

---

## 📈 **Análises e Relatórios**

### **Cálculo de Médias**
```python
# Correto: Ignora valores null
cwv_scores = [r.core_web_vitals_score for r in runs 
              if r.core_web_vitals_score is not None]

if cwv_scores:
    avg_cwv = sum(cwv_scores) / len(cwv_scores)
else:
    avg_cwv = None  # Ou "N/A"
```

### **Gráficos**
```python
# Mostrar apenas valores reais
data = [
    {"date": r.created_at, "cwv": r.core_web_vitals_score}
    for r in runs
    if r.core_web_vitals_score is not None
]
```

### **Comparações**
```python
# Indicar quando não há dados
if run.core_web_vitals_score is None:
    status = "Não medido"
elif run.core_web_vitals_score >= 90:
    status = "Excelente"
elif run.core_web_vitals_score >= 75:
    status = "Bom"
else:
    status = "Precisa melhorar"
```

---

## 🔄 **Migração de Dados Antigos**

### **Runs Antigas com Mock (75.0)**

**Opção 1: Manter como está**
- Runs antigas mantêm 75.0
- Novas runs terão null ou valor real
- Análises devem filtrar por data

**Opção 2: Limpar valores mock**
```sql
-- Zerar valores mock de runs sem citações do projeto
UPDATE runs 
SET 
  core_web_vitals_score = NULL,
  lcp_score = NULL,
  fid_score = NULL,
  cls_score = NULL
WHERE 
  core_web_vitals_score = 75.0
  AND lcp_score IS NULL  -- Indica que era mock
  AND created_at < '2025-01-30';  -- Antes da mudança
```

**Recomendação**: Opção 2 para consistência

---

## 🎯 **Checklist de Implementação**

### **Backend** ✅
- [x] Remover mock (75.0)
- [x] Retornar None quando sem URL
- [x] Ajustar IM-SEO para lidar com None
- [x] Ajustar IM-SEOIA para lidar com None
- [x] Logs informativos

### **Frontend** (Próximo)
- [ ] Exibir "Não disponível" quando null
- [ ] Tooltip explicativo
- [ ] Call-to-action para cadastrar domínios
- [ ] Filtrar nulls em gráficos
- [ ] Médias corretas (ignorar nulls)

### **Documentação** ✅
- [x] Documentar mudança
- [x] Explicar comportamento
- [x] Guia de UI
- [x] Exemplos de código

---

## 📞 **FAQ**

### **P: Por que não usar 0 ao invés de null?**
**R**: Zero indica "performance péssima", null indica "não medido". São coisas diferentes!

### **P: IM-SEO fica menor sem Core Web Vitals?**
**R**: Não! A fórmula é ajustada para manter proporção correta.

### **P: Como forçar medição de Core Web Vitals?**
**R**: 
1. Cadastre domínios do projeto
2. Crie queries que citem esses domínios
3. PageSpeed será chamado automaticamente

### **P: Posso desabilitar PageSpeed?**
**R**: Sim, basta não cadastrar domínios. Core Web Vitals será sempre null.

### **P: Quanto tempo demora o PageSpeed?**
**R**: 10-30 segundos por URL. É assíncrono, não bloqueia.

---

## 🚀 **Próximos Passos**

1. **Testar com run real** que tenha citação do projeto
2. **Atualizar frontend** para exibir null corretamente
3. **Limpar dados antigos** (opcional)
4. **Monitorar taxa de sucesso** do PageSpeed

---

**Última atualização**: 2025-01-30  
**Versão**: 2.1
