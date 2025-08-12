# Zero‑Click SEO & AI Citation Monitor (MVP)

Monitor de citações zero‑click (AI Overviews/SGE, Bing/Copilot, Perplexity, LLMs com grounding) e SERP com KPIs (AMR/DCR/SoV‑AI/ZCRS), evidências e dashboard.

- Guia de UX/Fluxo “mágico”: veja `docs/README-UX.md`.

## Stack
- Backend: FastAPI + SQLAlchemy (PostgreSQL), Celery + Redis, SSE
- Adapters: Gemini (google_search/sem tools com fallback), OpenAI, Perplexity, Google SERP (Playwright) + SerpAPI
- Frontend: React + Vite + Tailwind (dark mode), Recharts, ReactMarkdown
- Infra local: Docker Compose

## Requisitos
- Docker + Docker Compose
- Chaves (opcionais, mas recomendadas):
  - `PERPLEXITY_API_KEY`, `GOOGLE_API_KEY` (Gemini), `OPENAI_API_KEY`, `SERPAPI_KEY`

## Setup rápido
1) Crie `.env` na raiz com as chaves disponíveis:
```
PERPLEXITY_API_KEY=...
GOOGLE_API_KEY=...
OPENAI_API_KEY=...
SERPAPI_KEY=...
```
2) Suba os serviços:
```
docker compose up -d --build
```
3) Acesse:
- API: `http://localhost:8000/docs` (Swagger)
- Front: `http://localhost:5173`

## Fluxo de uso (UI)
1) Projeto
- O modal “Nova Run” permite “Criar rápido” um projeto com um clique. O `Project ID` fica salvo localmente.

2) Subprojetos (grupos)
- Menu “Subprojetos”: crie grupos (ex.: “Conta Universitária”) para agregar runs e dashboards específicos.

3) Templates
- Menu “Templates”: crie/edite prompts por categoria (ex.: “Abertura PF”, “Seguro Auto”).

4) Runs
- Página “Runs”: filtros por subprojeto/engine/status, busca por ID e auto‑refresh.
- Clique em “Nova Run”, selecione projeto, (opcional) subprojeto, categoria/Template e a engine desejada. 

5) Run Detail (ao vivo)
- Timeline em tempo real (SSE com fallback polling) e “toolbelt” (LLM/Search/SERP/Screenshot).
- Citações em cards (favicon e badge “nosso”).
- Resposta com markdown rico (GFM) em streaming e ações de copiar (Markdown/HTML).

6) Monitores (agendamento)
- Menu “Monitors”: agrupe múltiplos Templates e engines para rodar em lote.
- Presets de CRON prontos: “Diário 02:00” (0 2 * * *), “Dias úteis 06:00” (0 6 * * 1-5), “Semanal dom 03:00” (0 3 * * 0).
- Toggle “ativo” para pausar/retomar, e ação “Rodar agora”.
- Edite nome, `schedule_cron`, engines e vincule Templates. Histórico por monitor disponível na lista.

7) Dashboard por Subprojeto
- KPIs agregados (AMR/DCR/ZCRS), série temporal de ZCRS e top domínios citados.
- Exportar CSV: botão na UI e endpoint dedicado `GET /api/analytics/subprojects/{id}/export.csv`.

8) Settings
- Domínios‑alvo por projeto: listar/adicionar/remover.
- Engines por projeto: ver/editar `config_json` (p. ex. ativar web search em modelos suportados).
- Chaves de API via `.env` (Compose carrega automaticamente).

## Principais endpoints
- Projetos: `POST /api/projects`, `GET /api/projects`
- Domínios: `GET /api/projects/{project_id}/domains`, `DELETE /api/domains/{domain_id}`
- Engines: `GET/PATCH /api/projects/{project_id}/engines`
- Subprojetos: `POST/GET /api/projects/{project_id}/subprojects`
- Templates: `POST/GET /api/projects/{project_id}/templates`, `PATCH/DELETE /api/templates/{template_id}`
- Prompts: `POST /api/projects/{project_id}/prompts`, `GET/POST /api/prompts/{prompt_id}/versions`
- Monitores: `POST/GET /api/projects/{project_id}/monitors`, `POST /api/monitors/{monitor_id}/templates/{template_id}`, `POST /api/monitors/{monitor_id}/run`, `PATCH /api/monitors/{monitor_id}`
- Runs: `POST /api/runs`, `GET /api/runs` (filtros: `subproject_id`, `engine`, `status`, `limit`), `GET /api/runs/{id}`
- Relatórios: `GET /api/runs/{id}/report`, `GET /api/runs/{id}/evidences`
- Eventos: `GET /api/runs/{id}/events`, SSE `GET /api/runs/{id}/stream`
- Analytics: `GET /api/analytics/overview`, `GET /api/analytics/subprojects/{id}/overview`, `/series`, `/top-domains`, `GET /api/analytics/subprojects/{id}/export.csv`
- Utils: `GET /api/utils/url-title`

