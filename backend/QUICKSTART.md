# 🚀 Início Rápido - Banco Local SQLite

## ✅ Pré-requisitos Atendidos

- ✅ Python 3.13 instalado
- ✅ Ambiente virtual criado (`venv`)
- ✅ Dependências instaladas
- ✅ Banco SQLite configurado
- ✅ Scripts de gerenciamento criados

## 🎯 Comandos Essenciais

### 1. Ativar Ambiente Virtual
```bash
source venv/bin/activate
```

### 2. Ver Status do Banco
```bash
python manage_db.py status
```

### 3. Executar Aplicação
```bash
python run_local.py
```

### 4. Acessar Aplicação
- 🌐 **API**: http://localhost:8000
- 📚 **Documentação**: http://localhost:8000/docs
- 🔍 **ReDoc**: http://localhost:8000/redoc

## 🔧 Gerenciamento do Banco

### Backup
```bash
python manage_db.py backup
```

### Reset (CUIDADO!)
```bash
python manage_db.py reset
```

### Recriar Banco
```bash
python init_db.py
```

## 📁 Arquivos Importantes

- **`app.db`** - Banco de dados SQLite
- **`.env`** - Configurações de ambiente
- **`init_db.py`** - Script de inicialização do banco
- **`manage_db.py`** - Gerenciamento do banco
- **`run_local.py`** - Execução da aplicação

## 🐛 Troubleshooting

### Erro: "No module named..."
```bash
source venv/bin/activate
pip install -r requirements_basic.txt
```

### Banco corrompido
```bash
python manage_db.py reset
python init_db.py
```

### Porta em uso
```bash
# Altere a porta no arquivo run_local.py
port = 8001  # ou outra porta disponível
```

## 🔄 Próximos Passos

1. **Testar API**: Acesse http://localhost:8000/docs
2. **Criar Dados**: Use os endpoints da API
3. **Monitorar Banco**: Use `python manage_db.py status`
4. **Desenvolvimento**: Modifique código e veja mudanças automáticas

## 💡 Dicas

- Mantenha o ambiente virtual ativado durante o desenvolvimento
- Use `python manage_db.py backup` antes de grandes mudanças
- O modo reload detecta alterações automaticamente
- SQLite é ideal para desenvolvimento, mas considere PostgreSQL para produção

---

🎉 **Seu banco local está funcionando!** Agora você pode desenvolver sem depender do Azure SQL.