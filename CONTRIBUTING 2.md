# Guia de Contribuição

Obrigado por contribuir com o Zero-Click SEO Monitor! Este documento fornece diretrizes para contribuições.

---

## 🎯 Como Contribuir

### 1. Encontre ou Crie uma Issue

- Verifique se já existe uma issue relacionada
- Se não existir, crie uma nova descrevendo:
  - O problema ou feature
  - Contexto e motivação
  - Solução proposta (se aplicável)

### 2. Faça Fork e Clone

```bash
# Fork no GitHub/GitLab
# Clone seu fork
git clone <seu-fork-url>
cd "SEO Analyzer"

# Adicione o upstream
git remote add upstream <repo-original-url>
```

### 3. Crie uma Branch

```bash
# Atualize main
git checkout main
git pull upstream main

# Crie branch para sua feature/fix
git checkout -b feature/nome-da-feature
# ou
git checkout -b fix/nome-do-bug
```

**Convenção de nomes:**
- `feature/` - Nova funcionalidade
- `fix/` - Correção de bug
- `docs/` - Apenas documentação
- `refactor/` - Refatoração de código
- `test/` - Adição de testes
- `chore/` - Tarefas de manutenção

### 4. Desenvolva

- Siga os padrões de código do projeto
- Escreva código limpo e bem documentado
- Adicione testes se aplicável
- Teste localmente antes de commitar

### 5. Commit

Use **Conventional Commits**:

```bash
# Formato
<type>(<scope>): <subject>

# Exemplos
git commit -m "feat(api): adicionar endpoint de exportação CSV"
git commit -m "fix(frontend): corrigir bug no SSE streaming"
git commit -m "docs(readme): atualizar instruções de setup"
git commit -m "refactor(services): extrair lógica de classificação"
git commit -m "test(kpis): adicionar testes para cálculo de ZCRS"
git commit -m "chore(deps): atualizar dependências do backend"
```

**Types:**
- `feat` - Nova feature
- `fix` - Bug fix
- `docs` - Documentação
- `style` - Formatação (não afeta lógica)
- `refactor` - Refatoração
- `test` - Testes
- `chore` - Manutenção
- `perf` - Performance
- `ci` - CI/CD

**Scopes (opcional):**
- `api` - Backend API
- `frontend` - Frontend
- `services` - Serviços backend
- `models` - Modelos de dados
- `adapters` - Integrações externas
- `ui` - Componentes UI

### 6. Push e Pull Request

```bash
# Push para seu fork
git push origin feature/nome-da-feature

# Crie Pull Request no GitHub/GitLab
```

**Template de PR:**

```markdown
## 📝 Descrição

[Descreva o que foi feito e por quê]

## 🔗 Issue Relacionada

Closes #123

## 🎯 Tipo de Mudança

- [ ] 🐛 Bug fix (mudança que corrige um problema)
- [ ] ✨ Nova feature (mudança que adiciona funcionalidade)
- [ ] 💥 Breaking change (fix ou feature que quebra compatibilidade)
- [ ] 📝 Documentação
- [ ] 🎨 Refatoração (sem mudança funcional)
- [ ] ✅ Testes

## 🧪 Como Testar

1. [Passo 1]
2. [Passo 2]
3. [Resultado esperado]

## 📸 Screenshots (se aplicável)

[Adicione screenshots ou GIFs]

## ✅ Checklist

- [ ] Código segue os padrões do projeto
- [ ] Testei localmente e funciona
- [ ] Adicionei/atualizei testes (se aplicável)
- [ ] Adicionei/atualizei documentação (se aplicável)
- [ ] Sem warnings ou erros no console
- [ ] Commits seguem Conventional Commits
- [ ] Branch está atualizada com main
```

---

## 📋 Padrões de Código

### Python (Backend)

**Style Guide:** PEP 8

```python
# ✅ Bom
def calculate_zcrs(citations: List[Citation], domains: List[Domain]) -> float:
    """
    Calcula Zero-Click Response Score.
    
    Args:
        citations: Lista de citações extraídas
        domains: Lista de domínios do projeto
        
    Returns:
        Score de 0.0 a 100.0
    """
    our_citations = [c for c in citations if is_our_domain(c.url, domains)]
    total = len(citations)
    return (len(our_citations) / total * 100) if total > 0 else 0.0

# ❌ Ruim
def calc(c,d):
    o=[x for x in c if check(x.url,d)]
    return len(o)/len(c)*100 if len(c)>0 else 0
```