## Adapters (estado)
- Gemini: usa `google_search` (moderno) quando disponível; fallback para `google_search_retrieval` e, por fim, sem tools (`use_search=false`).
- OpenAI: extração de URLs por regex.
- Perplexity: coleta `citations`/`search_results`.
- Google SERP: Playwright headless; fallback via SerpAPI.

## KPIs
- AMR/DCR/ZCRS calculados por run; dedup de citações com normalização de URL (remove UTMs/fragment, host/path normalizados).

## Troubleshooting
- Live stream não atualiza: a UI cai automaticamente em polling se o SSE (`/api/runs/{id}/stream`) retornar 404. Verifique se o back está em `:8000` e a UI em `:5173`.
- “vite: not found” ou `ENOTEMPTY` no front: o Compose limpa `node_modules` e reinstala (`npm install --force`) no boot. Reinicie:
```
docker compose restart frontend
```
- Playwright/Chromium: primeira instalação pode demorar; logs no serviço `backend`.

## Roadmap (próximos)
- Toolbelt com estados por ferramenta (eventos dedicados)
- Markdown com ações (copiar em Markdown/HTML) e títulos das citações (captura `og:title`)
- Dashboards completos (series, SoV‑AI, Freshness Gap, leaderboard por engine)
- Alertas e‑mail/Slack e webhooks
- Deploy GCP (Cloud Run/Tasks/SQL/Storage/Scheduler/Logging) + OpenTelemetry/custos

## Scripts úteis
- Subir/derrubar: `docker compose up -d --build` / `docker compose down`
- Logs: `docker compose logs -f backend|worker|frontend`

## Deploy (DigitalOcean)

Passo a passo para subir em um Droplet usando Docker Compose em produção.

1) Copiar artefatos para o servidor (via scp) para `/opt/seo-analyzer`:
- Exemplos (ajuste usuário/host e a lista de arquivos):
```
# a partir da sua máquina local
scp -r docker-compose.prod.yml .env USER@HOST:/opt/seo-analyzer/
# (opcional) outros artefatos necessários
# scp -r backend frontend docker USER@HOST:/opt/seo-analyzer/
```

2) Conectar por SSH e criar volumes/diretórios (persistência e logs):
```
ssh USER@HOST <<'EOF'
  sudo mkdir -p /opt/seo-analyzer/{data/postgres,data/redis,data/storage,logs}
  sudo chown -R $USER:$USER /opt/seo-analyzer
EOF
```

3) Subir os serviços em modo produção (build + detach):
```
ssh USER@HOST "cd /opt/seo-analyzer && docker compose -f docker-compose.prod.yml up -d --build"
```

4) Smoke tests (validação rápida):
- Verificar containers:
```
ssh USER@HOST "cd /opt/seo-analyzer && docker compose -f docker-compose.prod.yml ps"
```
- Backend respondendo (Swagger):
```
# de fora do servidor (na sua máquina), troque HOST pelo IP/DNS
curl -I http://HOST:8000/docs
```
- Endpoint de analytics responde JSON:
```
curl -sSf http://HOST:8000/api/analytics/overview | head -c 500
```
- Teste utilitário simples (título de página):
```
curl -s "http://HOST:8000/api/utils/url-title?url=https://example.com"
```
- Logs rápidos (se necessário):
```
ssh USER@HOST "cd /opt/seo-analyzer && docker compose -f docker-compose.prod.yml logs --tail=100 --no-color backend"
```

Rollback
- Se algo der errado, derrube os serviços e volte para a tag anterior do repositório no servidor:
```
ssh USER@HOST <<'EOF'
  set -e
  cd /opt/seo-analyzer
  docker compose -f docker-compose.prod.yml down
  # opcional: verifique as tags disponíveis
  # git tag --list | tail -n 20
  git checkout <tag-anterior>
  docker compose -f docker-compose.prod.yml up -d --build
EOF
```
- Observação: se você não mantém o repositório Git no servidor (apenas artefatos copiados), restaure os arquivos anteriores (ex.: `docker-compose.prod.yml` e `.env`) e execute novamente o `docker compose -f docker-compose.prod.yml up -d --build`.

---
Contribuições: PRs e issues bem‑vindas. Ajuste as chaves em `.env` para maximizar as citações e a qualidade do grounding.
