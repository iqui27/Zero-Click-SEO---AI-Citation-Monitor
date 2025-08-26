---
trigger: model_decision
description: Abouth OCI Oracle Cloud Instance
---

# 📋 Oracle Cloud Infrastructure (OCI) Agent Documentation

## 🎯 Objetivo
Este documento contém todas as informações necessárias para criar um agente especializado em gerenciar Oracle Cloud Infrastructure (OCI), incluindo credenciais, configurações e comandos essenciais.

---

## 🔐 Credenciais e Configuração

### **Informações da Conta OCI**
```
User OCID:    ocid1.user.oc1..aaaaaaaa3b7gtiinwmcgo5zeqaqa7grk4je4zwmgi2ykkxyz73wih4memgnq
Tenancy OCID: ocid1.tenancy.oc1..aaaaaaaab3khzlpcurua4ba3fh4q6uthyjz7iw52tltgfv5g3ltg2ciycw3a
Region:       sa-saopaulo-1
Fingerprint:  40:46:e0:0d:18:5e:ab:bd:ad:ec:b9:e9:56:54:cd:2a
```

### **Localização das Chaves**
```
Private Key:  /Users/hrocha/.oci/oci_api_key.pem
Public Key:   /Users/hrocha/.oci/oci_api_key_public.pem
Config File:  /Users/hrocha/.oci/config
```

### **Arquivo de Configuração OCI CLI**
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaa3b7gtiinwmcgo5zeqaqa7grk4je4zwmgi2ykkxyz73wih4memgnq
fingerprint=40:46:e0:0d:18:5e:ab:bd:ad:ec:b9:e9:56:54:cd:2a
tenancy=ocid1.tenancy.oc1..aaaaaaaab3khzlpcurua4ba3fh4q6uthyjz7iw52tltgfv5g3ltg2ciycw3a
region=sa-saopaulo-1
key_file=/Users/hrocha/.oci/oci_api_key.pem
```

---

## 🏗️ Infraestrutura Atual

### **Instâncias em Execução**
| Instance ID | Display Name | Public IP | Private IP | Status |
|-------------|--------------|-----------|------------|---------|
| `ocid1.instance.oc1.sa-saopaulo-1.antxeljrjnucp5yc6ep6ebum6lz354i6pcmhlbxhvhwla5lxk66cjqer3d6a` | instance-20250821-1418 | N/A | N/A | Unknown |
| `ocid1.instance.oc1.sa-saopaulo-1.antxeljrjnucp5yck7iks7gasutsg7adej3ci6sdndk3hvrbbnktwxj3vmva` | instance-20250825-0947 | N/A | N/A | Unknown |
| `ocid1.instance.oc1.sa-saopaulo-1.antxeljrjnucp5yctmlmdargt5byzjce2dfdouwnuncrwu7kcl2ie2zmp7ba` | instance-20250825-1241 | 129.148.63.199 | 10.0.0.197 | ✅ ACTIVE |

### **Instância Principal (Produção)**
```
Instance ID:  ocid1.instance.oc1.sa-saopaulo-1.antxeljrjnucp5yctmlmdargt5byzjce2dfdouwnuncrwu7kcl2ie2zmp7ba
Display Name: instance-20250825-1241
Public IP:    129.148.63.199
Private IP:   10.0.0.197
SSH Key:      /Users/hrocha/Documents/SSH Oracle/oci_ed25519
SSH User:     ubuntu
```

### **Configuração de Rede**
```
VCN ID:          ocid1.vcn.oc1.sa-saopaulo-1.amaaaaaajnucp5ya4gbfiyjypoxev2cmyyg3vbictmhnnh2yjf2nuqm66nma
Subnet ID:       ocid1.subnet.oc1.sa-saopaulo-1.aaaaaaaa2k77zor7eoh5ykensvmntvykyufi6rbig4tu4vayw6jcqoysot5q
Security List:   ocid1.securitylist.oc1.sa-saopaulo-1.aaaaaaaaz2qvoojbladmbw75s5kep6assbhoi5frk2r6yaid7dybn653ut7a
VNIC ID:         ocid1.vnic.oc1.sa-saopaulo-1.abtxeljrq6kng5kxpc4qzzve2hps47s3yklgwdsgry42pokrxpyar7y3rrgq
```

---

## 🛡️ Configuração de Segurança

### **Security List Rules (Portas Abertas)**
| Port | Protocol | Source | Description |
|------|----------|---------|-------------|
| 22   | TCP      | 0.0.0.0/0 | SSH Access |
| 80   | TCP      | 0.0.0.0/0 | HTTP |
| 443  | TCP      | 0.0.0.0/0 | HTTPS |
| 5678 | TCP      | 0.0.0.0/0 | n8n Automation Platform |
| 8080 | TCP      | 0.0.0.0/0 | Evolution API for WhatsApp |

### **ICMP Rules**
| Protocol | Type | Code | Source | Description |
|----------|------|------|---------|-------------|
| ICMP | 3 | 4 | 0.0.0.0/0 | Path MTU Discovery |
| ICMP | 3 | null | 10.0.0.0/16 | Internal ICMP |

---

## 🔧 Comandos OCI CLI Essenciais

### **Validação da Configuração**
```bash
# Testar conectividade OCI CLI
oci iam region list --output table

