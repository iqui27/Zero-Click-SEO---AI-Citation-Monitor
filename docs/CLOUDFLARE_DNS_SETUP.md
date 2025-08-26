# ☁️ Configuração DNS no Cloudflare para iqui27.app

Este documento explica como configurar os registros DNS no Cloudflare para os subdomínios do projeto.

## 🎯 Subdomínios Configurados

| Subdomínio | Serviço | URL Final |
|------------|---------|-----------|
| `iqui27.app` | SEO Analyzer | http://iqui27.app |
| `www.iqui27.app` | SEO Analyzer | http://www.iqui27.app |
| `n8n.iqui27.app` | n8n Automation | http://n8n.iqui27.app |
| `evolution.iqui27.app` | Evolution API | http://evolution.iqui27.app |

## 🌐 Registros DNS no Cloudflare

### Passo a Passo

1. **Acesse o Cloudflare Dashboard**
   - Login em https://dash.cloudflare.com
   - Selecione o domínio `iqui27.app`

2. **Vá para DNS > Records**

3. **Adicione os seguintes registros A:**

```
Tipo: A
Nome: @
Conteúdo: 129.148.63.199
Proxy status: 🔶 DNS only (desabilitado)
TTL: Auto

Tipo: A
Nome: www
Conteúdo: 129.148.63.199
Proxy status: 🔶 DNS only (desabilitado)
TTL: Auto

Tipo: A
Nome: n8n
Conteúdo: 129.148.63.199
Proxy status: 🔶 DNS only (desabilitado)
TTL: Auto

Tipo: A
Nome: evolution
Conteúdo: 129.148.63.199
Proxy status: 🔶 DNS only (desabilitado)
TTL: Auto
```

### ⚠️ Importante: Proxy Status

**DESABILITE o proxy do Cloudflare** (🔶 DNS only) para todos os registros inicialmente, pois:
- O servidor não está configurado para HTTPS ainda
- Evita problemas de conectividade inicial
- Permite testar a configuração diretamente

## 🚀 Deploy da Configuração

### Opção 1: GitHub Actions (Recomendado)
```bash
git add .
git commit -m "feat: configure nginx for iqui27.app domain"
git push origin main
```

### Opção 2: Deploy Manual
```bash
# Fazer upload da nova configuração
scp -i "C:\Users\hftra\.ssh\oci_ed25519" deploy/nginx.conf ubuntu@129.148.63.199:/opt/seo-analyzer/deploy/

# Aplicar no servidor
ssh -i "C:\Users\hftra\.ssh\oci_ed25519" ubuntu@129.148.63.199
cd /opt/seo-analyzer
sudo docker compose -f docker-compose.prod.yml restart reverse-proxy
```

## 🧪 Testes de Verificação

### 1. Verificar Resolução DNS
```bash
# Windows
nslookup iqui27.app
nslookup n8n.iqui27.app
nslookup evolution.iqui27.app

# Linux/Mac
dig iqui27.app
dig n8n.iqui27.app
dig evolution.iqui27.app
```

### 2. Testar Conectividade HTTP
```bash
curl -I http://iqui27.app/health
curl -I http://n8n.iqui27.app
curl -I http://evolution.iqui27.app
```

### 3. Verificar no Navegador
- http://iqui27.app - SEO Analyzer
- http://n8n.iqui27.app - n8n (admin / N8n@2024!)
- http://evolution.iqui27.app - Evolution API

## 🔒 Próximos Passos (Opcional)

### Habilitar HTTPS com Cloudflare
Após confirmar que tudo funciona com HTTP:

1. **Configurar SSL/TLS no Cloudflare:**
   - SSL/TLS > Overview > Full (strict)
   - Edge Certificates > Always Use HTTPS: On

2. **Habilitar Proxy (🧡 Proxied):**
   - Voltar em DNS > Records
   - Ativar proxy para todos os registros A

3. **Atualizar Nginx para HTTPS:**
   - Adicionar redirect HTTP → HTTPS
   - Configurar certificados SSL

## 🔍 Troubleshooting

### DNS não resolve
- Aguardar propagação (até 24h, geralmente 5-15 min)
- Verificar se registros estão corretos no Cloudflare
- Testar com diferentes DNS: `nslookup iqui27.app 8.8.8.8`

### Site não carrega
```bash
# Verificar se containers estão rodando
ssh -i "C:\Users\hftra\.ssh\oci_ed25519" ubuntu@129.148.63.199
sudo docker ps

# Verificar logs do Nginx
sudo docker logs seo-analyzer-prod-reverse-proxy-1 --tail 20

# Testar conectividade direta
curl -I http://129.148.63.199/health
```

### Cloudflare Error 522
- Verificar se o servidor está respondendo na porta 80
- Desabilitar proxy temporariamente
- Verificar firewall do Oracle Cloud

## 📋 Checklist de Configuração

- [ ] Registros DNS criados no Cloudflare
- [ ] Proxy desabilitado (DNS only)
- [ ] Configuração Nginx atualizada no servidor
- [ ] Container Nginx reiniciado
- [ ] Teste de resolução DNS
- [ ] Teste de conectividade HTTP
- [ ] Acesso aos subdomínios funcionando

---

**📅 Criado em:** 26 de Agosto de 2025  
**🔄 Última atualização:** 26 de Agosto de 2025
