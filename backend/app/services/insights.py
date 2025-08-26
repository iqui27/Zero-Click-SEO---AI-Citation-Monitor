from __future__ import annotations

from typing import List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
import os

from app.models.models import Run, Citation, Insight, Domain, Engine, PromptVersion


def generate_basic_insights(db: Session, run: Run) -> List[Insight]:
    """Gera insights heurísticos simples pós-run.
    - Se não houver citações do domínio alvo: sugerir FAQ/HowTo, atualizar conteúdos e comparativos
    - Se houver citações concorrentes recorrentes: sugerir página comparativa
    """
    insights: List[Insight] = []
    project_domains = {d.domain for d in db.query(Domain).filter(Domain.project_id == run.project_id).all()}
    citations = db.query(Citation).filter(Citation.run_id == run.id).all()
    our_hit = any(c.domain in project_domains for c in citations)

    if not our_hit:
        insights.append(Insight(
            project_id=run.project_id,
            run_id=run.id,
            title="Por que não citou?",
            description="Não encontramos citações ao seu domínio nesta resposta. Avalie adicionar FAQ/HowTo, atualizar conteúdo e páginas comparativas com concorrentes.",
            impact=3,
            effort=2,
            status="open",
        ))

    # Top concorrente desta run
    competitor_domains = [c.domain for c in citations if c.domain not in project_domains]
    if competitor_domains:
        top = competitor_domains[0]
        insights.append(Insight(
            project_id=run.project_id,
            run_id=run.id,
            title=f"Concorrente citado: {top}",
            description=f"Crie/otimize uma página comparativa com {top} e adicione dados estruturados (FAQ/HowTo).",
            impact=2,
            effort=2,
            status="open",
        ))

    return insights