**Imports:**
```python
# Ordem: stdlib, third-party, local
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.models import Run, Citation
from app.services.kpis import compute_zcrs
```

**Type Hints:**
```python
# Sempre use type hints
def process_run(run_id: str, db: Session) -> dict:
    ...

# Para tipos complexos
from typing import List, Dict, Optional, Union

def get_stats(project_id: str) -> Dict[str, Union[int, float]]:
    ...
```

**Docstrings:**
```python
def complex_function(param1: str, param2: int) -> dict:
    """
    Breve descrição de uma linha.
    
    Descrição mais detalhada se necessário.
    Pode ter múltiplas linhas.
    
    Args:
        param1: Descrição do parâmetro 1
        param2: Descrição do parâmetro 2
        
    Returns:
        Descrição do retorno
        
    Raises:
        ValueError: Quando param2 é negativo
    """
    ...
```

### TypeScript (Frontend)

**Style Guide:** Airbnb + Prettier

```typescript
// ✅ Bom
interface RunCardProps {
  run: RunListItem
  onDelete: (id: string) => void
}

export const RunCard: React.FC<RunCardProps> = ({ run, onDelete }) => {
  const [loading, setLoading] = useState(false)
  
  const handleDelete = async () => {
    setLoading(true)
    try {
      await deleteRun(run.id)
      onDelete(run.id)
      toast.success('Run deleted')
    } catch (error) {
      toast.error('Failed to delete run')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Card>
      <CardContent>
        <h3>{run.id}</h3>
        <Button onClick={handleDelete} disabled={loading}>
          Delete
        </Button>
      </CardContent>
    </Card>
  )
}

// ❌ Ruim
export default function RC(props: any) {
  const [l, setL] = useState(false)
  return <div onClick={() => props.onDel(props.r.id)}>{props.r.id}</div>
}
```

**Naming:**
```typescript
// Components: PascalCase
export const RunDetail: React.FC = () => {}

// Functions: camelCase
const handleSubmit = () => {}

// Constants: UPPER_SNAKE_CASE
const MAX_RETRIES = 3

// Types/Interfaces: PascalCase
interface RunListItem {}
type Status = 'queued' | 'running' | 'completed'
```

**Async/Await:**
```typescript
// ✅ Bom
const loadData = async () => {
  try {
    const response = await fetchData()
    setData(response.data)
  } catch (error) {
    console.error('Failed to load:', error)
    toast.error('Failed to load data')
  }
}

// ❌ Ruim
fetchData().then(r => setData(r.data)).catch(e => console.log(e))
```

---

## 🧪 Testes

### Backend Tests

```python
# tests/test_kpis.py
import pytest
from app.services.kpis import compute_zcrs
from app.models.models import Citation, Domain

def test_zcrs_with_our_citations():
    citations = [
        Citation(url="https://bb.com.br/page1"),
        Citation(url="https://competitor.com/page2"),
    ]
    domains = [Domain(domain="bb.com.br")]
    
    result = compute_zcrs(citations, domains)
    
    assert result == 50.0

def test_zcrs_without_citations():
    result = compute_zcrs([], [])
    assert result == 0.0

@pytest.mark.asyncio
async def test_run_creation():
    # Test async functions
    ...
```

**Executar:**
```bash
cd backend
pytest tests/ -v
pytest tests/test_kpis.py -v
pytest tests/ -k "test_zcrs" -v
```

### Frontend Tests

```typescript
// src/__tests__/RunCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { RunCard } from '@/components/RunCard'

describe('RunCard', () => {
  it('renders run id', () => {
    const run = { id: 'run_123', status: 'completed' }
    render(<RunCard run={run} onDelete={() => {}} />)
    expect(screen.getByText('run_123')).toBeInTheDocument()
  })
  
  it('calls onDelete when button clicked', () => {
    const onDelete = jest.fn()
    const run = { id: 'run_123', status: 'completed' }
    render(<RunCard run={run} onDelete={onDelete} />)
    
    fireEvent.click(screen.getByText('Delete'))
    expect(onDelete).toHaveBeenCalledWith('run_123')
  })
})
```

**Executar:**
```bash
cd frontend
npm test
npm test -- --coverage
```

---

## 📝 Documentação

### Quando Documentar

