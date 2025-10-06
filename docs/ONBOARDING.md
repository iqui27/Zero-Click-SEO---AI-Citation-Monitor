# Guia de Onboarding - Novos Desenvolvedores

Bem-vindo ao time! Este guia vai te ajudar a começar rapidamente no projeto Zero-Click SEO Monitor.

---

## 🚀 Quick Start (15 minutos)

### 1. Pré-requisitos

Instale no seu computador:
- **Docker Desktop** (versão 20+)
- **Git**
- **VS Code** (recomendado) ou sua IDE preferida
- **Node.js 18+** (opcional, para desenvolvimento frontend local)

### 2. Clone e Configure

```bash
# Clone o repositório
git clone <repository-url>
cd "SEO Analyzer"

# Configure Git (rebase on pull)
git config pull.rebase true
git config rebase.autoStash true

# Crie o arquivo .env
cp .env.example .env
```

### 3. Configure as API Keys

Edite o arquivo `.env` e adicione suas chaves:

```bash
# Obrigatório para funcionalidade completa
GOOGLE_API_KEY=sua_chave_gemini_aqui
OPENAI_API_KEY=sua_chave_openai_aqui

# Opcional
PERPLEXITY_API_KEY=sua_chave_perplexity
SERPAPI_KEY=sua_chave_serpapi

# Database (Azure SQL - já configurado)
DATABASE_URL=mssql+pyodbc://...
```

**Onde conseguir as chaves:**
- **Gemini**: https://aistudio.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys
  - Org ID: `org-cwSHSUpwENqGkjtok0zVm4cu`
  - Project ID: `proj_5KNRTmP5Ojg4fqdEBloLhile`
- **Perplexity**: https://www.perplexity.ai/settings/api
- **SerpAPI**: https://serpapi.com/manage-api-key

### 4. Suba o Ambiente

```bash
# Build e start todos os serviços
docker compose up -d --build

# Aguarde ~2 minutos para tudo inicializar
# Acompanhe os logs
docker compose logs -f backend
```

### 5. Acesse a Aplicação

- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 6. Teste Básico

1. Acesse o frontend
2. Clique em "Nova Run"
3. Selecione um projeto (ou crie um novo)
4. Escolha uma engine (ex: gemini-2.0-flash)
5. Digite um prompt de teste
6. Clique em "Executar"
7. Veja a execução em tempo real!

✅ **Pronto!** Você está rodando o sistema localmente.

---

## 📚 Próximos Passos (Primeira Semana)

### Dia 1: Familiarização

**Manhã:**
1. Leia o `README.md` (visão geral)
2. Explore a UI: Projects → Subprojects → Templates → Monitors → Runs
3. Crie um projeto de teste e execute algumas runs

**Tarde:**
1. Leia `DEVELOPER_GUIDE.md` (seções 1-5)
2. Explore o código:
   - Backend: `backend/app/main.py` (entry point)
   - Frontend: `frontend/src/App.tsx` (entry point)
3. Veja os logs em tempo real:
   ```bash
   docker compose logs -f backend worker
   ```

### Dia 2: Backend Deep Dive

**Manhã:**
1. Leia `ARCHITECTURE.md` (arquitetura do sistema)
2. Estude os modelos de dados: `backend/app/models/models.py`
3. Entenda os schemas: `backend/app/schemas/schemas.py`

**Tarde:**
1. Explore os endpoints: `backend/app/api/routes.py`
2. Entenda o fluxo de execução: `backend/app/services/tasks.py`
3. Veja os adapters: `backend/app/services/adapters/`

**Exercício prático:**
- Adicione um campo simples em Run (ex: `notes: str`)
- Exponha via API
- Teste no Swagger

### Dia 3: Frontend Deep Dive

**Manhã:**
1. Estude a estrutura: `frontend/src/components/`
2. Entenda o API client: `frontend/src/lib/api.ts`
3. Veja como funciona o SSE: `frontend/src/components/RunDetail.tsx`

