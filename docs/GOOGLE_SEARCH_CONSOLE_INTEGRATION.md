# 🔌 Google Search Console - Plano de Integração

## 🎯 **Objetivo**

Integrar Google Search Console API para obter dados reais de:
- **CTR Real** (vs CTR esperado)
- **Impressões**
- **Cliques**
- **Posição média**
- **IRZC com dados reais**

---

## 📊 **Dados Disponíveis no Search Console**

### **Search Analytics API**

```python
{
  "query": "melhor banco 2025",
  "page": "https://exemplo.com/artigo",
  "clicks": 150,
  "impressions": 5000,
  "ctr": 0.03,  # 3%
  "position": 5.2
}
```

### **Métricas Derivadas**

```python
# CTR Ratio
ctr_expected = sistrix_curve[position]  # 7.2% para posição 5
ctr_real = 3.0%  # Do Search Console
ctr_ratio = ctr_real / ctr_expected  # 0.42 (42% do esperado)

# IRZC Score
if ctr_ratio < 0.5:
    irzc_score = 20  # Alto risco de zero-click
elif ctr_ratio < 0.8:
    irzc_score = 50  # Risco moderado
else:
    irzc_score = 80  # Baixo risco
```

---

## 🏗️ **Arquitetura da Implementação**

### **Fase 1: Autenticação OAuth2** (1 dia)

#### **1.1 Criar Credenciais no Google Cloud**
```bash
1. Acessar: https://console.cloud.google.com/
2. Criar projeto: "SEO Analyzer"
3. Ativar API: "Google Search Console API"
4. Criar credenciais OAuth 2.0
5. Configurar redirect URI: http://localhost:8000/api/search-console/callback
```

#### **1.2 Backend - Endpoint de Autenticação**

**Arquivo**: `backend/app/api/search_console.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

router = APIRouter(prefix="/api/search-console", tags=["search-console"])

# Configuração OAuth2
CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uris": ["http://localhost:8000/api/search-console/callback"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

@router.get("/connect")
def connect_search_console(project_id: str, db: Session = Depends(get_db)):
    """Inicia fluxo OAuth2 para conectar Search Console."""
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/search-console/callback"
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=project_id  # Passar project_id no state
    )
    
    return {"authorization_url": authorization_url}

@router.get("/callback")
def oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Callback OAuth2 - salva credenciais."""
    project_id = state
    
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/search-console/callback"
    )
    
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # Salvar credenciais no projeto
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    
    # Armazenar token (criptografado)
    project.search_console_token = encrypt_token(credentials.to_json())
    project.search_console_connected_at = datetime.utcnow()
    db.commit()
    
    return {"status": "connected", "project_id": project_id}
```

#### **1.3 Modelo - Adicionar Campos**

**Arquivo**: `backend/app/models/models.py`

```python
class Project(Base):
    # ... campos existentes ...
    
    # Google Search Console
    search_console_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    search_console_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    search_console_site_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
```

---

### **Fase 2: Buscar Dados do Search Console** (1 dia)

#### **2.1 Serviço de Busca**

**Arquivo**: `backend/app/services/search_console.py`

```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta

class SearchConsoleService:
    """Serviço para buscar dados do Google Search Console."""
    
    @staticmethod
    def get_query_data(
        credentials_json: str,
        site_url: str,
        query: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """
        Busca dados de uma query específica.
        
        Returns:
            {
                "clicks": 150,
                "impressions": 5000,
                "ctr": 0.03,
                "position": 5.2
            }
        """
        credentials = Credentials.from_authorized_user_info(
            json.loads(decrypt_token(credentials_json))
        )
        
        service = build('searchconsole', 'v1', credentials=credentials)
        
        request = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'dimensions': ['query'],
            'dimensionFilterGroups': [{
                'filters': [{
                    'dimension': 'query',
                    'expression': query,
                    'operator': 'equals'
                }]
            }],
            'rowLimit': 1
        }
        
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body=request
        ).execute()
        
        if 'rows' in response and len(response['rows']) > 0:
            row = response['rows'][0]
            return {
                "clicks": row.get('clicks', 0),
                "impressions": row.get('impressions', 0),
                "ctr": row.get('ctr', 0.0),
                "position": row.get('position', 0.0)
            }
        
        return {
            "clicks": 0,
            "impressions": 0,
            "ctr": 0.0,
            "position": 0.0
        }
```

#### **2.2 Integração no Cálculo de Métricas**

**Arquivo**: `backend/app/services/tasks.py`

```python
# Após calcular métricas IM
if project and project.search_console_token:
    try:
        # Buscar dados do Search Console
        gsc_data = SearchConsoleService.get_query_data(
            credentials_json=project.search_console_token,
            site_url=project.search_console_site_url,
            query=run.query,  # Query da run
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow()
        )
        
        # Atualizar run com dados reais
        run.ctr_real = gsc_data['ctr'] * 100  # Converter para %
        
        if run.ctr_expected and run.ctr_real:
            run.ctr_ratio = run.ctr_real / run.ctr_expected
            
            # Recalcular IRZC com dados reais
            run.irzc_score = calculate_irzc_with_real_data(
                ctr_ratio=run.ctr_ratio,
                zero_click_features=serp_metrics.get('ia_resources_detected', 0)
            )
        
        db.commit()
        _log(db, run.id, "search_console", "ok", f"CTR Real: {run.ctr_real}%")
        
    except Exception as e:
        _log(db, run.id, "search_console", "fail", f"Error: {str(e)}")
```

---

### **Fase 3: Cálculo de IRZC com Dados Reais** (0.5 dia)

