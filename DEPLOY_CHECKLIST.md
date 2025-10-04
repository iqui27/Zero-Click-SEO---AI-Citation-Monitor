# 📋 Checklist de Deploy - SEO Analyzer

**Última atualização:** 2025-10-04

## ✅ Configurações que SE MANTÊM entre deploys

### 1. Arquivo `.env` no Servidor
**Localização:** `/opt/seo-analyzer/.env`

**Status:** ✅ Persistente (não é sobrescrito)

**Variáveis configuradas:**
```bash
DATABASE_URL=mssql+pyodbc://...
PERPLEXITY_API_KEY=pplx-njzY3TBIvd...
OPENAI_API_KEY=sk-proj-1g-E2Iq...
GOOGLE_API_KEY=AIzaSyDo8hbI673...
SERPAPI_KEY=45731e73a6d6531...
PAGESPEED_API_KEY=AIzaSyCs5YI1zEiKeLWlTrJsj...  ← NOVA!
```

**Por que se mantém:**
- O arquivo `.env` está no `.gitignore`
- Deploy via rsync usa `--exclude '.env'`
- Nunca é sobrescrito automaticamente

### 2. Dados do Banco (Azure SQL)
**Status:** ✅ Persistente

- Projetos
- Runs e métricas
- Domínios configurados
- Todas as tabelas

### 3. Volumes Docker
**Status:** ✅ Persistente

- Logs
- Cache do Redis (se configurado com volume)

---

## ⚠️ O que PODE ser sobrescrito em deploy

### 1. Código da Aplicação
**Status:** ⚠️ Sobrescrito

- `backend/` - Todo código Python
- `frontend/` - Todo código React
- `docker-compose.prod.yml`

**Solução:** Sempre commitar mudanças importantes

### 2. Containers Docker
**Status:** ⚠️ Recriados

- Containers são reconstruídos
- Variáveis de ambiente são recarregadas do `.env`

**Solução:** Garantir que `.env` está atualizado antes do deploy

---

## 🚀 Processo de Deploy Seguro

### Opção 1: Deploy Manual (Atual)

```bash
# 1. No local - Commitar mudanças
git add .
git commit -m "feat: nova funcionalidade"
git push origin POC

# 2. No servidor - Copiar arquivos
scp -i "~/.ssh/oci_ed25519" backend/app/... ubuntu@129.148.63.199:/opt/seo-analyzer/...

# 3. No servidor - Reiniciar serviços
ssh -i "~/.ssh/oci_ed25519" ubuntu@129.148.63.199
cd /opt/seo-analyzer
sudo docker compose -f docker-compose.prod.yml restart api worker

# ✅ .env NÃO é afetado
```

### Opção 2: Deploy com Script (Recomendado)

```bash
# No local
./scripts/deploy.sh

# O script já está configurado para:
# - Fazer rsync excluindo .env
# - Manter configurações do servidor
# - Reiniciar apenas serviços necessários
```

**Importante:** O script `deploy.sh` usa:
```bash
rsync --exclude '.env' --exclude 'node_modules' ...
```

---

## 🔐 Backup de Configurações Críticas

### Criar Backup do .env (Recomendado)

```bash
# No servidor
ssh -i "~/.ssh/oci_ed25519" ubuntu@129.148.63.199
cd /opt/seo-analyzer
sudo cp .env .env.backup.$(date +%Y%m%d)

# Verificar
ls -la .env*
```

### Restaurar .env se necessário

