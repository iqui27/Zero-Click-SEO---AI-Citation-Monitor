# 📚 Índice de Documentação - Zero-Click SEO Monitor

Guia completo de toda a documentação do projeto. Use este índice para encontrar rapidamente o que você precisa.

---

## 🎯 Por Onde Começar?

### Sou Novo no Projeto
1. **[README.md](./README.md)** - Comece aqui! Visão geral e quick start
2. **[ONBOARDING.md](./ONBOARDING.md)** - Guia de onboarding (primeira semana)
3. **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - Comandos e padrões comuns

### Vou Desenvolver Features
1. **[DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)** - Guia completo do desenvolvedor
2. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Arquitetura e padrões
3. **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Como contribuir

### Vou Fazer Deploy
1. **[README-DEPLOYMENT.md](./README-DEPLOYMENT.md)** - Deploy em produção
2. **[DEVELOPMENT.md](./DEVELOPMENT.md)** - Setup de ambiente

### Quero Entender o Sistema
1. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Arquitetura do sistema
2. **[ZERO_CLICK_CLASSIFICATION.md](./ZERO_CLICK_CLASSIFICATION.md)** - Sistema de classificação
3. **[DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)** - Modelos e API
4. **[docs/SEMANTIC_INSIGHTS.md](./docs/SEMANTIC_INSIGHTS.md)** - Insights semânticos (Gemini, entidades, percepção)

---

## 📖 Documentação Principal

### [README.md](./README.md)
**O que é:** Documento principal do projeto  
**Quando usar:** Primeira vez no projeto, overview geral  
**Conteúdo:**
- Visão geral do projeto
- Stack tecnológica
- Setup rápido (15 min)
- Fluxo de uso da UI
- Principais endpoints
- Troubleshooting básico

**Público:** Todos (desenvolvedores, PMs, stakeholders)

---

### [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
**O que é:** Guia completo para desenvolvedores  
**Quando usar:** Desenvolvimento de features, referência técnica  
**Conteúdo:**
- Arquitetura detalhada (diagramas)
- Stack tecnológica completa
- Estrutura do projeto
- Modelos de dados (todos os campos)
- API Reference (todos os endpoints)
- Serviços e integrações
- Frontend (componentes, API client)
- Fluxo de desenvolvimento
- Testes
- Deploy e infraestrutura
- Troubleshooting avançado
- Boas práticas

**Público:** Desenvolvedores (backend + frontend)  
**Tamanho:** ~500 linhas (leitura: 30-45 min)

---

### [ARCHITECTURE.md](./ARCHITECTURE.md)
**O que é:** Documentação de arquitetura do sistema  
**Quando usar:** Entender decisões técnicas, adicionar features complexas  
**Conteúdo:**
- Arquitetura de alto nível
- Camadas da aplicação
- Fluxos de dados (diagramas)
- Padrões de design (Adapter, Observer, Strategy, etc.)
- Decisões arquiteturais (por quê Azure SQL, Celery, SSE, etc.)
- Segurança
- Performance e escalabilidade
- Monitoramento e observabilidade
- Disaster recovery

**Público:** Desenvolvedores sênior, arquitetos, tech leads  
**Tamanho:** ~400 linhas (leitura: 30 min)

---

### [ONBOARDING.md](./ONBOARDING.md)
**O que é:** Guia de onboarding para novos desenvolvedores  
**Quando usar:** Primeiro dia/semana no projeto  
**Conteúdo:**
- Quick start (15 min)
- Plano da primeira semana (dia a dia)
- Ferramentas e comandos úteis
- Como testar mudanças
- Debugging
- Recursos de aprendizado
- Como contribuir
- Checklist de onboarding
- Objetivos de 30 dias

**Público:** Novos desenvolvedores  
**Tamanho:** ~300 linhas (leitura: 20 min)

---

### [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
**O que é:** Cheat sheet de comandos e padrões  
**Quando usar:** Consulta rápida durante desenvolvimento  
**Conteúdo:**
- Docker commands
- Development workflow
- Code patterns (backend + frontend)
- Common queries (DB + API)
- UI components (shadcn/ui)
- Testing snippets
- Environment variables
- Debug helpers
- Common metrics/KPIs
- Emergency commands
- Pro tips

**Público:** Todos os desenvolvedores  
**Tamanho:** ~400 linhas (referência rápida)

---

### [CONTRIBUTING.md](./CONTRIBUTING.md)
**O que é:** Guia de contribuição  
**Quando usar:** Antes de criar PR, durante code review  
**Conteúdo:**
- Como contribuir (passo a passo)
- Padrões de código (Python + TypeScript)
- Conventional commits
- Testes
- Documentação
- Code review (para reviewers e authors)
- O que NÃO fazer
- Checklist final
- Recursos e ferramentas

**Público:** Todos os contribuidores  
**Tamanho:** ~300 linhas (leitura: 20 min)

---