def generate_subproject_insights(db: Session, subproject_id: str) -> Dict[str, Any]:
    """Gera um relatório completo (via LLM quando disponível) consolidando as runs de um subprojeto.

    Estrutura de saída:
    {
      summary: string[],
      recommendations: [{ title, impact?, effort? }],
      quick_wins: string[],
      topics: string[],
      keywords: string[],
      wordcloud: [{ token, weight }]
    }
    """
    # Coleta de dados básicos do subprojeto
    runs = (
        db.query(
            Run.id,
            Run.status,
            Run.started_at,
            Run.finished_at,
            Run.zcrs,
            Run.cost_usd,
            Run.tokens_total,
            Run.amr_flag,
            Run.dcr_flag,
            Run.model_name,
            Engine.name.label("engine"),
            Engine.config_json.label("engine_config"),
            Run.project_id,
            PromptVersion.text.label("prompt_text"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .filter(Run.subproject_id == subproject_id)
        .order_by(Run.started_at.desc().nullslast())
        .limit(200)
        .all()
    )
    citations = (
        db.query(Citation.run_id, Citation.domain, Citation.url)
        .join(Run, Run.id == Citation.run_id)
        .filter(Run.subproject_id == subproject_id)
        .limit(1000)
        .all()
    )

    # Anexar evidências (resposta e links) e opts efetivos por run
    run_ids = [r.id for r in runs]
    ev_map: Dict[str, Dict[str, Any]] = {}
    if run_ids:
        from app.models.models import Evidence, RunEvent  # import local para evitar ciclos
        ev_rows = (
            db.query(Evidence)
            .filter(Evidence.run_id.in_(run_ids))
            .order_by(Evidence.id.desc())
            .all()
        )
        for ev in ev_rows:
            if ev.run_id not in ev_map:
                ev_map[ev.run_id] = ev.parsed_json or {}
    opts_map: Dict[str, Any] = {}
    if run_ids:
        from app.models.models import RunEvent  # local
        evt_rows = (
            db.query(RunEvent)
            .filter(RunEvent.run_id.in_(run_ids), RunEvent.version == "opts")
            .order_by(RunEvent.created_at.desc())
            .all()
        )
        import json as _json
        for e in evt_rows:
            if e.run_id in opts_map:
                continue
            try:
                opts_map[e.run_id] = _json.loads(e.message or "{}")
            except Exception:
                opts_map[e.run_id] = {"raw": (e.message or "")[:500]}

    def _subset_cfg(cfg: Dict[str, Any] | None) -> Dict[str, Any]:
        if not isinstance(cfg, dict):
            return {}
        keys = [
            "model",
            "web_search",
            "use_search",
            "search_context_size",
            "reasoning_effort",
            "max_output_tokens",
            "user_location",
            "web_search_force",
        ]
        return {k: cfg.get(k) for k in keys if k in cfg}

    def _trim(s: Any, n: int) -> Any:
        if isinstance(s, str) and len(s) > n:
            return s[:n] + "…"
        return s

    # Estruturar contexto enxuto para LLM
    runs_ctx: List[Dict[str, Any]] = []
    for r in runs:
        rid = r.id
        ev = ev_map.get(rid) or {}
        parsed = ev.get("parsed") or {}
        meta = parsed.get("meta") or {}
        text = parsed.get("text") or ""
        links = parsed.get("links") or []
        engine_cfg = _subset_cfg(r.engine_config or {})
        if rid in opts_map and isinstance(opts_map[rid], dict):
            engine_cfg.update(_subset_cfg(opts_map[rid]))
        runs_ctx.append({
            "id": rid,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "zcrs": float(r.zcrs or 0),
            "cost_usd": float(r.cost_usd or 0),
            "tokens_total": int(r.tokens_total or 0),
            "engine": r.engine,
            "model": (r.model_name or meta.get("model") or meta.get("engine") or r.engine),
            "prompt": _trim(r.prompt_text or "", 3000),
            "response": _trim(text or "", 6000),
            "links": links,
            "amr_flag": bool(r.amr_flag) if r.amr_flag is not None else None,
            "dcr_flag": bool(r.dcr_flag) if r.dcr_flag is not None else None,
            "project_id": r.project_id,
            "engine_config": engine_cfg,
        })

    cits_ctx: List[Dict[str, Any]] = [
        {"run_id": rid, "domain": dom or "", "url": url or ""} for (rid, dom, url) in citations
    ]

    # Domínios oficiais do projeto (para evitar classificar como concorrente)
    project_domains: List[str] = []
    try:
        proj_id = None
        for rc in runs_ctx:
            if rc.get("project_id"):
                proj_id = rc["project_id"]
                break
        if proj_id:
            for d in db.query(Domain).filter(Domain.project_id == proj_id).all():
                if d.domain:
                    project_domains.append(d.domain.lower())
    except Exception:
        project_domains = []

    # Prompt de sistema para orientar estilo e seções
    system = (
        "Você é um analista sênior de SEO para Zero‑Click/AI Overviews. "
        "Escreva um insight executivo e prático, sem perguntas. Em português. "
        "Respeite a estrutura de saída JSON pedida."
    )
    user_prompt = {
        "task": "Gerar insights agregados sobre Zero‑Click para um subprojeto",
        "requirements": [
            "Resumo executivo (3-5 bullets) com números do período (ex.: ZCRS médio, total de runs, total de citações)",
            "Principais recomendações priorizadas (impacto x esforço) — cada item deve citar explicitamente um dado que o justifique (ex.: domínios, contagens, variações)",
            "Ações rápidas (quick wins) específicas para os achados",
            "Tópicos recorrentes e lacunas (com base nas respostas/citações)",
            "Palavras‑chave sugeridas (lista)",
            "Esboço de nuvem de palavras (wordcloud: {token, weight})",
        ],
        "data": {
            "runs": runs_ctx,
            "citations": cits_ctx,
            "project_domains": project_domains,
        },
        "output_schema": {
            "summary": ["string"],
            "recommendations": [{"title": "string", "impact": "low|medium|high", "effort": "low|medium|high"}],
            "quick_wins": ["string"],
            "topics": ["string"],
            "keywords": ["string"],
            "wordcloud": [{"token": "string", "weight": "number"}]
        }
    }

    # Fallback caso não haja chave/SDK: retorna um esqueleto com heurísticas leves
    try:
        from openai import OpenAI  # type: ignore
        has_key = bool(os.getenv("OPENAI_API_KEY"))
    except Exception:  # pragma: no cover
        OpenAI = None  # type: ignore
        has_key = False

    if OpenAI is None or not has_key:
        # Heurística simples: top domínios e palavras básicas a partir de URLs
        from collections import Counter
        doms = [d or "" for (_rid, d, _u) in citations]
        top = Counter(doms).most_common(8)
        wc = [{"token": k[:24], "weight": int(v)} for k, v in top if k]
        return {
            "summary": [
                "Resumo indisponível (LLM não configurado).",
                f"Runs consideradas: {len(runs_ctx)}; Citações: {len(cits_ctx)}.",
            ],
            "recommendations": [],
            "quick_wins": ["Configure a chave OPENAI_API_KEY para insights completos."],
            "topics": [],
            "keywords": [],
            "wordcloud": wc,
        }

    # Chamada ao LLM (Responses API) com um formato enxuto
    try:  # pragma: no cover - integrações externas
        import json
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # type: ignore
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "array", "items": {"type": "string"}},
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "title": {"type": "string"},
                            "impact": {"type": "string"},
                            "effort": {"type": "string"}
                        },
                        "required": ["title"],
                    }
                },
                "quick_wins": {"type": "array", "items": {"type": "string"}},
                "topics": {"type": "array", "items": {"type": "string"}},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "wordcloud": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "token": {"type": "string"},
                            "weight": {"type": "number"}
                        },
                        "required": ["token", "weight"]
                    }
                }
            },
            "required": ["summary", "recommendations", "quick_wins", "topics", "keywords", "wordcloud"]
        }
        instructions = (
            system
            + "\n\nContexto adicional e regras importantes:" 
            + "\n- Trate os domínios do cliente como NÃO-concorrentes: " + ", ".join(project_domains or ["(desconhecido)"]) 
            + " (incluindo subdomínios). Nunca liste esses domínios como concorrentes ou oportunidades." 
            + "\n- Evite respostas genéricas: cada recomendação deve referenciar dados (ex.: contagens de citações, engines, variações de ZCRS, tokens, custos)." 
            + "\n- Se perceber ausência do domínio do cliente nas citações, ressalte lacunas específicas e onde o concorrente aparece mais." 
            + "\n\nIMPORTANTE: Responda apenas com JSON válido (sem markdown e sem ```), obedecendo ao schema a seguir. "
            + json.dumps(schema, ensure_ascii=False)
        )
        resp = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5"),
            instructions=instructions,
            input=(
                "Analise os dados a seguir e gere APENAS o JSON final.\nDADOS:\n"
                + json.dumps(user_prompt, ensure_ascii=False)
            ),
            max_output_tokens=1024,
            reasoning={"effort": "low"},
        )
        text = getattr(resp, "output_text", None) or ""
        if not text:
            try:
                d = resp.model_dump()  # type: ignore[attr-defined]
                out = d.get("output") or []
                parts: List[str] = []
                for it in out:
                    if isinstance(it, dict) and it.get("type") == "message":
                        for c in (it.get("content") or []):
                            t = c.get("text") or c.get("content")
                            if isinstance(t, str):
                                parts.append(t)
                if parts:
                    text = "\n".join(parts)
            except Exception:
                text = ""

        # Parsing robusto com saneamento
        import re as _re
        def _try_parse(txt: str):
            return json.loads(txt)
        def _sanitize(txt: str) -> str:
            s = (txt or "").strip()
            if s.startswith("```"):
                s = s[s.find("\n") + 1 :] if "\n" in s else s.replace("```", "")
                s = s.replace("```", "")
            if '{' in s and '}' in s:
                start = s.find('{'); end = s.rfind('}')
                if end > start:
                    s = s[start:end+1]
            s = s.replace('“', '"').replace('”', '"').replace('’', '"').replace("‘", '"')
            s = s.replace('NaN', '0').replace('Infinity', '0').replace('-Infinity', '0')
            s = _re.sub(r",\s*([}\]])", r"\1", s)
            s = _re.sub(r"^\s*//.*$", "", s, flags=_re.MULTILINE)
            return s
        def _parse_markdown(txt: str) -> dict:
            s = (txt or "").replace('\r', '')
            lines = s.split('\n')
            current = None
            buckets: dict[str, list[str]] = {"summary": [], "recommendations": [], "quick_wins": [], "topics": [], "keywords": [], "wordcloud": []}
            def _norm(h: str) -> str:
                h = h.lower().strip()
                if 'resumo' in h: return 'summary'
                if 'recomenda' in h: return 'recommendations'
                if 'quick' in h or 'ações rápidas' in h: return 'quick_wins'
                if 'tópico' in h or 'lacuna' in h: return 'topics'
                if 'palavras' in h: return 'keywords'
                if 'wordcloud' in h or 'nuvem' in h: return 'wordcloud'
                return ''
            for ln in lines:
                if ln.lstrip().startswith('#'):
                    header = ln.lstrip('#').strip(); current = _norm(header); continue
                if current:
                    stripped = ln.strip()
                    if stripped.startswith(('-', '*')) or _re.match(r"^\d+\.\s", stripped):
                        item = stripped.lstrip('-* ').strip(); buckets[current].append(item)
            from math import isnan
            out: dict[str, Any] = {
                "summary": buckets["summary"],
                "recommendations": [],
                "quick_wins": buckets["quick_wins"],
                "topics": buckets["topics"],
                "keywords": buckets["keywords"],
                "wordcloud": []
            }
            for itm in buckets['recommendations']:
                import re as _re2
                impact = None; effort = None
                m1 = _re2.search(r"impacto\s*[:=-]\s*([a-zA-Z]+)", itm, flags=_re2.IGNORECASE)
                m2 = _re2.search(r"esforç[o|o]\s*[:=-]\s*([a-zA-Z]+)", itm, flags=_re2.IGNORECASE)
                if m1: impact = m1.group(1).lower()
                if m2: effort = m2.group(1).lower()
                title = _re2.sub(r"\(.*?\)|\[.*?\]|impacto.*$|esforço.*$", "", itm, flags=_re2.IGNORECASE).strip(" -–—;:")
                out['recommendations'].append({"title": title or itm, **({"impact": impact} if impact else {}), **({"effort": effort} if effort else {})})
            for itm in buckets['wordcloud']:
                import re as _re3
                m = _re3.search(r"^(.+?)[\s:（\(]+([0-9]+(?:\.[0-9]+)?)\)?$", itm.strip())
                if m:
                    token = m.group(1).strip().strip('-:').strip()
                    try:
                        weight = float(m.group(2))
                    except Exception:
                        weight = 1.0
                else:
                    token, weight = itm.strip(), 1.0
                if token:
                    out['wordcloud'].append({"token": token[:48], "weight": weight})
            return out

        data: dict = {}
        try:
            data = _try_parse(text)
        except Exception:
            s1 = _sanitize(text)
            try:
                data = _try_parse(s1)
            except Exception:
                s2 = _re.sub(r",\s*(\n|\r)+\s*([}\]])", r"\2", s1)
                try:
                    data = _try_parse(s2)
                except Exception:
                    data = _parse_markdown(text)
        payload = {
            "summary": list(data.get("summary", []))[:10],
            "recommendations": data.get("recommendations", [])[:10],
            "quick_wins": list(data.get("quick_wins", []))[:10],
            "topics": list(data.get("topics", []))[:20],
            "keywords": list(data.get("keywords", []))[:30],
            "wordcloud": data.get("wordcloud", [])[:40],
        }
        return payload
    except Exception as e:  # pragma: no cover
        return {
            "summary": [
                "Falha ao gerar via LLM.",
                str(e)[:200],
            ],
            "recommendations": [],
            "quick_wins": [],
            "topics": [],
            "keywords": [],
            "wordcloud": [],
        }

