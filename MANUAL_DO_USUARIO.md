# Manual do Usuário - Zero-Click SEO & AI Citation Monitor

## Visão Geral

O **Zero-Click SEO & AI Citation Monitor** é uma plataforma avançada para monitoramento de citações em respostas de IA (AI Overviews, Bing Copilot, Perplexity, etc.) e análise de SERP com KPIs especializados. A ferramenta permite acompanhar como seu conteúdo é citado em respostas zero-click e otimizar sua estratégia de SEO para IA.

### Acesso à Plataforma
- **URL Principal**: http://iqui27.app
- **Interface**: Aplicação web moderna com modo escuro/claro
- **Navegação**: Atalhos de teclado disponíveis (`/` para busca, `r` para nova run, `g+d` para dashboard)

---

## 🚀 Primeiros Passos

### 1. Configuração Inicial

Ao acessar a plataforma pela primeira vez:

1. **Criar Projeto**: Use o botão "Criar rápido" no modal "Nova Run" para configurar automaticamente um projeto
2. **Configurar Domínios**: Acesse Settings → Domínios para adicionar seus domínios-alvo
3. **Configurar APIs**: As chaves de API são configuradas via variáveis de ambiente (OPENAI_API_KEY, PERPLEXITY_API_KEY, etc.)

### 2. Estrutura Organizacional

A plataforma organiza o trabalho em:
- **Projetos**: Container principal (ex: "Projeto Banco – BR pt-BR")
- **Subprojetos/Temas**: Grupos temáticos (ex: "Conta Universitária", "Seguros")
- **Templates**: Prompts reutilizáveis por categoria
- **Runs**: Execuções individuais de análise

---

## 📊 Funcionalidades Principais

### **Runs - Execução de Análises**

#### Criar Nova Run
1. Clique em "Nova Run" ou pressione `r`
2. Selecione:
   - **Projeto**: Container organizacional
   - **Subprojeto** (opcional): Tema específico
   - **Template**: Prompt pré-configurado ou customizado
   - **Engine**: Modelo de IA (OpenAI GPT-5, Gemini 2.5, Perplexity, Google SERP)
   - **Ciclos**: Número de execuções (1-10)
   - **Delay**: Intervalo entre ciclos (em segundos)

#### Engines Disponíveis
- **OpenAI GPT-5/4.1**: Com web search e configurações avançadas
- **Gemini 2.5 Pro/Flash**: Google Search integrado
- **Perplexity Sonar Pro**: Especializado em citações
- **Google SERP**: AI Overview via SerpAPI

#### Configurações Avançadas (OpenAI)
- **Web Search**: Ativar/desativar busca na web
- **Context Size**: low/medium/high
- **Reasoning Effort**: Nível de raciocínio
- **Max Output Tokens**: Limite de resposta
- **System Prompt**: Personalizar comportamento
- **Location**: País/cidade/região para localização

### **Monitoramento em Tempo Real**

#### Run Detail - Acompanhamento ao Vivo
- **Timeline**: Progresso em tempo real via SSE (Server-Sent Events)
- **Toolbelt**: Status das ferramentas (LLM, Search, SERP, Screenshot)
- **Streaming**: Resposta sendo gerada em tempo real
- **Ciclos**: Navegação entre múltiplos ciclos de execução

#### Indicadores de Status
- **Verde**: Operação concluída com sucesso
- **Azul**: Em execução
- **Vermelho**: Erro
- **Cinza**: Aguardando

### **Templates - Gerenciamento de Prompts**

#### Funcionalidades
- **Categorização**: Organizar por temas (ex: "Abertura PF", "Seguro Auto")
- **Reutilização**: Templates podem ser usados em múltiplas runs
- **Personalização**: Editar prompts existentes ou criar novos
- **Vinculação**: Associar templates a subprojetos específicos

#### Templates Pré-configurados
- Tarifas bancárias
- Abertura de contas
- Produtos financeiros
- Seguros
- Investimentos

### **Monitores - Automação**

#### Agendamento Automático
- **Presets CRON**: 
  - Diário 02:00 (`0 2 * * *`)
  - Dias úteis 06:00 (`0 6 * * 1-5`)
  - Semanal domingo 03:00 (`0 3 * * 0`)
- **Múltiplos Templates**: Executar vários prompts em lote
- **Múltiplas Engines**: Testar diferentes modelos simultaneamente
- **Toggle Ativo/Inativo**: Pausar/retomar monitoramento
- **Execução Manual**: Botão "Rodar agora"

### **Analytics e KPIs**

#### Métricas Principais
- **AMR (AI Mention Rate)**: Taxa de menção em respostas de IA
- **DCR (Domain Citation Rate)**: Taxa de citação do domínio
- **ZCRS (Zero-Click Response Score)**: Pontuação de resposta zero-click
- **SoV-AI (Share of Voice AI)**: Participação de voz em IA


### **Citações e Evidências**

#### Análise de Citações
- **Detecção Automática**: URLs extraídas das respostas
- **Normalização**: Remoção de UTMs e fragmentos
- **Classificação**: "Nosso" vs. concorrentes
- **Favicon**: Identificação visual dos domínios
- **Títulos**: Captura automática via `og:title`

#### Evidências
- **Raw Data**: Dados brutos das APIs
- **Parsed Content**: Conteúdo processado
- **Screenshots**: Capturas de tela (quando disponível)
- **Metadata**: Informações técnicas da execução

---

## 🔧 Configurações e Personalização

### **Settings - Configurações do Projeto**