#### **3.1 Nova Fórmula de IRZC**

**Arquivo**: `backend/app/services/im_metrics_simple.py`

```python
@staticmethod
def calculate_irzc_with_real_data(ctr_ratio: float, zero_click_features: int) -> float:
    """
    Calcula IRZC com dados reais do Search Console.
    
    Args:
        ctr_ratio: CTR real / CTR esperado (0.0 - 2.0+)
        zero_click_features: Número de features de IA na SERP
        
    Returns:
        Score 0-100 (quanto maior, menor o risco de zero-click)
    """
    # Base score pelo CTR ratio
    if ctr_ratio >= 1.0:
        base_score = 90  # CTR igual ou melhor que esperado
    elif ctr_ratio >= 0.8:
        base_score = 70  # CTR próximo do esperado
    elif ctr_ratio >= 0.5:
        base_score = 50  # CTR moderadamente abaixo
    elif ctr_ratio >= 0.3:
        base_score = 30  # CTR muito abaixo
    else:
        base_score = 10  # CTR crítico
    
    # Penalizar por features de zero-click
    if zero_click_features > 0:
        penalty = min(30, zero_click_features * 10)
        base_score = max(0, base_score - penalty)
    
    return round(base_score, 2)
```

---

### **Fase 4: Frontend** (1 dia)

#### **4.1 Botão de Conexão**

**Arquivo**: `frontend/src/components/ProjectSettings.tsx`

```tsx
const connectSearchConsole = async () => {
  const response = await fetch(`/api/search-console/connect?project_id=${projectId}`);
  const data = await response.json();
  
  // Abrir popup OAuth
  window.open(data.authorization_url, 'Google Search Console', 'width=600,height=600');
};

return (
  <Card>
    <CardHeader>
      <CardTitle>Google Search Console</CardTitle>
    </CardHeader>
    <CardContent>
      {project.search_console_connected_at ? (
        <div className="flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-500" />
          <span>Conectado em {formatDate(project.search_console_connected_at)}</span>
        </div>
      ) : (
        <Button onClick={connectSearchConsole}>
          <Link className="w-4 h-4 mr-2" />
          Conectar Search Console
        </Button>
      )}
    </CardContent>
  </Card>
);
```

#### **4.2 Exibição de Métricas**

```tsx
<Card>
  <CardHeader>
    <CardTitle>IRZC - Índice de Resistência Zero-Click</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      <div className="flex justify-between">
        <span>Score IRZC</span>
        <Badge variant={getIRZCBadge(run.irzc_score)}>
          {run.irzc_score}
        </Badge>
      </div>
      
      {run.ctr_real && (
        <>
          <div className="flex justify-between">
            <span>CTR Esperado</span>
            <span>{run.ctr_expected}%</span>
          </div>
          <div className="flex justify-between">
            <span>CTR Real</span>
            <span className="font-bold">{run.ctr_real}%</span>
          </div>
          <div className="flex justify-between">
            <span>Ratio</span>
            <Badge variant={getCTRRatioBadge(run.ctr_ratio)}>
              {(run.ctr_ratio * 100).toFixed(0)}%
            </Badge>
          </div>
        </>
      )}
    </CardContent>
  </Card>
);
```

---

## 📦 **Dependências**

### **Backend**

```txt
# requirements.txt
google-auth==2.23.0
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.100.0
cryptography==41.0.5  # Para criptografar tokens
```

### **Variáveis de Ambiente**

```bash
# .env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
ENCRYPTION_KEY=your_encryption_key_here  # Para criptografar tokens
```

---

## 🧪 **Testes**

### **1. Teste de Autenticação**
```bash
curl http://localhost:8000/api/search-console/connect?project_id=prj_xxx
```

### **2. Teste de Busca de Dados**
```python
# test_search_console.py
data = SearchConsoleService.get_query_data(
    credentials_json=token,
    site_url="https://exemplo.com",
    query="melhor banco 2025",
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now()
)
print(f"CTR: {data['ctr']}, Clicks: {data['clicks']}")
```

---

## 📊 **Estimativa de Tempo**

| Fase | Tarefa | Tempo |
|------|--------|-------|
| 1 | OAuth2 + Credenciais | 1 dia |
| 2 | Buscar dados GSC | 1 dia |
| 3 | IRZC com dados reais | 0.5 dia |
| 4 | Frontend | 1 dia |
| **Total** | | **3.5 dias** |

---

## 🎯 **Checklist de Implementação**

### **Backend**
- [ ] Criar credenciais no Google Cloud
- [ ] Implementar OAuth2 flow
- [ ] Adicionar campos no modelo Project
- [ ] Criar SearchConsoleService
- [ ] Integrar no cálculo de métricas
- [ ] Implementar criptografia de tokens
- [ ] Adicionar endpoints na API

### **Frontend**
- [ ] Botão de conexão
- [ ] Popup OAuth
- [ ] Exibição de status
- [ ] Métricas de CTR real
- [ ] Badge de IRZC

### **Testes**
- [ ] Teste de autenticação
- [ ] Teste de busca de dados
- [ ] Teste de cálculo de IRZC
- [ ] Teste end-to-end

---

## 🚀 **Próximos Passos Imediatos**

1. ✅ Adicionar campos `organic_position` e `competitors_top10` na API
2. ✅ Rebuild backend
3. 🔄 Criar credenciais no Google Cloud
4. 🔄 Implementar OAuth2
5. 🔄 Testar com dados reais

---

**Última atualização**: 2025-01-30  
**Versão**: 1.0
