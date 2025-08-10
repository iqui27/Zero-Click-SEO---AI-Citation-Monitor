# Zero‑Click SEO & AI Citation Monitor — Fluxo “mágico” (para README/Cursor)

Este documento descreve o **fluxo ideal de uso** e as **decisões de UX** para que qualquer pessoa rode o monitor em minutos — sem fricção, com telas claras e resultados imediatos.

---

## Visão rápida

- **Objetivo:** descobrir se o nosso domínio é **citado** nas respostas de IA (AI Overviews/SGE, Copilot, Perplexity, LLMs) e na SERP — e **por que** não é quando falha.
- **Sensação:** plug‑and‑play. Se houver chaves, usamos; se não, rodamos em **Sandbox** com dados reais de SERP e respostas gravadas para demonstrar valor.
- **Entregáveis imediatos:** KPIs (AMR/DCR/SoV‑AI/ZCRS), lista de consultas, domínios citados, motivos de não‑citação, prints/evidências e recomendações.

---

## Setup “zero esforço”

1. **Um comando**:

   ```bash
   docker compose up -d --build
   ```
2. Se **não existir `.env`**, abre o **First‑Run Wizard** no navegador (localhost):

   - Pergunta o **site principal** (ex.: `https://www.seudominio.com.br`).
   - Oferece colar chaves (OpenAI, Gemini, Perplexity, SerpAPI). **Todas são opcionais**.
   - Botão **“Testar conexões”** mostra ✔️/⚠️ por provedor.
   - Se não houver chaves: ativa **Sandbox Mode** (usa amostras/fixtures para demonstração + SERP via fallback permitido).
3. **Criar projeto com 1 clique**: o wizard sugere um nome (ex.: *Cartões – BR pt‑BR*) e cria **Subprojeto** inicial.
4. **Gerar consultas automaticamente** (pode editar):

   - **Modo rápido**: 15 money queries baseadas no domínio (rotina: sitemap/títulos comuns + intents).
   - **Importar CSV/Sheets** (opcional).
5. **Rodar “Smoke Test”**: 5 consultas × 1 engine → timeline ao vivo + evidências. Ao final, salva agendamento diário (08:00 local) — ajustável.

> **Resultado:** em menos de 3 minutos o usuário vê **citações/ausências** e motivos, já com um **dashboard** inicial.

---

## Navegação principal

- **Runs** (ao vivo) · **Dashboard** · **Consultas & Templates** · **Evidências** · **Configurações**

### Padrões de UI (design system)

- **Dark mode** padrão, tipografia legível, cards com cantos 2xl, sombras suaves.
- **Empty states úteis** com CTA direto (ex.: “Nenhuma consulta — Importar CSV”).
- **Skeleton loaders** e **toasts** curtos.
- **Atalhos de teclado**: `/` foca busca, `r` = Nova Run, `g d` = Dashboard.
- **Acessibilidade**: foco visível, contraste AA, labels e descrição para ícones.

---

## Fluxo do usuário (end‑to‑end)

### 1) First‑Run Wizard

- **Passo 1 — Domínio**: detecta variantes automaticamente (com/sem www, `m.`). Permite adicionar subdomínios.
- **Passo 2 — Conexões**: toggles por engine. Botão **“Testar”** exibe latência e quota. Sem chaves → ativa **Sandbox**.
- **Passo 3 — Consultas**: sugere lista por intenção (Informacional, Comparativa, Transacional, Navegacional). Upload CSV.
- **Passo 4 — Smoke Test**: executa, mostra timeline (SSE) e cards de citações ao vivo. Conclui com **agendamento diário**.

### 2) Runs (tempo real)

- Filtros por subprojeto/engine/status. **Auto‑refresh** + SSE.
- **Toolbelt** lateral: LLM/Search/SERP/Screenshot (estado por etapa com badges).
- **Cards de Citação**: favicon, domínio, tipo (link/menção), **badge “NOSSO”** quando pertence ao domínio alvo.
- **Painel de Resposta**: markdown rico + **fontes reconhecidas** (ícones),
- **Drawer de Evidência**: captura de tela, raw JSON e **links normalizados** (copiar/abrir).