### [ZERO_CLICK_CLASSIFICATION.md](./ZERO_CLICK_CLASSIFICATION.md)
**O que é:** Documentação do sistema de classificação  
**Quando usar:** Trabalhar com classificação, entender métricas  
**Conteúdo:**
- Funcionalidades principais
- Tipos de classificação (ResponseType, SufficiencyLevel, etc.)
- Métricas avançadas
- Análise com Gemini 2.5 Pro
- Arquitetura do sistema de classificação
- API endpoints de classificação
- Scripts de automação
- Casos de uso e exemplos
- Troubleshooting

**Público:** Desenvolvedores trabalhando com classificação/IA  
**Tamanho:** ~400 linhas (leitura: 25 min)

---

### [DEVELOPMENT.md](./DEVELOPMENT.md)
**O que é:** Setup do ambiente de desenvolvimento  
**Quando usar:** Configurar ambiente local  
**Conteúdo:**
- Pré-requisitos
- Estrutura do projeto
- Setup de desenvolvimento
- Frontend development
- Backend development
- Worker process (Celery)
- Development workflow
- Database management
- Testing
- Debugging
- Troubleshooting
- Environment variables

**Público:** Desenvolvedores (setup inicial)  
**Tamanho:** ~370 linhas (leitura: 25 min)

---

### [README-DEPLOYMENT.md](./README-DEPLOYMENT.md)
**O que é:** Guia de deploy em produção  
**Quando usar:** Deploy, configuração de infraestrutura  
**Conteúdo:**
- Deploy em DigitalOcean/OCI
- Configuração de servidor
- Docker Compose produção
- Nginx/Caddy setup
- SSL/TLS
- Backup e restore
- Monitoramento
- Rollback

**Público:** DevOps, desenvolvedores fazendo deploy  
**Tamanho:** Varia (leitura: 15 min)

---

## 📁 Documentação Adicional (docs/)

### [docs/README-UX.md](./docs/README-UX.md)
**O que é:** Guia de UX e fluxo "mágico"  
**Conteúdo:** Jornadas do usuário, fluxos de tela

### [docs/CLOUDFLARE_DNS_SETUP.md](./docs/CLOUDFLARE_DNS_SETUP.md)
**O que é:** Setup de DNS com Cloudflare  
**Conteúdo:** Configuração de domínio e SSL

### [docs/SUBDOMAIN_SETUP.md](./docs/SUBDOMAIN_SETUP.md)
**O que é:** Configuração de subdomínios  
**Conteúdo:** Setup de subdomínios para múltiplos ambientes

### [docs/SECRET_HANDLING.md](./docs/SECRET_HANDLING.md)
**O que é:** Gestão de secrets e API keys  
**Conteúdo:** Boas práticas de segurança

### [docs/UI_FRAMEWORK_GUIDE.md](./docs/UI_FRAMEWORK_GUIDE.md)
**O que é:** Guia do framework UI (shadcn/ui)  
**Conteúdo:** Componentes, temas, customização

### [docs/smoke-tests.md](./docs/smoke-tests.md)
**O que é:** Testes de smoke após deploy  
**Conteúdo:** Checklist de validação pós-deploy

---

## 🗺️ Mapa de Navegação

### Por Tarefa

#### "Quero rodar o projeto localmente"
1. [README.md](./README.md) - Setup rápido
2. [DEVELOPMENT.md](./DEVELOPMENT.md) - Setup detalhado
3. [ONBOARDING.md](./ONBOARDING.md) - Primeiro teste

#### "Quero adicionar uma nova feature"
1. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seção "Fluxo de Desenvolvimento"
2. [ARCHITECTURE.md](./ARCHITECTURE.md) - Entender arquitetura
3. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Code patterns
4. [CONTRIBUTING.md](./CONTRIBUTING.md) - Antes de criar PR

#### "Quero corrigir um bug"
1. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seção "Troubleshooting"
2. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Debug helpers
3. [CONTRIBUTING.md](./CONTRIBUTING.md) - Como contribuir

#### "Quero entender como funciona X"
1. [ARCHITECTURE.md](./ARCHITECTURE.md) - Fluxos e padrões
2. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Detalhes técnicos
3. Código fonte

#### "Quero fazer deploy"
1. [README-DEPLOYMENT.md](./README-DEPLOYMENT.md) - Deploy guide
2. [docs/CLOUDFLARE_DNS_SETUP.md](./docs/CLOUDFLARE_DNS_SETUP.md) - DNS
3. [docs/smoke-tests.md](./docs/smoke-tests.md) - Validação