**Tarde:**
1. Explore os componentes shadcn/ui: `frontend/src/components/ui/`
2. Entenda o roteamento: `frontend/src/main.tsx`
3. Veja o styling (TailwindCSS)

**Exercício prático:**
- Adicione um badge no RunCard mostrando o campo `notes` que você criou
- Teste no browser

### Dia 4: Serviços e Integrações

**Manhã:**
1. Estude os adapters: `backend/app/services/adapters/gemini.py`
2. Entenda o sistema de KPIs: `backend/app/services/kpis.py`
3. Veja o classificador: `backend/app/services/response_classifier.py`

**Tarde:**
1. Entenda o scheduler: `backend/app/services/scheduler.py`
2. Veja a geração de insights: `backend/app/services/insights.py`
3. Explore o Celery: `backend/celery_app.py`
4. Leia `docs/SEMANTIC_INSIGHTS.md` (pipeline de entidades/wordcloud via Gemini)
5. Rode um backfill local para entender o fluxo completo:
   ```bash
   docker compose exec backend bash -lc "PYTHONPATH=/app python scripts/backfill_semantic_insights.py --days 7"
   ```

**Exercício prático:**
- Execute um monitor manualmente
- Veja os logs do worker processando

### Dia 5: Primeira Feature

**Objetivo:** Implementar uma feature simples end-to-end.

**Sugestão de feature:**
- Adicionar campo `tags` (array de strings) em Run
- Permitir filtrar runs por tag
- Mostrar tags na UI

**Checklist:**
- [ ] Atualizar modelo (backend/app/models/models.py)
- [ ] Adicionar migração SQL (backend/app/main.py)
- [ ] Atualizar schema (backend/app/schemas/schemas.py)
- [ ] Adicionar filtro na API (backend/app/api/routes.py)
- [ ] Atualizar tipos TypeScript (frontend/src/lib/api.ts)
- [ ] Adicionar UI para tags (frontend/src/components/Runs.tsx)
- [ ] Testar localmente
- [ ] Criar PR

---

## 🛠️ Ferramentas e Comandos Úteis

### Docker

```bash
# Ver status dos containers
docker compose ps

# Logs de um serviço específico
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Reiniciar um serviço
docker compose restart backend

# Rebuild após mudanças no Dockerfile
docker compose up -d --build backend

# Acessar shell de um container
docker compose exec backend bash
docker compose exec frontend sh

# Parar tudo
docker compose down

# Parar e remover volumes (⚠️ apaga dados)
docker compose down -v
```

### Backend

```bash
# Acessar Python REPL no container
docker compose exec backend python

# Executar script Python
docker compose exec backend python scripts/classify_existing_runs.py

# Ver variáveis de ambiente
docker compose exec backend env | grep API_KEY

# Instalar nova dependência
docker compose exec backend pip install <package>
# Depois: docker compose exec backend pip freeze > requirements.txt
```

### Frontend

```bash
# Instalar nova dependência
docker compose exec frontend npm install <package>

# Rebuild
docker compose exec frontend npm run build

# Lint
docker compose exec frontend npm run lint
```

### Database

```bash
# Conectar ao Azure SQL (se tiver sqlcmd local)
sqlcmd -S seoanalyzer.database.windows.net \
  -U iqui27 -P <password> \
  -d SEO

# Query rápida
docker compose exec backend python -c "
from app.db.session import SessionLocal
from app.models.models import Run
db = SessionLocal()
runs = db.query(Run).limit(5).all()
for r in runs:
    print(f'{r.id} - {r.status}')
"
```

### Git

```bash
# Criar branch para feature
git checkout -b feature/minha-feature

# Commit com conventional commits
git commit -m "feat: adicionar campo tags em Run"
git commit -m "fix: corrigir cálculo de ZCRS"
git commit -m "docs: atualizar ONBOARDING.md"

# Push e criar PR
git push origin feature/minha-feature
# Depois: criar PR no GitHub/GitLab
```

---

## 🧪 Como Testar Suas Mudanças