```bash
# No servidor
cd /opt/seo-analyzer
sudo cp .env.backup.YYYYMMDD .env
sudo docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 📝 Checklist Pré-Deploy

### Antes de fazer deploy:

- [ ] Código commitado e pushed
- [ ] Testes locais passando
- [ ] `.env` local atualizado (para referência)
- [ ] Backup do `.env` do servidor criado (opcional)

### Durante o deploy:

- [ ] Copiar apenas arquivos necessários
- [ ] **NÃO copiar** `.env` para o servidor
- [ ] Reiniciar serviços (restart ou up -d)

### Após o deploy:

- [ ] Verificar se API keys ainda estão configuradas
- [ ] Testar endpoints críticos
- [ ] Verificar logs para erros

---

## 🧪 Verificação Pós-Deploy

### 1. Verificar API Keys

```bash
ssh -i "~/.ssh/oci_ed25519" ubuntu@129.148.63.199
cd /opt/seo-analyzer
sudo docker compose -f docker-compose.prod.yml exec -T api python -c "
import os
print('PERPLEXITY:', '✅' if os.getenv('PERPLEXITY_API_KEY') else '❌')
print('OPENAI:', '✅' if os.getenv('OPENAI_API_KEY') else '❌')
print('GOOGLE:', '✅' if os.getenv('GOOGLE_API_KEY') else '❌')
print('SERPAPI:', '✅' if os.getenv('SERPAPI_KEY') else '❌')
print('PAGESPEED:', '✅' if os.getenv('PAGESPEED_API_KEY') else '❌')
"
```

**Resultado esperado:**
```
PERPLEXITY: ✅
OPENAI: ✅
GOOGLE: ✅
SERPAPI: ✅
PAGESPEED: ✅
```

### 2. Testar Endpoints

```bash
# Health check
curl http://129.148.63.199/api/projects

# Executar uma run de teste
# Verificar se Core Web Vitals é calculado
```

### 3. Verificar Logs

```bash
sudo docker compose -f docker-compose.prod.yml logs -f worker | grep -E "PAGESPEED|Core Web Vitals"
```

---

## 🔄 Cenários de Deploy

### Cenário 1: Deploy de Código (Comum)
**O que muda:** Código Python/React  
**O que mantém:** `.env`, banco de dados  
**Ação:** Copiar arquivos + restart

### Cenário 2: Atualização de Dependências
**O que muda:** `requirements.txt`, `package.json`  
**O que mantém:** `.env`, banco de dados  
**Ação:** Rebuild containers

```bash
sudo docker compose -f docker-compose.prod.yml build --no-cache
sudo docker compose -f docker-compose.prod.yml up -d
```

### Cenário 3: Nova API Key
**O que muda:** `.env`  
**O que mantém:** Código, banco de dados  
**Ação:** Editar `.env` + recreate containers

```bash
sudo nano .env  # Adicionar nova key
sudo docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### Cenário 4: Deploy Completo (Raro)
**O que muda:** Tudo  
**O que mantém:** Banco de dados (Azure SQL externo)  
**Ação:** Backup `.env` + deploy + restore `.env`

```bash
# Backup
sudo cp .env .env.backup

# Deploy completo
# ... copiar tudo ...

# Restore se necessário
sudo cp .env.backup .env
sudo docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 🎯 Resumo

### ✅ SE MANTÉM automaticamente:
- `.env` no servidor (API keys, DATABASE_URL)
- Banco de dados Azure SQL
- Volumes Docker persistentes

### ⚠️ Requer atenção:
- Código da aplicação (commitar antes)
- Containers (recriar se mudar .env)

### 🔐 Melhor prática:
1. **Nunca commitar** `.env` com secrets
2. **Sempre fazer backup** do `.env` do servidor antes de deploy
3. **Verificar API keys** após cada deploy
4. **Testar funcionalidades** críticas pós-deploy

---

## 📞 Em caso de problemas

### API Keys perdidas após deploy

```bash
# 1. Verificar se .env existe
cat /opt/seo-analyzer/.env | grep PAGESPEED

# 2. Se não existir, restaurar backup
sudo cp .env.backup .env

# 3. Recriar containers
sudo docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### Containers não carregam novas variáveis

```bash
# Sempre usar --force-recreate para recarregar .env
sudo docker compose -f docker-compose.prod.yml up -d --force-recreate api worker
```

---

**✅ Configuração atual está segura e persistente!**

A `PAGESPEED_API_KEY` está configurada e será mantida em futuros deploys, desde que o arquivo `.env` do servidor não seja sobrescrito.