#### "Estou com um problema"
1. [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Troubleshooting
2. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Emergency commands
3. Issues do repositório
4. Time no Slack/Teams

---

## 📊 Matriz de Documentação

| Documento | Público | Quando Usar | Tempo Leitura | Atualização |
|-----------|---------|-------------|---------------|-------------|
| README.md | Todos | Primeira vez | 10 min | Frequente |
| DEVELOPER_GUIDE.md | Devs | Desenvolvimento | 45 min | Frequente |
| ARCHITECTURE.md | Devs Sr. | Features complexas | 30 min | Ocasional |
| ONBOARDING.md | Novos devs | Primeiro dia | 20 min | Ocasional |
| QUICK_REFERENCE.md | Todos devs | Consulta diária | Referência | Frequente |
| CONTRIBUTING.md | Contribuidores | Antes de PR | 20 min | Ocasional |
| ZERO_CLICK_CLASSIFICATION.md | Devs IA | Classificação | 25 min | Ocasional |
| DEVELOPMENT.md | Devs | Setup inicial | 25 min | Ocasional |
| README-DEPLOYMENT.md | DevOps | Deploy | 15 min | Ocasional |

---

## 🔄 Fluxo de Leitura Recomendado

### Dia 1 (Novo Desenvolvedor)
1. ✅ [README.md](./README.md) - 10 min
2. ✅ [ONBOARDING.md](./ONBOARDING.md) - Seção "Quick Start" - 15 min
3. ✅ Setup local seguindo os passos
4. ✅ Primeiro teste executado

### Semana 1
1. ✅ [ONBOARDING.md](./ONBOARDING.md) - Completo - 20 min
2. ✅ [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seções 1-5 - 30 min
3. ✅ [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Skim - 10 min
4. ✅ [ARCHITECTURE.md](./ARCHITECTURE.md) - Seções principais - 20 min

### Semana 2
1. ✅ [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Completo - 45 min
2. ✅ [CONTRIBUTING.md](./CONTRIBUTING.md) - Completo - 20 min
3. ✅ [ARCHITECTURE.md](./ARCHITECTURE.md) - Completo - 30 min
4. ✅ Primeira feature implementada

### Mês 1
1. ✅ Toda documentação lida
2. ✅ Múltiplas features implementadas
3. ✅ Code reviews feitos
4. ✅ Autonomia no desenvolvimento

---

## 🔍 Como Encontrar Informação

### Por Palavra-chave

**API / Endpoints**
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seção "API Reference"
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Seção "API Queries"

**Modelos / Database**
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seção "Modelos de Dados"
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Seção "Database Queries"

**Frontend / UI**
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seção "Frontend"
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Seção "UI Components"
- [docs/UI_FRAMEWORK_GUIDE.md](./docs/UI_FRAMEWORK_GUIDE.md)

**Docker / Infraestrutura**
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Seção "Docker Commands"
- [DEVELOPMENT.md](./DEVELOPMENT.md)
- [README-DEPLOYMENT.md](./README-DEPLOYMENT.md)

**Classificação / IA**
- [ZERO_CLICK_CLASSIFICATION.md](./ZERO_CLICK_CLASSIFICATION.md)
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seção "Serviços e Integrações"

**Testes**
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Seção "Testes"
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Seção "Testing Snippets"

**Deploy / Produção**
- [README-DEPLOYMENT.md](./README-DEPLOYMENT.md)
- [docs/CLOUDFLARE_DNS_SETUP.md](./docs/CLOUDFLARE_DNS_SETUP.md)

**Troubleshooting**
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Seção "Troubleshooting"
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Seção "Emergency Commands"
- [README.md](./README.md) - Seção "Troubleshooting"

---

## 📝 Mantendo a Documentação Atualizada

### Quando Atualizar

**Sempre:**
- Mudanças em APIs públicas
- Novas features importantes
- Breaking changes
- Mudanças em setup/deploy

**Ocasionalmente:**
- Melhorias de processo
- Novos padrões adotados
- Lições aprendidas

### Como Atualizar

1. Identifique o documento relevante
2. Faça as mudanças necessárias
3. Atualize a data de "Última atualização"
4. Crie PR com `docs:` prefix
5. Peça review

### Checklist de Atualização

- [ ] Informação está correta e atualizada
- [ ] Links funcionam
- [ ] Exemplos de código funcionam
- [ ] Screenshots atualizados (se aplicável)
- [ ] Data de atualização modificada
- [ ] Índice atualizado (se necessário)

---

## 🆘 Documentação Faltando?

Se você não encontrou o que procurava:

1. **Busque no código:** Comentários e docstrings
2. **Pergunte ao time:** Slack/Teams
3. **Crie uma issue:** "Documentação: [o que falta]"
4. **Contribua:** Adicione a documentação você mesmo!

---

## 📞 Feedback

Encontrou algo confuso? Tem sugestão de melhoria?

- Abra uma issue com label `documentation`
- Crie um PR melhorando a documentação
- Fale com o time no Slack/Teams

---

**A documentação é um projeto vivo. Ajude a mantê-la atualizada! 📚**

---

**Versão**: 1.0  
**Última atualização**: Janeiro 2025  
**Maintainer**: Equipe de Desenvolvimento