### 3) Dashboard

- **KPIs** (AMR/DCR/ZCRS, variação vs. semana passada).
- **Série temporal** do ZCRS e **leaderboard** de domínios citados.
- **Por intenção**: barras empilhadas (citado × não citado).
- **Insights** com prioridade (Impacto × Esforço) e status atribuível.
- **Views salvas** (ex.: “Conta PJ – BR/desktop/pt‑BR”).

### 4) Consultas & Templates

- Biblioteca com **versionamento** e tags. Placeholders `{{produto}}`, `{{cidade}}`.
- Ações rápidas: **Clonar**, **Desativar**, **Rodar agora**.
- Importar/exportar CSV. Validação de duplicatas.

### 5) Evidências

- Lista pesquisável por consulta/domínio/engine.
- Cada item abre **duas colunas**: `AI Block/SERP` ↔ `Links/JSON`.
- **Botão Copiar** (Markdown/HTML) e **Baixar print**.

### 6) Recomendações (Por que não citou?)

- Chips com os 3 principais **motivos** (ex.: conteúdo desatualizado, falta FAQ, autoridade menor).
- **Playbooks** por motivo com checklists (`schema.org`, HowTo/FAQ, comparativos, lastmod, E‑E‑A‑T).
- Botões **“Abrir tarefa”** (Webhook → Linear/Jira) e **“Adicionar ao backlog”** interno.

### 7) Alertas e Relatórios

- **Alertas** quando AMR/DCR caem, ZCRS sobe, ou concorrente dispara.
- **Resumo semanal** por e‑mail (KPIs + 5 maiores problemas + 5 vitórias), linkando para evidências.

---

## Comportamentos “mágicos”

- **Detecção automática de domínio** a partir da URL inserida (normalização + regex de variações).
- **Auto‑tagging de intenção** por consulta (heurística simples + override manual).
- **Dedup** de citações com normalização (remoção de UTM/fragment, canonical simples).
- **Fallbacks inteligentes**: se um provedor falha, marca ⚠️ mas **continua** com os demais.
- **Sandbox Mode**: sem chaves, o app roda com fixtures reais e deixa tudo pronto; ao adicionar chaves, ele **reprocessa** o último run automaticamente.

---

## Conteúdo do repositório (sugestão)

```
/scripts
  first-run.sh        # cria .env interativo ou ativa Sandbox
  seed.sh             # carrega consultas de exemplo e subprojeto
  smoke-test.sh       # executa 5×1 para validação
/backend
  ... FastAPI + Celery + Redis + Postgres
/frontend
  ... React + Vite + Tailwind + Recharts
/fixtures             # respostas/screenhots para Sandbox
/docs
  README-UX.md        # este arquivo
```

---

## Textos de interface (microcopy)

- **Empty consultas**: “Sem consultas ainda — importe um CSV ou gere automaticamente em 1 clique.”
- **Testar conexões**: “Tudo certo! Podemos rodar em produção.” / “Sem chaves? Tudo bem — vou te mostrar como fica em Sandbox.”
- **Conclusão do wizard**: “Pronto! Agendei uma verificação diária. Você pode rodar outra agora mesmo.”

---

## Perguntas frequentes (FAQ)

- **Preciso de chaves?** Não. Em **Sandbox** você já vê o fluxo completo. Com chaves, os dados ficam 100% reais.
- **Isso impacta SEO?** Não executamos nada no seu site; só lemos resultados públicos.
- **Posso usar só Google?** Sim. Você escolhe engines no Wizard ou nas Configurações.

---

## Roadmap curto (UX)

- **Wizard** com import do **Sitemap** (para gerar consultas por conteúdo).
- **Título das citações** (captura `og:title`) e cópia como Markdown.
- **Views compartilháveis** (link público somente‑leitura).
- **Tema** com paletas predefinidas + logotipo do projeto.

---

> **Resumo**: o usuário entra, cola a URL do site, opcionalmente cola chaves, aceita uma lista de consultas sugeridas e **vê resultados em minutos** — com KPIs claros, evidências visuais e recomendações acionáveis. O resto é iteração contínua, sem fricção.