# Verificar configuração atual
cat ~/.oci/config

# Listar compartments
oci iam compartment list --all --output table
```

### **Gerenciamento de Instâncias**
```bash
# Listar todas as instâncias
TENANCY_ID="ocid1.tenancy.oc1..aaaaaaaab3khzlpcurua4ba3fh4q6uthyjz7iw52tltgfv5g3ltg2ciycw3a"
oci compute instance list --compartment-id $TENANCY_ID --output table

# Detalhes de uma instância específica
INSTANCE_ID="ocid1.instance.oc1.sa-saopaulo-1.antxeljrjnucp5yctmlmdargt5byzjce2dfdouwnuncrwu7kcl2ie2zmp7ba"
oci compute instance get --instance-id $INSTANCE_ID --output json

# Start/Stop instância
oci compute instance action --action START --instance-id $INSTANCE_ID
oci compute instance action --action STOP --instance-id $INSTANCE_ID
```

### **Gerenciamento de Rede**
```bash
# Obter informações do VNIC
VNIC_ID="ocid1.vnic.oc1.sa-saopaulo-1.abtxeljrq6kng5kxpc4qzzve2hps47s3yklgwdsgry42pokrxpyar7y3rrgq"
oci network vnic get --vnic-id $VNIC_ID --output json

# Verificar Security List
SECURITY_LIST_ID="ocid1.securitylist.oc1.sa-saopaulo-1.aaaaaaaaz2qvoojbladmbw75s5kep6assbhoi5frk2r6yaid7dybn653ut7a"
oci network security-list get --security-list-id $SECURITY_LIST_ID --output json
```

### **Atualização de Security Lists**
```bash
# Backup das regras atuais
oci network security-list get --security-list-id $SECURITY_LIST_ID \
  --query 'data."ingress-security-rules"' --output json > backup-ingress-rules.json

# Adicionar nova regra (exemplo: porta 9000)
oci network security-list update --security-list-id $SECURITY_LIST_ID \
  --ingress-security-rules '[
    {"description": "New Service Port", "icmp-options": null, "is-stateless": false, 
     "protocol": "6", "source": "0.0.0.0/0", "source-type": "CIDR_BLOCK", 
     "tcp-options": {"destination-port-range": {"max": 9000, "min": 9000}, 
     "source-port-range": null}, "udp-options": null},
    ...outras regras existentes...
  ]' --force
```

---

## 🖥️ Aplicações em Execução

### **Evolution API (WhatsApp)**
```
Container:    evolution-api
Port:         8080
URL Externa:  http://129.148.63.199:8080/
Manager:      http://129.148.63.199:8080/manager/
Version:      2.1.1
Status:       ✅ RUNNING
```

### **n8n (Automação)**
```
Container:    n8n  
Port:         5678
URL Externa:  http://129.148.63.199:5678/
Usuário:      admin
Senha:        N8n@2024!
Version:      1.108.1
Status:       ✅ RUNNING
```

### **PostgreSQL (Database)**
```
Container:    evolution-db
Port:         5432 (internal)
Host:         evolution-db
Usuário:      evolution
Senha:        Ev0lut10n@2024!
Databases:    evolution, n8n
Status:       ✅ RUNNING
```

---

## 📁 Estrutura de Diretórios no Servidor

### **Evolution API**
```
/opt/evolution-api/
├── .env                    # Variáveis de ambiente
├── docker-compose.yml     # Configuração dos containers
└── volumes/               # Dados persistentes
```

### **n8n**
```
/opt/n8n/
├── .env                    # Variáveis de ambiente
├── .env.backup            # Backup da configuração
├── docker-compose.yml     # Configuração do container
└── volumes/               # Dados persistentes do n8n
```

---

## 🔑 Informações de Acesso SSH

### **Chave SSH da Instância Principal**
```
Caminho:      /Users/hrocha/Documents/SSH Oracle/oci_ed25519
Permissões:   600 (rw-------)
Usuário:      ubuntu
Comando:      ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199
```

### **Comandos Docker Remotos**
```bash
# Status dos containers
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "sudo docker ps"

# Logs da Evolution API
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "sudo docker logs evolution-api -f"

# Logs do n8n
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "sudo docker logs n8n -f"

