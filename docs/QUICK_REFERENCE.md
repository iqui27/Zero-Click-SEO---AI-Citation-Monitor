# Quick Reference - Zero-Click SEO Monitor

Referência rápida para comandos e padrões comuns. Mantenha este documento aberto durante o desenvolvimento!

---

## 🐳 Docker Commands

```bash
# Start/Stop
docker compose up -d                    # Start all services
docker compose down                     # Stop all services
docker compose down -v                  # Stop and remove volumes (⚠️ deletes data)
docker compose restart backend          # Restart specific service

# Build
docker compose up -d --build            # Rebuild and start
docker compose build --no-cache backend # Force rebuild without cache

# Logs
docker compose logs -f                  # All logs (follow)
docker compose logs -f backend          # Backend logs only
docker compose logs -f worker           # Worker logs only
docker compose logs --tail=100 backend  # Last 100 lines

# Status
docker compose ps                       # List containers
docker compose top                      # Show running processes

# Shell Access
docker compose exec backend bash        # Backend shell
docker compose exec frontend sh         # Frontend shell
docker compose exec redis redis-cli     # Redis CLI
docker compose exec backend bash -lc 'PYTHONPATH=/app python scripts/backfill_semantic_insights.py --days 30'  # Reprocess insights semânticos

# Cleanup
docker system prune -a                  # Clean everything (⚠️ careful!)
docker volume prune                     # Clean unused volumes
```

---

## 🔧 Development Workflow

### Backend Changes

```bash
# 1. Edit code in backend/app/
# 2. FastAPI auto-reloads (no restart needed)
# 3. Check logs
docker compose logs -f backend

# If you change requirements.txt or Dockerfile:
docker compose up -d --build backend
```
**Worker/Celery**
```bash
# Escutar as filas runs + celery (necessário para processar insights semânticos)
docker compose exec worker bash -lc "celery -A celery_app.celery_app worker -Q runs,celery -l info"

# Backfill manual dos insights (últimos 30 dias)
docker compose exec backend bash -lc "PYTHONPATH=/app python scripts/backfill_semantic_insights.py --days 30"
```

### Frontend Changes

```bash
# 1. Edit code in frontend/src/
# 2. Vite HMR updates automatically
# 3. Check browser console

# If you change package.json:
docker compose exec frontend npm install
docker compose restart frontend
```

### Database Changes

```bash
# 1. Edit backend/app/models/models.py
# 2. Add migration in backend/app/main.py (on_startup)
# 3. Restart backend
docker compose restart backend

# 4. Verify migration ran
docker compose logs backend | grep MIGRATION
```

---

## 📝 Code Patterns

### Backend: Add New Endpoint

```python
# backend/app/api/routes.py

from app.models.models import MyModel
from app.schemas.schemas import MyModelOut, MyModelCreate

@api_router.post("/my-endpoint", response_model=MyModelOut)
def create_my_model(
    payload: MyModelCreate,
    db: Session = Depends(get_db)
):
    obj = MyModel(**payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@api_router.get("/my-endpoint/{id}", response_model=MyModelOut)
def get_my_model(id: str, db: Session = Depends(get_db)):
    obj = db.get(MyModel, id)
    if not obj:
        raise HTTPException(404, "Not found")
    return obj
```

### Backend: Add New Model

```python
# backend/app/models/models.py

class MyModel(Base):
    __tablename__ = "my_models"
    
    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("mdl"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    project: Mapped[Project] = relationship(back_populates="my_models")
```

### Backend: Add Schema

```python
# backend/app/schemas/schemas.py

from pydantic import BaseModel, Field

class MyModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class MyModelOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### Backend: Add Migration

```python
# backend/app/main.py (in on_startup function)

# For SQL Server (Azure SQL)
_exec_safe("""
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'my_table' AND COLUMN_NAME = 'my_column'
    )
    BEGIN
        ALTER TABLE my_table ADD my_column VARCHAR(255) NULL;
    END
""", "Add my_table.my_column")

# For PostgreSQL (if using)
stmts = [
    "ALTER TABLE my_table ADD COLUMN IF NOT EXISTS my_column VARCHAR(255)",
]
```

### Frontend: Add API Function

```typescript
// frontend/src/lib/api.ts

export type MyModel = {
  id: string
  name: string
  description?: string
  created_at: string
}

export const getMyModels = () =>
  http.get<MyModel[]>('/my-endpoint')

export const createMyModel = (data: { name: string; description?: string }) =>
  http.post<MyModel>('/my-endpoint', data)

