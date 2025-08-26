# 🌐 Configuração de Subdomínios

Este documento explica como configurar subdomínios para acessar n8n, Evolution API e SEO Analyzer através de URLs amigáveis.

## 📋 Serviços Configurados

| Subdomínio | Serviço | Porta Original | Nova URL |
|------------|---------|----------------|----------|
| `n8n.seudominio.com` | n8n Automation | 5678 | http://n8n.seudominio.com |
| `evolution.seudominio.com` | Evolution API | 8080 | http://evolution.seudominio.com |
| `seudominio.com` | SEO Analyzer | 80 | http://seudominio.com |

## 🔧 Configuração Técnica

### Nginx Proxy Reverso
A configuração foi adicionada ao arquivo `deploy/nginx.conf` com três blocos `server`:

1. **n8n subdomain**: Redireciona `n8n.*` para `localhost:5678`
2. **Evolution subdomain**: Redireciona `evolution.*` para `localhost:8080`
3. **Main site**: Mantém o SEO Analyzer como site principal

### Aplicar Configuração no Servidor

1. **Deploy via GitHub Actions** (Recomendado):
   ```bash
   git add .
   git commit -m "feat: add subdomain configuration for n8n and evolution"
   git push origin main
   ```

2. **Deploy manual**:
   ```bash
   # Copiar script para o servidor
   scp -i "C:\Users\hftra\.ssh\oci_ed25519" scripts/setup-subdomains.sh ubuntu@129.148.63.199:/tmp/
   
   # Executar no servidor
   ssh -i "C:\Users\hftra\.ssh\oci_ed25519" ubuntu@129.148.63.199
   chmod +x /tmp/setup-subdomains.sh
   /tmp/setup-subdomains.sh
   ```

## 🌍 Configuração DNS

### Opção 1: Provedor de DNS (Recomendado)
Configure os seguintes registros A no seu provedor de DNS:

```
Tipo: A
Nome: @
Valor: 129.148.63.199
TTL: 300

Tipo: A  
Nome: n8n
Valor: 129.148.63.199
TTL: 300

Tipo: A
Nome: evolution  
Valor: 129.148.63.199
TTL: 300
```

### Opção 2: Teste Local (/etc/hosts)
Para testar localmente, adicione ao arquivo hosts:

**Windows**: `C:\Windows\System32\drivers\etc\hosts`
**Linux/Mac**: `/etc/hosts`

```
129.148.63.199 seudominio.com
129.148.63.199 n8n.seudominio.com
129.148.63.199 evolution.seudominio.com
```

## 🔍 Verificação e Testes

### Comandos de Teste
```bash
# Testar conectividade
curl -I http://129.148.63.199:5678/     # n8n direto
curl -I http://129.148.63.199:8080/     # Evolution direto
curl -I http://129.148.63.199/health    # SEO Analyzer

# Testar subdomínios (após configurar DNS)
curl -I http://n8n.seudominio.com
curl -I http://evolution.seudominio.com
curl -I http://seudominio.com/health
```

### Status dos Serviços
Verificar se os serviços estão rodando no servidor:

```bash
ssh -i "C:\Users\hftra\.ssh\oci_ed25519" ubuntu@129.148.63.199
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## 🔐 Credenciais de Acesso

### n8n
- **URL**: http://n8n.seudominio.com
- **Usuário**: admin
- **Senha**: N8n@2024!

### Evolution API
- **URL**: http://evolution.seudominio.com
- **Manager**: http://evolution.seudominio.com/manager
- **API Key**: Ev0lut10n_G10b4l_API_K3y_2024!@#$

### SEO Analyzer
- **URL**: http://seudominio.com
- **Health Check**: http://seudominio.com/health

## 🚨 Troubleshooting

### Nginx não reinicia
```bash
# Verificar configuração
sudo docker exec seo-analyzer-prod-reverse-proxy-1 nginx -t

# Ver logs
sudo docker logs seo-analyzer-prod-reverse-proxy-1 --tail 50

# Reiniciar manualmente
sudo docker compose -f docker-compose.prod.yml restart reverse-proxy
```

### Subdomínio não resolve
1. Verificar configuração DNS com `nslookup seudominio.com`
2. Aguardar propagação DNS (até 24h)
3. Testar com arquivo hosts local primeiro

### Serviço não responde
```bash
# Verificar se containers estão rodando
sudo docker ps | grep -E "(n8n|evolution|seo-analyzer)"

# Verificar logs específicos
sudo docker logs n8n --tail 20
sudo docker logs evolution-api --tail 20
```

## 📝 Próximos Passos

1. ✅ Configuração Nginx aplicada
2. 🔄 Deploy da configuração para o servidor
3. 🌐 Configurar registros DNS
4. 🧪 Testar acesso aos subdomínios
5. 🔒 Configurar HTTPS (opcional)

---

**📅 Criado em:** 26 de Agosto de 2025  
**🔄 Última atualização:** 26 de Agosto de 2025