### 1. Testes Manuais

**Backend:**
```bash
# 1. Acesse o Swagger
open http://localhost:8000/docs

# 2. Teste o endpoint que você modificou
# Exemplo: POST /api/runs
{
  "project_id": "prj_12345678",
  "prompt_version_id": "pv_87654321",
  "engines": [{"name": "gemini-2.0-flash"}]
}

# 3. Verifique a resposta e os logs
docker compose logs -f backend
```

**Frontend:**
```bash
# 1. Abra o browser
open http://localhost:5173

# 2. Abra o DevTools (F12)
# 3. Teste a funcionalidade
# 4. Veja console logs e network requests
```

### 2. Testes Automatizados (Futuro)

```bash
# Backend
cd backend
pytest tests/ -v

# Frontend
cd frontend
npm test
```

### 3. Smoke Tests

```bash
# Health check
curl http://localhost:8000/health

# List projects
curl http://localhost:8000/api/projects

# Create project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "country": "BR"}'
```

---

## 🐛 Debugging

### Backend

**Adicionar breakpoint:**
```python
# Em qualquer arquivo .py
import pdb; pdb.set_trace()

# Quando o código chegar aqui, você terá um REPL interativo
# Comandos úteis:
# - n (next): próxima linha
# - s (step): entrar na função
# - c (continue): continuar execução
# - p variavel: printar variável
# - l: ver código ao redor
```

**Logs detalhados:**
```python
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug(f"Run ID: {run_id}")
logger.info(f"Processing run: {run.id}")
logger.warning(f"Slow query: {duration}s")
logger.error(f"Adapter failed: {e}")
```

### Frontend

**Console logs:**
```typescript
console.log('Debug:', data)
console.table(runs)
console.error('Error:', error)
```

**React DevTools:**
- Instale a extensão no Chrome/Firefox
- Inspecione componentes e state
- Veja props e hooks

**Network tab:**
- Veja todas as requests HTTP
- Inspecione payloads e responses
- Veja timing

---

## 📖 Recursos de Aprendizado

### Documentação do Projeto

1. **README.md** - Visão geral e quick start
2. **DEVELOPER_GUIDE.md** - Guia completo do desenvolvedor
3. **ARCHITECTURE.md** - Arquitetura e padrões
4. **ZERO_CLICK_CLASSIFICATION.md** - Sistema de classificação
5. **ONBOARDING.md** - Este arquivo

### Documentação Externa

