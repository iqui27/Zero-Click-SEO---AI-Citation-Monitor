# FIXME: tasks.py - Correção de Indentação

## Problema

O arquivo `backend/app/services/tasks.py` precisa ter TODO o bloco de cálculo de IM metrics (linhas 507-662) indentado com +4 espaços para ficar dentro do `try:` que começa na linha 493.

## Solução Manual

1. Abrir `backend/app/services/tasks.py`
2. Selecionar as linhas 507 até 662 (todo o bloco de IM metrics até o `except Exception as e:`)
3. Adicionar 4 espaços de indentação em TODAS essas linhas
4. Salvar

## Ou usar este comando:

```bash
cd /Users/hrocha/Documents/Projetos/SEO\ Analyzer

# Fazer backup
cp backend/app/services/tasks.py backend/app/services/tasks.py.backup

# Aplicar indentação (linhas 507-662)
sed -i.bak '507,662s/^/    /' backend/app/services/tasks.py
```

## Alternativamente: Reverter e Aplicar Patch Simples

```bash
# Reverter mudanças
git checkout backend/app/services/tasks.py

# Aplicar apenas a verificação LLM sem mexer na estrutura
# Adicionar após linha 478:
```

```python
        # === VERIFICAR TIPO DE ENGINE: SERP vs LLM ===
        engine = db.get(Engine, run.engine_id) if run.engine_id else None
        engine_name = engine.name.lower() if engine else ""
        is_llm = any(llm in engine_name for llm in ["chatgpt", "gemini", "perplexity", "claude", "gpt", "openai"])
        
        print(f"[ENGINE_TYPE] Run {run.id} - Engine: {engine_name} - Is LLM: {is_llm}")
        
        if is_llm:
            print(f"[DEBUG] Pulando IM-SEO metrics - run é LLM (métricas GEO serão calculadas em semantic insights)")
            # Salvar response_text se disponível
            response_text = (last_parsed or {}).get("text") if last_parsed else None
            if response_text:
                run.response_text = response_text[:50000]
                db.commit()
            
            # Enfileirar semantic insights (que inclui GEO)
            if settings.semantic_insights_enabled and response_text:
                try:
                    process_semantic_insights.delay(run.id)
                    _log(db, run.id, "semantic_insights", "queued", "Gemini semantic insights + GEO metrics enqueued")
                except Exception as queue_err:
                    print(f"[SEMANTIC] Falha ao enfileirar insights para run {run.id}: {queue_err}")
                    _log(db, run.id, "semantic_insights", "fail", f"queue error: {queue_err}")
            else:
                _log(db, run.id, "semantic_insights", "skip", "No response_text or semantic insights disabled")
            
            # Pular para o final (não calcular IM metrics)
            # NOTA: Adicionar um 'pass' ou 'continue' aqui dependendo da estrutura
        else:
            # Continuar com IM metrics normalmente...
```

## Status

- ❌ Arquivo com erro de sintaxe
- ⏳ Aguardando correção manual
- ✅ Lógica de separação LLM vs SERP implementada (mas com indentação errada)

## Teste Após Correção

```bash
# Verificar sintaxe
python3 -m py_compile backend/app/services/tasks.py

# Rebuild e restart
docker compose build backend && docker compose up -d backend

# Verificar logs
docker compose logs backend --tail 50 | grep ENGINE_TYPE
```