export const deleteMyModel = (id: string) =>
  http.delete(`/my-endpoint/${id}`)
```

### Frontend: Add Component

```tsx
// frontend/src/components/MyComponent.tsx

import { useState, useEffect } from 'react'
import { getMyModels, type MyModel } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

export default function MyComponent() {
  const [items, setItems] = useState<MyModel[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadItems()
  }, [])

  const loadItems = async () => {
    try {
      const response = await getMyModels()
      setItems(response.data)
    } catch (error) {
      console.error('Failed to load items:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">My Items</h1>
      <div className="grid gap-4">
        {items.map(item => (
          <Card key={item.id}>
            <CardHeader>
              <CardTitle>{item.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{item.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

---

## 🔍 Common Queries

### Database Queries (Python)

```python
# In Python shell: docker compose exec backend python

from app.db.session import SessionLocal
from app.models.models import Run, Project, Citation
from sqlalchemy import func, desc

db = SessionLocal()

# Get all runs
runs = db.query(Run).all()

# Get runs by project
runs = db.query(Run).filter(Run.project_id == "prj_12345678").all()

# Get completed runs
runs = db.query(Run).filter(Run.status == "completed").all()

# Get runs with citations
runs = db.query(Run).filter(Run.citations_count > 0).all()

# Get recent runs
runs = db.query(Run).order_by(desc(Run.started_at)).limit(10).all()

# Count runs by status
counts = db.query(Run.status, func.count(Run.id))\
    .group_by(Run.status)\
    .all()

# Get run with citations (eager load)
from sqlalchemy.orm import joinedload
run = db.query(Run)\
    .options(joinedload(Run.citations))\
    .filter(Run.id == "run_12345678")\
    .first()

# Delete old runs
db.query(Run).filter(Run.status == "error").delete()
db.commit()
```

### API Queries (curl)

```bash
# Health check
curl http://localhost:8000/health

# List projects
curl http://localhost:8000/api/projects

# Create project
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "country": "BR", "language": "pt-BR"}'

# Get run
curl http://localhost:8000/api/runs/run_12345678

# List runs (with filters)
curl "http://localhost:8000/api/runs?status=completed&limit=10"

# Create run
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "prj_12345678",
    "prompt_version_id": "pv_87654321",
    "engines": [{"name": "gemini-2.0-flash"}],
    "cycles": 1
  }'

# Delete run
curl -X DELETE http://localhost:8000/api/runs/run_12345678

# SSE stream (in terminal)
curl -N http://localhost:8000/api/runs/run_12345678/stream
```

---

## 🎨 UI Components (shadcn/ui)

### Common Components

```tsx
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'

// Button
<Button onClick={handleClick}>Click me</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline" size="sm">Small</Button>

// Card
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
  </CardHeader>
  <CardContent>
    Content here
  </CardContent>
</Card>

// Badge
<Badge>Default</Badge>
<Badge variant="destructive">Error</Badge>
<Badge variant="outline">Outline</Badge>

// Dialog
<Dialog>
  <DialogTrigger asChild>
    <Button>Open</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
    </DialogHeader>
    <p>Dialog content</p>
  </DialogContent>
</Dialog>

// Select
<Select value={value} onValueChange={setValue}>
  <SelectTrigger>
    <SelectValue placeholder="Select..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="option1">Option 1</SelectItem>
    <SelectItem value="option2">Option 2</SelectItem>
  </SelectContent>
</Select>

// Input
<Input
  type="text"
  placeholder="Enter text..."
  value={value}
  onChange={(e) => setValue(e.target.value)}
/>

// Textarea
<Textarea
  placeholder="Enter text..."
  value={value}
  onChange={(e) => setValue(e.target.value)}
/>

// Toast
toast.success('Success message')
toast.error('Error message')
toast.info('Info message')
```

### TailwindCSS Common Classes

```tsx
// Layout
<div className="flex items-center justify-between">
<div className="grid grid-cols-3 gap-4">
<div className="space-y-4">

// Spacing
<div className="p-4">      // padding all sides
<div className="px-4 py-2"> // padding x and y
<div className="mt-4">     // margin top
<div className="mb-2">     // margin bottom

// Typography
<h1 className="text-2xl font-bold">
<p className="text-sm text-gray-500">
<span className="font-semibold">

// Colors
<div className="bg-blue-500 text-white">
<div className="border border-gray-200">
<div className="hover:bg-gray-100">

// Sizing
<div className="w-full h-64">
<div className="max-w-4xl mx-auto">

// Responsive
<div className="hidden md:block">  // Hidden on mobile, visible on md+
<div className="grid grid-cols-1 md:grid-cols-3">
```

---

## 🧪 Testing Snippets

### Test Run Creation

```python
# In Python shell
from app.db.session import SessionLocal
from app.models.models import Project, Engine, Prompt, PromptVersion, Run

db = SessionLocal()

# Create test project
project = Project(name="Test Project", country="BR", language="pt-BR")
db.add(project)
db.commit()

# Create engine
engine = Engine(project_id=project.id, name="gemini-2.0-flash")
db.add(engine)
db.commit()

# Create prompt
prompt = Prompt(project_id=project.id, name="Test", text="Hello")
db.add(prompt)
db.commit()

# Create prompt version
pv = PromptVersion(prompt_id=prompt.id, version=1, text="Hello")
db.add(pv)
db.commit()

# Create run
run = Run(
    project_id=project.id,
    engine_id=engine.id,
    prompt_version_id=pv.id,
    status="queued"
)
db.add(run)
db.commit()

print(f"Created run: {run.id}")
```

### Test API Endpoint

```bash
# Create project
PROJECT_ID=$(curl -s -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "country": "BR"}' | jq -r '.id')

echo "Project ID: $PROJECT_ID"

# Add domain
curl -X POST http://localhost:8000/api/projects/$PROJECT_ID/domains \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "is_primary": true}'

# List domains
curl http://localhost:8000/api/projects/$PROJECT_ID/domains | jq
```

---

## 🔐 Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

# Optional
PERPLEXITY_API_KEY=your_perplexity_key
SERPAPI_KEY=your_serpapi_key

# Database (Azure SQL)
DATABASE_URL=mssql+pyodbc://user:pass@server:1433/db?driver=ODBC+Driver+18+for+SQL+Server

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI Organization (optional)
OPENAI_ORG_ID=org-cwSHSUpwENqGkjtok0zVm4cu
OPENAI_PROJECT_ID=proj_5KNRTmP5Ojg4fqdEBloLhile
```

---

## 🐛 Debug Helpers

### Backend Debug

```python
# Add to any file
import logging
logger = logging.getLogger(__name__)

# Log levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")

# Pretty print
import json
print(json.dumps(data, indent=2))

# Breakpoint
import pdb; pdb.set_trace()

# Time execution
import time
start = time.time()
# ... code ...
print(f"Took {time.time() - start:.2f}s")
```

### Frontend Debug

```typescript
// Console
console.log('Data:', data)
console.table(array)
console.error('Error:', error)
console.time('operation')
// ... code ...
console.timeEnd('operation')

// Debugger
debugger;  // Browser will pause here

// React DevTools
// Install extension and inspect components
```

---

## 📊 Common Metrics/KPIs

```python
# AMR (AI Mention Rate)
amr = bool(our_citations_count > 0)

# DCR (Domain Citation Rate)
dcr = bool(specific_domain_cited)

# ZCRS (Zero-Click Response Score)
zcrs = (our_citations_count / total_citations_count) * 100 if total_citations_count > 0 else 0

# SoV-AI (Share of Voice - AI)
sov_ai = (our_citations / total_citations_in_category) * 100
```

---

## 🚨 Emergency Commands

```bash
# Backend not responding
docker compose restart backend

# Worker stuck
docker compose restart worker
docker compose exec redis redis-cli FLUSHALL  # ⚠️ Clears queue

# Database connection issues
docker compose logs backend | grep -i error
# Check DATABASE_URL in .env

# Frontend not loading
docker compose exec frontend rm -rf node_modules
docker compose restart frontend

# Everything broken
docker compose down -v
docker system prune -a
docker compose up -d --build

# Check disk space
df -h
docker system df
```

---

## 📚 Useful Links

- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **Gemini API**: https://ai.google.dev/docs
- **OpenAI API**: https://platform.openai.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **shadcn/ui**: https://ui.shadcn.com
- **TailwindCSS**: https://tailwindcss.com/docs

---

## 💡 Pro Tips

1. **Keep logs open**: `docker compose logs -f backend worker`
2. **Use Swagger**: Test APIs at http://localhost:8000/docs
3. **Browser DevTools**: F12 is your friend
4. **Git commits**: Use conventional commits (feat:, fix:, docs:)
5. **Ask for help**: Don't spend hours stuck on something
6. **Read errors**: Error messages usually tell you exactly what's wrong
7. **Test locally**: Always test before pushing
8. **Document**: If you figured something out, document it!

---

**Última atualização**: Janeiro 2025  
**Contribua**: Se você descobrir algo útil, adicione aqui!