**Backend:**
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Celery Docs](https://docs.celeryq.dev/en/stable/)
- [Pydantic](https://docs.pydantic.dev/)

**Frontend:**
- [React Docs](https://react.dev/learn)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [TailwindCSS](https://tailwindcss.com/docs)
- [shadcn/ui](https://ui.shadcn.com/)

**APIs de IA:**
- [Gemini API](https://ai.google.dev/docs)
- [OpenAI API](https://platform.openai.com/docs)
- [Perplexity API](https://docs.perplexity.ai/)

### Vídeos e Tutoriais

- FastAPI Crash Course (YouTube)
- React + TypeScript Tutorial (YouTube)
- SQLAlchemy Tutorial (YouTube)
- Docker Compose Tutorial (YouTube)

---

## 🤝 Como Contribuir

### 1. Escolha uma Task

- Veja o board de issues/tasks
- Escolha algo marcado como "good first issue"
- Comente na issue que você vai trabalhar nela

### 2. Crie uma Branch

```bash
git checkout -b feature/nome-da-feature
# ou
git checkout -b fix/nome-do-bug
```

### 3. Desenvolva

- Faça commits pequenos e frequentes
- Use conventional commits
- Teste suas mudanças localmente

### 4. Crie um Pull Request

**Checklist antes de criar PR:**
- [ ] Código funciona localmente
- [ ] Sem erros no console/logs
- [ ] Código segue os padrões do projeto
- [ ] Adicionou comentários se necessário
- [ ] Atualizou documentação se necessário

**Template de PR:**
```markdown
## Descrição
[Descreva o que foi feito]

## Tipo de mudança
- [ ] Bug fix
- [ ] Nova feature
- [ ] Breaking change
- [ ] Documentação

## Como testar
1. [Passo 1]
2. [Passo 2]
3. [Passo 3]

## Screenshots (se aplicável)
[Adicione screenshots]

## Checklist
- [ ] Código testado localmente
- [ ] Documentação atualizada
- [ ] Sem warnings/errors
```

### 5. Code Review

- Aguarde review de outro desenvolvedor
- Responda aos comentários
- Faça ajustes se necessário
- Após aprovação, faça merge

---

## 🆘 Precisa de Ajuda?

### Problemas Comuns

**1. Docker não sobe:**
```bash
# Limpe tudo e tente novamente
docker compose down -v
docker system prune -a
docker compose up -d --build
```

**2. Backend não conecta ao banco:**
- Verifique DATABASE_URL no .env
- Veja logs: `docker compose logs backend`
- Consulte DEVELOPER_GUIDE.md seção Troubleshooting

**3. Frontend não carrega:**
```bash
# Limpe node_modules e reinstale
docker compose exec frontend rm -rf node_modules
docker compose restart frontend
```

**4. SSE não funciona:**
- Verifique se backend está rodando
- Abra Network tab no DevTools
- Veja se há erro de CORS

### Onde Pedir Ajuda

1. **Documentação**: Leia DEVELOPER_GUIDE.md e ARCHITECTURE.md
2. **Logs**: Sempre verifique os logs primeiro
3. **Time**: Pergunte no Slack/Teams
4. **Issues**: Crie uma issue no repositório

### Contatos

- **Tech Lead**: [nome@email.com]
- **Slack**: #seo-analyzer-dev
- **Daily**: [horário e link]

---

## ✅ Checklist de Onboarding

Use este checklist para acompanhar seu progresso:

### Setup (Dia 1)
- [ ] Repositório clonado
- [ ] Docker instalado e funcionando
- [ ] .env configurado com API keys
- [ ] Ambiente rodando localmente (frontend + backend)
- [ ] Primeiro teste executado com sucesso

### Conhecimento (Semana 1)
- [ ] Li README.md
- [ ] Li DEVELOPER_GUIDE.md (seções principais)
- [ ] Li ARCHITECTURE.md
- [ ] Explorei a UI completa
- [ ] Entendi o fluxo de Run
- [ ] Entendi os modelos de dados
- [ ] Explorei os endpoints da API

### Prática (Semana 1)
- [ ] Executei runs de teste
- [ ] Criei um projeto e subprojeto
- [ ] Configurei um monitor
- [ ] Adicionei um campo simples (exercício)
- [ ] Fiz mudança no frontend (exercício)
- [ ] Criei minha primeira PR

### Autonomia (Semana 2)
- [ ] Implementei uma feature completa
- [ ] Fiz code review de outro PR
- [ ] Ajudei outro dev com dúvida
- [ ] Contribuí para a documentação

---

## 🎯 Objetivos de 30 Dias

Ao final de 30 dias, você deve ser capaz de:

1. **Desenvolver features end-to-end** (backend + frontend)
2. **Debugar problemas** sozinho na maioria dos casos
3. **Fazer code reviews** construtivos
4. **Entender a arquitetura** e tomar decisões técnicas
5. **Contribuir para a documentação** e processos

---

## 🎉 Bem-vindo ao Time!

Estamos felizes em ter você aqui. Não hesite em fazer perguntas e pedir ajuda. Todos passamos por esse processo de onboarding e estamos aqui para apoiar.

**Dica final:** A melhor forma de aprender é fazendo. Não tenha medo de quebrar coisas no ambiente local - é para isso que ele existe! 🚀

---

**Versão**: 1.0  
**Última atualização**: Janeiro 2025  
**Feedback**: Se algo neste guia não está claro, por favor abra uma issue ou PR para melhorá-lo!
