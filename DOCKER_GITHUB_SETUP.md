# 🐳 Docker + GitHub Actions: Como Funciona

## 🔍 **Situação Atual Configurada:**

### ✅ **Desenvolvimento Local (SQLite)**
- **Dockerfile**: `backend/Dockerfile` (sem Azure SQL)
- **Dependências**: `requirements_basic.txt` (compatível com SQLite)
- **Banco**: SQLite local (`app.db`)
- **Comando**: `docker compose up`

### ✅ **Produção (Azure SQL/PostgreSQL)**
- **Dockerfile**: `backend/Dockerfile.prod` (com Azure SQL)
- **Dependências**: `requirements.txt` (completo)
- **Banco**: Azure SQL ou PostgreSQL (via `DATABASE_URL`)
- **Comando**: `docker compose -f docker-compose.prod.yml up`

### ✅ **GitHub Actions**
- **Teste Local**: Executa antes de cada deploy
- **Deploy**: Só executa se os testes passarem
- **Ambiente**: Oracle Cloud (produção)

## 🚀 **Como Funciona o Fluxo:**

### 1. **Desenvolvimento Local**
```bash
# Usar SQLite local
cd backend
source venv/bin/activate
python run_local.py

# Ou usar Docker (SQLite)
docker compose up
```

### 2. **Commit e Push**
```bash
git add .
git commit -m "Nova funcionalidade"
git push origin main
```

### 3. **GitHub Actions Executa**
- ✅ **Testa ambiente local** (SQLite)
- ✅ **Testa Docker builds** (local + produção)
- ✅ **Se tudo passar**: Deploy para produção

### 4. **Deploy em Produção**
- 🚀 **Build** da imagem Docker de produção
- 🚀 **Deploy** no Oracle Cloud
- 🚀 **Usa Azure SQL/PostgreSQL** (não SQLite)

## 🔧 **Arquivos de Configuração:**

| Arquivo | Propósito | Ambiente |
|---------|-----------|----------|
| `Dockerfile` | Desenvolvimento local | SQLite |
| `Dockerfile.prod` | Produção | Azure SQL |
| `requirements_basic.txt` | Dependências locais | SQLite |
| `requirements.txt` | Dependências completas | Azure SQL |
| `docker-compose.yml` | Desenvolvimento | SQLite |
| `docker-compose.prod.yml` | Produção | Azure SQL |

## 📋 **Workflows GitHub Actions:**

### **`test-local.yml`**
- Executa em Pull Requests
- Testa ambiente local
- Testa Docker builds
- **Não faz deploy**

### **`deploy.yml`**
- Executa em push para main/production
- **Primeiro**: Testa local (`needs: test-local`)
- **Depois**: Deploy para produção
- **Só executa se testes passarem**

## 🎯 **Vantagens desta Configuração:**

✅ **Desenvolvimento Rápido**: SQLite local sem dependências externas
✅ **Testes Automáticos**: GitHub Actions testa antes de cada deploy
✅ **Produção Robusta**: Azure SQL/PostgreSQL para produção
✅ **Sem Conflitos**: Ambientes separados e bem definidos
✅ **Deploy Seguro**: Só faz deploy se tudo estiver funcionando

## 🚨 **Pontos de Atenção:**

### **Desenvolvimento Local**
- Use `requirements_basic.txt` para evitar problemas de compilação
- SQLite é suficiente para desenvolvimento
- Docker local usa SQLite por padrão

### **Produção**
- Sempre usa `requirements.txt` completo
- Sempre usa Azure SQL/PostgreSQL
- Docker de produção tem todas as dependências

### **GitHub Actions**
- Testa AMBOS os ambientes antes do deploy
- Deploy só acontece se testes passarem
- Ambiente de teste é isolado

## 🔄 **Fluxo Completo:**

```
1. Desenvolver localmente (SQLite)
   ↓
2. Commit e Push para GitHub
   ↓
3. GitHub Actions testa local
   ↓
4. GitHub Actions testa Docker builds
   ↓
5. Se tudo OK: Deploy para produção
   ↓
6. Produção usa Azure SQL/PostgreSQL
```

## 💡 **Dicas de Uso:**

### **Para Desenvolvimento:**
```bash
# Opção 1: Python direto (SQLite)
cd backend
source venv/bin/activate
python run_local.py

# Opção 2: Docker (SQLite)
docker compose up
```

### **Para Testar Produção:**
```bash
# Testar Docker de produção localmente
cd backend
docker build -f Dockerfile.prod -t test-prod .
```

### **Para Debug:**
```bash
# Ver logs do GitHub Actions
# Verificar se testes passaram
# Verificar se Docker builds funcionaram
```

---

🎉 **Resultado**: Agora você tem o melhor dos dois mundos: desenvolvimento rápido com SQLite local E produção robusta com Azure SQL, tudo testado automaticamente pelo GitHub Actions!