#### Domínios-Alvo
- **Adicionar**: Inserir domínios para monitoramento
- **Remover**: Excluir domínios desnecessários
- **Validação**: Verificação automática de formato

#### Engines por Projeto
- **Configuração JSON**: Personalizar parâmetros por engine
- **Web Search**: Ativar/desativar busca para modelos suportados
- **Modelos**: Selecionar versões específicas (GPT-5, Gemini 2.5, etc.)

### **Workspace - Organização**

#### Projetos
- **Criar**: Novos projetos com país, idioma e timezone
- **Editar**: Modificar configurações existentes
- **Excluir**: Remover projetos (cuidado: ação irreversível)

#### Subprojetos/Temas
- **Agrupamento**: Organizar runs por temas
- **Analytics**: Dashboards específicos por tema
- **Templates**: Vincular prompts a temas específicos

---

## 📈 Análise e Relatórios

### **Visualização de Dados**

#### Run Detail
- **Resposta Markdown**: Formatação rica com GFM (GitHub Flavored Markdown)
- **Citações**: Cards com favicon e classificação
- **Métricas**: Tokens, custo, latência, ciclos
- **Progresso**: Timeline detalhada de execução

#### Ações de Cópia
- **Markdown**: Copiar resposta em formato MD
- **HTML**: Copiar como HTML estruturado
- **Citações**: Links diretos para fontes

### **Exportação de Dados**

#### CSV Export
- **Endpoint**: `GET /api/analytics/subprojects/{id}/export.csv`
- **Conteúdo**: KPIs, citações, métricas por run
- **Filtros**: Por período, engine, status

---

## 🔍 Busca e Filtros

### **Filtros Disponíveis**
- **Subprojeto**: Filtrar por tema específico
- **Engine**: Filtrar por modelo de IA
- **Status**: completed, running, failed
- **Período**: Por data de execução

### **Busca Global**
- **Atalho**: Pressione `/` para focar na busca
- **Escopo**: IDs de run, templates, engines
- **Auto-refresh**: Atualização automática a cada 5 segundos

---

## 🚨 Troubleshooting

### **Problemas Comuns**

#### Live Stream Não Atualiza
- **Causa**: Conexão SSE falhando
- **Solução**: Sistema faz fallback automático para polling
- **Verificação**: Badge "Conectado (SSE)" vs "Conectado (Polling)"


## 🔐 Segurança e APIs

### **Chaves de API Necessárias**
- `PERPLEXITY_API_KEY`: Para Perplexity Sonar
- `GOOGLE_API_KEY`: Para Gemini (Google AI)
- `OPENAI_API_KEY`: Para GPT-5/4.1
- `SERPAPI_KEY`: Para Google SERP/AI Overview

### **Configuração Segura**
- Chaves armazenadas em variáveis de ambiente
- Não expostas no frontend
- Rotação periódica recomendada

---

## 📱 Interface e Usabilidade

### **Atalhos de Teclado**
- `/`: Focar na busca
- `r`: Nova run
- `g + d`: Ir para dashboard
- `Esc`: Fechar modais

### **Modo Escuro/Claro**
- **Toggle**: Botão no header
- **Persistência**: Preferência salva localmente
- **Auto-detecção**: Respeita configuração do sistema

### **Responsividade**
- **Mobile**: Interface adaptada para dispositivos móveis
- **Tablet**: Layout otimizado para telas médias
- **Desktop**: Experiência completa

---

## 🔄 Fluxo de Trabalho Recomendado

### **Setup Inicial**
1. Criar projeto com "Criar rápido"
2. Configurar domínios-alvo em Settings
3. Criar subprojetos por tema
4. Configurar templates por categoria

### **Execução Diária**
1. Verificar runs automáticas (monitores)
2. Analisar citações e KPIs
3. Criar runs manuais para testes específicos
4. Exportar dados para relatórios

### **Otimização Contínua**
1. Ajustar prompts baseado em resultados
2. Testar diferentes engines
3. Configurar novos monitores
4. Analisar tendências nos dashboards

---

## 📞 Suporte e Recursos

### **Documentação Técnica**
- `docs/README-UX.md`: Fluxo de experiência do usuário
- `DEVELOPMENT.md`: Guia para desenvolvedores
- `README-DEPLOYMENT.md`: Instruções de deploy

### **Endpoints da API**
- **Swagger**: `http://localhost:8000/docs` (desenvolvimento)
- **Produção**: `http://iqui27.app/api/docs`

### **Monitoramento**
- **Health Check**: Verificação automática de saúde dos serviços
- **Logs**: Sistema de logging estruturado
- **Métricas**: Acompanhamento de performance

---


## 📊 Métricas e Interpretação

### **AMR (AI Mention Rate)**
- **Definição**: Percentual de menções em respostas de IA
- **Cálculo**: (Menções / Total de Queries) × 100
- **Meta**: >20% para tópicos relevantes

### **DCR (Domain Citation Rate)**
- **Definição**: Taxa de citação do domínio
- **Cálculo**: (Citações do Domínio / Total de Citações) × 100
- **Meta**: >15% em nicho específico

### **ZCRS (Zero-Click Response Score)**
- **Definição**: Pontuação de qualidade da resposta zero-click
- **Fatores**: Relevância, autoridade, frescor
- **Escala**: 0-100 (>70 considerado excelente)

---

*Este manual é atualizado regularmente. Para dúvidas específicas ou suporte técnico, consulte a documentação técnica ou entre em contato com a equipe de desenvolvimento.*