# Reiniciar serviços
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 "cd /opt/evolution-api && sudo docker compose restart"
```

---

## 🚨 Comandos de Emergência

### **Restaurar Configuração OCI CLI**
```bash
# Recriar configuração
mkdir -p ~/.oci
cat > ~/.oci/config << 'EOF'
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaa3b7gtiinwmcgo5zeqaqa7grk4je4zwmgi2ykkxyz73wih4memgnq
fingerprint=40:46:e0:0d:18:5e:ab:bd:ad:ec:b9:e9:56:54:cd:2a
tenancy=ocid1.tenancy.oc1..aaaaaaaab3khzlpcurua4ba3fh4q6uthyjz7iw52tltgfv5g3ltg2ciycw3a
region=sa-saopaulo-1
key_file=/Users/hrocha/.oci/oci_api_key.pem
EOF
chmod 600 ~/.oci/config
```

### **Gerar Nova Chave API (se necessário)**
```bash
# Gerar novo par de chaves
openssl genrsa -out ~/.oci/oci_api_key.pem 2048
openssl rsa -pubout -in ~/.oci/oci_api_key.pem -out ~/.oci/oci_api_key_public.pem
chmod 400 ~/.oci/oci_api_key.pem
chmod 444 ~/.oci/oci_api_key_public.pem

# Exibir chave pública para adicionar no OCI Console
cat ~/.oci/oci_api_key_public.pem
```

### **Emergência de Rede - Abrir Porta Temporária**
```bash
# Exemplo: abrir porta 9999 temporariamente
SECURITY_LIST_ID="ocid1.securitylist.oc1.sa-saopaulo-1.aaaaaaaaz2qvoojbladmbw75s5kep6assbhoi5frk2r6yaid7dybn653ut7a"

# Backup atual
oci network security-list get --security-list-id $SECURITY_LIST_ID \
  --query 'data."ingress-security-rules"' --output json > emergency-backup.json

# Adicionar regra de emergência (ajustar conforme necessário)
oci network security-list update --security-list-id $SECURITY_LIST_ID \
  --ingress-security-rules '[{"description": "Emergency Port", "protocol": "6", 
  "source": "0.0.0.0/0", "source-type": "CIDR_BLOCK", 
  "tcp-options": {"destination-port-range": {"max": 9999, "min": 9999}}}]' --force
```

---

## 📊 Monitoramento e Status

### **Verificação de Saúde dos Serviços**
```bash
# Status HTTP das aplicações
curl -s -o /dev/null -w "Evolution API: %{http_code}\n" http://129.148.63.199:8080/
curl -s -o /dev/null -w "n8n: %{http_code}\n" http://129.148.63.199:5678/

# Verificar via SSH se necessário
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 \
  "curl -s http://localhost:8080/ | jq '.message' && curl -s http://localhost:5678/ | head -1"
```

### **Recursos da Instância**
```bash
# Via OCI CLI
oci compute instance get --instance-id $INSTANCE_ID \
  --query 'data.{"shape":"shape","state":"lifecycle-state"}' --output json

# Via SSH
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 \
  "free -h && df -h && sudo docker stats --no-stream"
```

---

## 🔄 Procedimentos de Backup

### **Backup de Configurações**
```bash
# Backup das configurações OCI
cp -r ~/.oci ~/.oci.backup.$(date +%Y%m%d)

# Backup remoto dos arquivos de configuração
scp -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" \
  ubuntu@129.148.63.199:/opt/*/docker-compose.yml ./backup/
scp -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" \
  ubuntu@129.148.63.199:/opt/*/.env ./backup/
```

### **Backup dos Dados**
```bash
# Backup dos volumes Docker
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199 \
  "sudo docker run --rm -v evolution-api_postgres_data:/data -v /tmp:/backup alpine \
   tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz -C /data ."

# Baixar backup
scp -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" \
  ubuntu@129.148.63.199:/tmp/postgres_backup_*.tar.gz ./backup/
```

---

## 📝 Notas Importantes

### **⚠️ Avisos de Segurança**
- As chaves privadas devem ter permissão 600 ou mais restritiva
- Nunca compartilhe as chaves privadas ou credenciais em texto puro
- O secure cookie do n8n está desabilitado para permitir HTTP - considere HTTPS para produção
- As senhas estão hardcoded nos arquivos .env - considere usar secrets management

### **🔧 Configurações Específicas**
- n8n: `N8N_SECURE_COOKIE=false` para acesso HTTP
- Evolution API: Redis desabilitado, usando PostgreSQL
- PostgreSQL: Compartilhado entre Evolution API e n8n
- Timezone: America/Sao_Paulo em todos os serviços

### API KEY Evolution
Ev0lut10n_G10b4l_API_K3y_2024!@#$

### **📍 Localização dos Recursos**
- Região: São Paulo (sa-saopaulo-1)
- Availability Domain: SA-SAOPAULO-1-AD-1
- Tenancy: Compartilhado com outros recursos

---

## 🆘 Contatos e Suporte

### **Oracle Cloud Support**
- Console: https://cloud.oracle.com/
- Documentação: https://docs.oracle.com/iaas/
- OCI CLI Reference: https://docs.oracle.com/iaas/tools/oci-cli/

### **Aplicações**
- Evolution API Docs: https://doc.evolution-api.com/
- n8n Documentation: https://docs.n8n.io/

---

**📅 Última Atualização:** 25 de Agosto de 2025  
**🔄 Próxima Revisão:** Mensal ou conforme alterações na infraestrutura

---