- **Sempre:** Funções públicas, classes, módulos
- **Quando complexo:** Lógica não óbvia
- **Quando útil:** Decisões arquiteturais, trade-offs

### O Que Documentar

**Código:**
```python
# Docstrings para funções públicas
# Comentários inline para lógica complexa
# Type hints sempre
```

**README/Docs:**
- Atualize se mudar comportamento
- Adicione exemplos de uso
- Documente breaking changes

### Onde Documentar

- `README.md` - Overview e quick start
- `DEVELOPER_GUIDE.md` - Guia completo
- `ARCHITECTURE.md` - Decisões arquiteturais
- `QUICK_REFERENCE.md` - Comandos comuns
- Docstrings/JSDoc - Código

---

## 🔍 Code Review

### Para Reviewers

**O que verificar:**
- [ ] Código funciona e resolve o problema
- [ ] Segue padrões do projeto
- [ ] Tem testes (se aplicável)
- [ ] Documentação atualizada
- [ ] Sem código duplicado
- [ ] Performance adequada
- [ ] Segurança (inputs validados, sem secrets)
- [ ] Commits bem escritos

**Como fazer review:**
- Seja construtivo e educado
- Explique o "porquê" dos comentários
- Sugira alternativas
- Aprove quando estiver bom

**Exemplo de comentário:**
```
❌ "Este código está ruim"
✅ "Podemos simplificar usando list comprehension:
   `items = [x for x in data if x.active]`
   Isso é mais Pythonic e legível."
```

### Para Authors

**Respondendo a review:**
- Agradeça o feedback
- Faça perguntas se não entender
- Implemente sugestões ou explique por que não
- Marque conversas como resolvidas

**Após aprovação:**
- Faça squash de commits se necessário
- Merge usando a estratégia definida (squash/rebase/merge)

---

## 🚫 O Que NÃO Fazer

### ❌ Commits Ruins

```bash
# Muito vago
git commit -m "fix"
git commit -m "update"
git commit -m "changes"

# Muito longo (deveria ser múltiplos commits)
git commit -m "add feature X, fix bug Y, refactor Z, update docs"
```

### ❌ Código Ruim

```python
# Sem type hints
def process(data):
    return data.filter()

# Nomes ruins
def f(x, y):
    return x + y

# Código comentado
# old_function()
# if False:
#     do_something()

# Print statements (use logging)
print("Debug:", data)
```

### ❌ PRs Ruins

- PR gigante (500+ linhas) sem explicação
- Mistura múltiplas features/fixes
- Sem descrição ou contexto
- Não testado
- Quebra testes existentes

---

## ✅ Checklist Final

Antes de criar PR, verifique:

- [ ] Código funciona localmente
- [ ] Testes passam (se houver)
- [ ] Sem warnings/errors no console
- [ ] Código segue padrões do projeto
- [ ] Commits seguem Conventional Commits
- [ ] Branch atualizada com main
- [ ] Documentação atualizada (se necessário)
- [ ] PR tem descrição clara
- [ ] Screenshots adicionados (se mudança visual)

---

## 🎓 Recursos

### Aprendizado

- [Conventional Commits](https://www.conventionalcommits.org/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)

### Ferramentas

- **Linting:**
  - Backend: `flake8`, `black`, `mypy`
  - Frontend: `eslint`, `prettier`
- **Testing:**
  - Backend: `pytest`
  - Frontend: `vitest`, `@testing-library/react`
- **Git:**
  - `git rebase -i` - Interactive rebase
  - `git commit --amend` - Amend last commit
  - `git stash` - Stash changes

---

## 🤝 Comunidade

### Comunicação

- **Issues:** Para bugs e features
- **Discussions:** Para perguntas e ideias
- **Slack/Teams:** Para discussões rápidas
- **Email:** Para questões privadas

### Código de Conduta

- Seja respeitoso e profissional
- Aceite feedback construtivo
- Ajude outros desenvolvedores
- Mantenha discussões focadas e produtivas

---

## 📞 Precisa de Ajuda?

- Leia a documentação primeiro
- Procure em issues existentes
- Pergunte no Slack/Teams
- Crie uma issue se necessário

---

**Obrigado por contribuir! 🎉**

Sua contribuição ajuda a tornar este projeto melhor para todos.

---

**Versão**: 1.0  
**Última atualização**: Janeiro 2025
