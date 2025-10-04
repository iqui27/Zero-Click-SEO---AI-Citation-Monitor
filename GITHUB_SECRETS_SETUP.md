# 🔐 Configuração de Secrets no GitHub

**Última atualização:** 2025-10-04

## ⚠️ AÇÃO NECESSÁRIA

Para que o deploy automático funcione com a PAGESPEED_API_KEY, você precisa adicionar o secret no GitHub.

## 📝 Passo a Passo

### 1. Acesse as Configurações do Repositório

1. Vá para: https://github.com/iqui27/Zero-Click-SEO---AI-Citation-Monitor
2. Clique em **Settings** (Configurações)
3. No menu lateral, clique em **Secrets and variables** → **Actions**

### 2. Adicione o Novo Secret

1. Clique em **New repository secret**
2. Preencha:
   - **Name:** `PAGESPEED_API_KEY`
   - **Secret:** `AIzaSyCs5YI1zEiKeLWlTrJsj-gMmtyHmAhU574`
3. Clique em **Add secret**

## ✅ Secrets Necessários

Verifique se todos estes secrets estão configurados:

| Secret Name | Status | Descrição |
|-------------|--------|-----------|
| ORACLE_SSH_KEY | ✅ Deve existir | Chave SSH para acesso ao servidor |
| DATABASE_URL | ✅ Deve existir | Connection string do Azure SQL |
| SECRET_KEY | ✅ Deve existir | Chave secreta da aplicação |
| OPENAI_API_KEY | ✅ Deve existir | OpenAI para classificação |
| GOOGLE_API_KEY | ✅ Deve existir | Google Gemini |
| GEMINI_API_KEY | ✅ Deve existir | Gemini (alternativo) |
| PERPLEXITY_API_KEY | ✅ Deve existir | Perplexity para prompts |
| SERPAPI_KEY | ✅ Deve existir | SerpAPI para dados SERP |
| **PAGESPEED_API_KEY** | ❌ **ADICIONAR** | **PageSpeed Insights** |

## 🔄 O que Mudou no Deploy

### Antes
```yaml
# .env criado sem PAGESPEED_API_KEY
# Nginx não era reiniciado
# Podia dar erro 502 após deploy
```

### Agora
```yaml
# .env inclui PAGESPEED_API_KEY
PAGESPEED_API_KEY=${{ secrets.PAGESPEED_API_KEY }}

# Nginx é reiniciado automaticamente
- name: Restart nginx to refresh container IPs
  run: |
    ssh ... 'sudo docker compose restart reverse-proxy'
```

## 🎯 Benefícios

1. ✅ **PAGESPEED_API_KEY** configurada automaticamente em cada deploy
2. ✅ **Nginx reiniciado** para evitar erro 502
3. ✅ **Core Web Vitals** funcionando após deploy
4. ✅ **Sem intervenção manual** necessária

## 🧪 Testando o Deploy

Após adicionar o secret:

1. Faça um commit qualquer no branch POC
2. O GitHub Actions vai executar automaticamente
3. Verifique se o deploy completa sem erros
4. Teste se Core Web Vitals está funcionando

### Verificar se funcionou:

```bash
# No servidor
ssh -i "~/.ssh/oci_ed25519" ubuntu@129.148.63.199
cd /opt/seo-analyzer

# Verificar se a chave está no .env
cat .env | grep PAGESPEED_API_KEY

# Verificar se está carregada no container
sudo docker compose -f docker-compose.prod.yml exec -T api python -c "
import os
print('PAGESPEED_API_KEY:', '✅' if os.getenv('PAGESPEED_API_KEY') else '❌')
"
```

## 📋 Checklist Pós-Configuração

- [ ] Secret PAGESPEED_API_KEY adicionado no GitHub
- [ ] Deploy executado com sucesso
- [ ] API key presente no .env do servidor
- [ ] API key carregada nos containers
- [ ] Core Web Vitals funcionando em novas runs
- [ ] Nginx não dá erro 502 após deploy

## 🚨 Troubleshooting

### Secret não aparece no .env após deploy

**Causa:** Secret não foi adicionado no GitHub ou nome está errado

**Solução:**
1. Verifique se o nome é exatamente `PAGESPEED_API_KEY`
2. Verifique se o secret foi salvo
3. Rode o deploy novamente

### Erro 502 após deploy

**Causa:** Nginx não foi reiniciado (versão antiga do workflow)

**Solução:**
1. Pull da branch POC atualizada
2. Workflow agora inclui restart do nginx
3. Deploy novamente

### Core Web Vitals ainda NULL

**Causa:** Quota excedida ou API key inválida

**Solução:**
1. Verifique se a chave é válida
2. Aguarde reset da quota (meia-noite UTC)
3. Verifique logs: `docker compose logs worker | grep PAGESPEED`

## 📞 Suporte

Se tiver problemas:

1. Verifique os logs do GitHub Actions
2. Verifique os logs do servidor
3. Confirme que todos os secrets estão configurados

---

**✅ Após adicionar o secret, o deploy automático estará 100% funcional!**
