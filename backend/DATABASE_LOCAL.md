# 🗄️ Banco de Dados Local SQLite

Este documento explica como configurar e gerenciar o banco de dados SQLite local para desenvolvimento.

## 📋 Pré-requisitos

- Python 3.8+
- Dependências instaladas (`pip install -r requirements.txt`)

## 🚀 Configuração Inicial

### 1. Configurar variáveis de ambiente

O arquivo `.env` já está configurado para usar SQLite:

```bash
DATABASE_URL=sqlite:///./app.db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=devsecret123456789
```

### 2. Inicializar o banco

```bash
cd backend
python init_db.py
```

Este comando irá:
- Criar o arquivo `app.db` (banco SQLite)
- Criar todas as tabelas baseadas nos modelos
- Configurar o modo WAL para melhor performance

## 🔧 Gerenciamento do Banco

### Script de Gerenciamento

Use o script `manage_db.py` para operações comuns:

```bash
# Ver status do banco
python manage_db.py status

# Criar backup
python manage_db.py backup

# Resetar banco (remover e recriar)
python manage_db.py reset

# Ver ajuda
python manage_db.py help
```

### Operações Manuais

#### Backup Manual
```bash
cp app.db backup_$(date +%Y%m%d_%H%M%S).db
```

#### Reset Manual
```bash
rm app.db
python init_db.py
```

## 📊 Estrutura do Banco

O banco SQLite contém as seguintes tabelas principais:

- **projects** - Projetos do sistema
- **domains** - Domínios associados aos projetos
- **prompts** - Prompts de IA
- **prompt_versions** - Versões dos prompts
- **engines** - Motores de IA
- **conversations** - Conversas
- **messages** - Mensagens das conversas
- **sessions** - Sessões de usuário

## 🔍 Inspeção do Banco

### Usando SQLite CLI

```bash
# Conectar ao banco
sqlite3 app.db

# Listar tabelas
.tables

# Ver estrutura de uma tabela
.schema projects

# Executar consulta
SELECT * FROM projects LIMIT 5;

# Sair
.quit
```

### Usando Python

```python
from app.db.session import SessionLocal
from app.models.models import Project

db = SessionLocal()
projects = db.query(Project).all()
print(f"Total de projetos: {len(projects)}")
db.close()
```

## ⚠️ Considerações Importantes

### Vantagens do SQLite Local
- ✅ Não requer servidor externo
- ✅ Arquivo único, fácil de backup
- ✅ Suporte nativo no Python
- ✅ Ideal para desenvolvimento

### Limitações
- ❌ Não suporta múltiplas conexões simultâneas (para produção)
- ❌ Performance pode ser menor para grandes volumes
- ❌ Não tem recursos avançados de clustering

### Migração para Produção
Quando estiver pronto para produção, você pode:
1. Migrar para PostgreSQL/MySQL
2. Usar Azure SQL (quando estiver funcionando)
3. Configurar replicação e backup automático

## 🐛 Troubleshooting

### Erro: "database is locked"
- Feche todas as conexões Python
- Verifique se não há outros processos usando o banco
- Reinicie a aplicação

### Erro: "no such table"
- Execute `python init_db.py` para criar as tabelas
- Verifique se o arquivo `app.db` existe

### Performance lenta
- O SQLite usa WAL mode por padrão
- Para grandes operações, considere usar transações
- Evite muitas operações simultâneas

## 📚 Recursos Adicionais

- [Documentação SQLite](https://www.sqlite.org/docs.html)
- [SQLAlchemy com SQLite](https://docs.sqlalchemy.org/en/14/dialects/sqlite.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)

## 🔄 Migração de Dados

Se você tiver dados no Azure SQL e quiser migrar para SQLite local:

1. Exporte os dados do Azure SQL
2. Crie o banco local com `python init_db.py`
3. Importe os dados usando scripts de migração
4. Verifique a integridade dos dados

---

💡 **Dica**: Mantenha backups regulares do seu banco local durante o desenvolvimento!