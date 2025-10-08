"""Serviço para gerar insights semânticos usando Gemini (JSON mode)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple, Set

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmBlockThreshold, HarmCategory
    GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    GENAI_AVAILABLE = False

# Validação opcional
try:
    import jsonschema  # pip install jsonschema
    JSONSCHEMA_AVAILABLE = True
except Exception:
    JSONSCHEMA_AVAILABLE = False

from app.core.config import settings
from app.services.normalization import normalize_domain, normalize_url_for_dedupe


# -------------------------
# JSON Schema (tolerante)
# -------------------------
JSON_OUTPUT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": True,
    "required": ["entities", "relationships", "keywords", "perception", "summary", "competitors"],
    "properties": {
        "meta": {"type": "object"},
        "entities": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "required": ["name", "category", "roles", "confidence"],
                "additionalProperties": True,
                "properties": {
                    "name": {"type": "string"},
                    "category": {"enum": ["brand", "product", "feature", "competitor", "other"]},
                    "roles": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "citations": {
                        "oneOf": [
                            {"type": "array", "items": {"type": "string"}},
                            {"type": "array", "items": {"type": "object"}}
                        ]
                    },
                    "description": {"type": ["string", "null"]}
                }
            }
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target", "type"],
                "additionalProperties": True,
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "weight": {"type": "number", "minimum": 0, "maximum": 1},
                    "explanation": {"type": ["string", "null"]}
                }
            }
        },
        "keywords": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "required": ["token", "weight"],
                "additionalProperties": True,
                "properties": {
                    "token": {"type": "string"},
                    "weight": {"type": "number", "minimum": 0, "maximum": 1},
                    "brands": {"type": "array", "items": {"type": "string"}},
                    "products": {"type": "array", "items": {"type": "string"}},
                    "competitors": {"type": "array", "items": {"type": "string"}},
                    "context": {"type": ["string", "null"]}
                }
            }
        },
        "perception": {
            "type": "object",
            "additionalProperties": True,
            "required": ["primary_category", "confidence"],
            "properties": {
                "primary_category": {"enum": ["inovacao", "tradicao", "custo", "atendimento"]},
                "secondary_categories": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "rationale": {"type": ["string", "null"]},
                "scores": {"type": "object"}
            }
        },
        "summary": {
            "type": "object",
            "additionalProperties": True,
            "required": ["headline", "bullets"],
            "properties": {
                "headline": {"type": "string"},
                "bullets": {"type": "array", "items": {"type": "string"}},
                "opportunities": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "object", "properties": {"text": {"type": "string"}}}
                        ]
                    }
                },
                "risks": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "object", "properties": {"text": {"type": "string"}}}
                        ]
                    }
                }
            }
        },
        "competitors": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "mentions": {"type": ["integer", "null"], "minimum": 0},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "presence": {"type": "array", "items": {"type": "string"}},
                    "urls": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "seo_metrics": {"type": "object"},
        "evidence": {"type": "object"},
        "citations": {"type": "array"}
    }
}

# Limites e chaves de ordenação
MAX_ENTITIES = 10
MAX_KEYWORDS = 10
ENTITY_SORT_KEY = lambda e: float(e.get("confidence") or 0.0)
KEYWORD_SORT_KEY = lambda k: float(k.get("weight") or 0.0)


FINANCIAL_BASE_DOMAINS: Set[str] = {
    "bb.com.br",
    "bancodobrasil.com.br",
    "itau.com.br",
    "itauuniclass.com.br",
    "bradesco.com.br",
    "caixa.gov.br",
    "santander.com.br",
    "btgpactual.com.br",
    "safra.com.br",
    "sicredi.com.br",
    "sicoob.com.br",
    "inter.com.br",
    "inter.co",
    "nubank.com.br",
    "nubank.com",
    "pagbank.com.br",
    "pagseguro.uol.com.br",
    "blog.pagseguro.uol.com.br",
    "mercadopago.com.br",
    "c6bank.com.br",
    "banrisul.com.br",
    "original.com.br",
    "digio.com.br",
    "willbank.com.br",
    "next.me",
    "agibank.com.br",
    "neon.com.br",
    "modalmais.com.br",
}

FINANCIAL_KEYWORDS: Tuple[str, ...] = (
    "banco",
    "bank",
    "finance",
    "finança",
    "financas",
    "fintech",
    "crédito",
    "credito",
    "cartão",
    "cartao",
    "credi",
    "pagbank",
    "pagseguro",
    "nubank",
    "santander",
    "itau",
    "bradesco",
    "caixa",
    "sicredi",
    "sicoob",
    "inter",
    "btg",
    "safra",
    "banrisul",
    "c6",
    "agibank",
    "modalmais",
    "neon",
    "original",
    "mercado pago",
)


FINANCIAL_DOMAIN_LABELS: Dict[str, str] = {
    "bb.com.br": "Banco do Brasil",
    "bancodobrasil.com.br": "Banco do Brasil",
    "itau.com.br": "Itaú",
    "itauuniclass.com.br": "Itaú Uniclass",
    "bradesco.com.br": "Bradesco",
    "caixa.gov.br": "Caixa Econômica Federal",
    "santander.com.br": "Santander",
    "btgpactual.com.br": "BTG Pactual",
    "safra.com.br": "Banco Safra",
    "sicredi.com.br": "Sicredi",
    "sicoob.com.br": "Sicoob",
    "inter.com.br": "Banco Inter",
    "inter.co": "Banco Inter",
    "nubank.com.br": "Nubank",
    "nubank.com": "Nubank",
    "pagbank.com.br": "PagBank",
    "pagseguro.uol.com.br": "PagBank",
    "blog.pagseguro.uol.com.br": "PagBank",
    "mercadopago.com.br": "Mercado Pago",
    "c6bank.com.br": "C6 Bank",
    "banrisul.com.br": "Banrisul",
    "original.com.br": "Banco Original",
    "digio.com.br": "Digio",
    "willbank.com.br": "Will Bank",
    "next.me": "Next",
    "agibank.com.br": "Agibank",
    "neon.com.br": "Banco Neon",
    "modalmais.com.br": "Banco Modalmais",
    "empresta.com.br": "Empresta",
    "serasa.com.br": "Serasa",
}


def _beautify_competitor_label(label: str) -> str:
    label = (label or "").strip()
    if not label:
        return label

    clean = re.sub(r"[-_]+", " ", label).strip()
    lower = clean.lower()

    if lower.startswith("www "):
        clean = clean[4:]
        lower = clean.lower()

    if lower.startswith("banco "):
        rest = clean[6:]
        return f"Banco {rest.strip().title()}" if rest else "Banco"

    if lower.startswith("banco"):
        rest = clean[5:]
        rest = rest.strip()
        if rest:
            return f"Banco {rest.title()}"

    if lower.endswith(" bank"):
        return clean.title()

    return clean.title()


def _format_competitor_name(raw_name: str, urls: List[str]) -> Optional[str]:
    candidate = (raw_name or "").strip()
    urls = urls or []

    domains: List[str] = []
    if candidate:
        domain = normalize_domain(candidate)
        if domain:
            domains.append(domain)

    for url in urls:
        domain = normalize_domain(url)
        if domain:
            domains.append(domain)

    for domain in domains:
        if domain in FINANCIAL_DOMAIN_LABELS:
            return FINANCIAL_DOMAIN_LABELS[domain]

    for domain in domains:
        if domain in FINANCIAL_BASE_DOMAINS:
            base = domain.split(".")[0]
            return _beautify_competitor_label(base)

    if candidate:
        domain = normalize_domain(candidate)
        if domain and domain != candidate.lower():
            return _beautify_competitor_label(domain.split(".")[0])

    if candidate:
        return _beautify_competitor_label(candidate)

    return None


class GeminiSemanticService:
    """Wrapper simples para chamar Gemini e extrair insights estruturados."""

    def __init__(self, model_name: str = "gemini-2.5-pro", api_key: Optional[str] = None) -> None:
        if not settings.semantic_insights_enabled:
            raise RuntimeError("semantic insights disabled by configuration")
        if not GENAI_AVAILABLE:
            raise ImportError("google-generativeai não está instalado")

        self.api_key = api_key or settings.gemini_api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("API key do Gemini não configurada. Defina GEMINI_API_KEY ou GOOGLE_API_KEY.")

        self.model_name = model_name
        genai.configure(api_key=self.api_key)

        generation_config = {
            "temperature": 0.15,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 9500,
            # Força o modo JSON
            "response_mime_type": "application/json",
        }

        # Desabilitamos response_schema porque o Gemini SDK tem problemas com schemas
        # que contêm type: ["string", "null"], causando erro "unhashable type: 'list'".
        # Nossa normalização manual já é robusta o suficiente.
        # try:
        #     generation_config["response_schema"] = JSON_OUTPUT_SCHEMA
        # except Exception:
        #     pass

        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        
        # Cache para hints automáticos
        self._last_normalized_citations: List[Dict[str, Any]] = []

    # -------------------------
    # Utils internos
    # -------------------------

    @staticmethod
    def _get_empty_structure() -> Dict[str, Any]:
        """Retorna estrutura vazia válida para quando Gemini falha."""
        return {
            "meta": {},
            "entities": [],
            "relationships": [],
            "keywords": [],
            "perception": {},
            "summary": {},
            "competitors": [],
            "wordcloud": [],
            "seo_metrics": {},
            "evidence": {},
            "citations": [],
        }

    @staticmethod
    def _prepare_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prepared: List[Dict[str, Any]] = []
        seen: set[str] = set()
        if not citations:
            return prepared

        for cite in citations[:100]:  # manter prompt enxuto
            if not isinstance(cite, dict):
                continue

            raw_url = (cite.get("url") or "").strip()
            domain_raw = cite.get("domain")
            domain_raw = domain_raw.strip().lower() if isinstance(domain_raw, str) else ""

            normalized_url = normalize_url_for_dedupe(raw_url) if raw_url else ""
            domain_norm = normalize_domain(raw_url or domain_raw)

            key = normalized_url or domain_norm or domain_raw
            if not key:
                anchor = cite.get("anchor")
                key = (anchor or raw_url or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)

            position_raw = cite.get("position")
            if isinstance(position_raw, (int, float)):
                position_val = int(position_raw)
            elif isinstance(position_raw, str) and position_raw.strip().isdigit():
                position_val = int(position_raw.strip())
            else:
                position_val = len(prepared) + 1

            prepared.append(
                {
                    "url": raw_url or None,
                    "normalized_url": normalized_url or None,
                    "domain": domain_norm or (domain_raw or None),
                    "position": position_val,
                    "is_ours": bool(cite.get("is_ours")),
                    "anchor": cite.get("anchor") or None,
                }
            )

        return prepared

    @staticmethod
    def _format_citations(prepared: List[Dict[str, Any]]) -> str:
        if not prepared:
            return "Nenhuma citação disponível."

        total = len(prepared)
        ours = sum(1 for cite in prepared if cite.get("is_ours"))
        competitors = total - ours
        lines = [f"Total: {total} (nossas: {ours}; concorrentes: {competitors})"]

        for idx, cite in enumerate(prepared[:12], start=1):
            try:
                pos_int = int(cite.get("position") or idx)
            except (TypeError, ValueError):
                pos_int = idx
            domain_display = cite.get("domain")
            if not domain_display:
                domain_display = normalize_domain(cite.get("normalized_url") or cite.get("url") or "")
            if not domain_display:
                domain_display = cite.get("normalized_url") or cite.get("url") or "desconhecido"
            label = "nossa" if cite.get("is_ours") else "concorrente"
            anchor = cite.get("anchor")
            url_display = cite.get("url") or cite.get("normalized_url")

            extras: List[str] = []
            if anchor:
                extras.append(anchor)
            if url_display:
                extras.append(url_display)
            extra_text = f" — {'; '.join(extras)}" if extras else ""
            lines.append(f"{pos_int:02d}. {domain_display} ({label}){extra_text}")

        return "\n".join(lines)

    @staticmethod
    def _safe_json_loads(raw: str) -> Dict[str, Any]:
        """Extrai JSON de resposta do Gemini com limpeza agressiva (fallback)."""
        import re

        cleaned = (raw or "").strip()
        if not cleaned:
            return GeminiSemanticService._get_empty_structure()

        # Remover markdown code blocks, se houver
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        # Tenta parse direto
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Heurística: pega do primeiro '{' ao último '}'
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        print("[SEMANTIC] Aviso: JSON inválido; retornando estrutura vazia.")
        return GeminiSemanticService._get_empty_structure()

    # ---------- NOVO: inferência de brand/domain hints ----------
    @staticmethod
    def _infer_brand_domain_hints(project_name: Optional[str], citations: List[Dict[str, Any]]) -> Dict[str, str]:
        brand_hint = f"Projeto/Marca principal: {project_name}." if project_name else ""
        domain_hint = ""

        # preferir domínio first-party mais frequente nas citações
        ours = [c for c in citations if c.get("is_ours") and c.get("domain")]
        domain = None
        if ours:
            # mais frequente
            from collections import Counter
            domain = Counter([c["domain"] for c in ours]).most_common(1)[0][0]
        else:
            # fallback: primeiro domínio válido
            for c in citations:
                if c.get("domain"):
                    domain = c["domain"]
                    break

        if domain and project_name:
            domain_hint = f"Domínio principal: {domain} ({project_name})."
        elif domain:
            domain_hint = f"Domínio principal: {domain}."
        return {"brand_hint": brand_hint, "domain_hint": domain_hint}

    # -------------------------
    # Normalização + limites
    # -------------------------
    @staticmethod
    def _round01(x: Any) -> float:
        try:
            v = float(x)
        except (TypeError, ValueError):
            return 0.0
        v = 0.0 if v < 0 else (1.0 if v > 1 else v)
        return float(f"{v:.2f}")

    @staticmethod
    def _normalize_payload(
        data: Dict[str, Any],
        *,
        response_text: Optional[str] = None,
        project_name: Optional[str] = None,
        normalized_citations: Optional[List[Dict[str, Any]]] = None,
        meta_defaults: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        def as_list(value: Any) -> List[Any]:
            if isinstance(value, list):
                return value
            if value is None:
                return []
            return [value]

        def as_dict(value: Any) -> Dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def clean_str_list(values: Any) -> List[str]:
            cleaned: List[str] = []
            for item in as_list(values):
                if item is None:
                    continue
                if isinstance(item, str):
                    stripped = item.strip()
                    if stripped:
                        cleaned.append(stripped)
                else:
                    cleaned.append(item)
            return cleaned

        def to_int(value: Any) -> Optional[int]:
            try:
                if value is None:
                    return None
                return int(value)
            except (TypeError, ValueError):
                return None

        payload: Dict[str, Any] = {
            "meta": as_dict(data.get("meta")),
            "entities": [],
            "relationships": [],
            "keywords": [],
            "perception": {},
            "summary": {},
            "competitors": [],
            "wordcloud": [],
            "seo_metrics": as_dict(data.get("seo_metrics")),
            "evidence": as_dict(data.get("evidence")),
            "citations": normalized_citations or [],
        }

        # ENTITIES
        entities: List[Dict[str, Any]] = []
        for item in as_list(data.get("entities")):
            if not isinstance(item, dict):
                continue
            canonical = item.get("canonical_name") or item.get("name")
            if not canonical:
                continue
            entry = {
                "name": canonical,
                "canonical_name": canonical,
                "aliases": clean_str_list(item.get("aliases")),
                "category": (item.get("category") or item.get("type") or "other").strip().lower(),
                "roles": clean_str_list(item.get("roles")),
                "confidence": GeminiSemanticService._round01(item.get("confidence", 0.0)),
                "citations": as_list(item.get("citations")),
                "description": item.get("description"),
            }
            if project_name and canonical.strip().lower() == project_name.strip().lower():
                if "brand" not in [r.lower() for r in entry["roles"]]:
                    entry.setdefault("roles", []).append("brand")
            entities.append(entry)

        # Ordena e limita
        entities.sort(key=ENTITY_SORT_KEY, reverse=True)
        payload["entities"] = entities[:MAX_ENTITIES]

        # RELATIONSHIPS
        rels = []
        for item in as_list(data.get("relationships") or data.get("relations")):
            if not isinstance(item, dict):
                continue
            src = item.get("source") or item.get("from")
            tgt = item.get("target") or item.get("to")
            if not (src and tgt):
                continue
            weight = GeminiSemanticService._round01(item.get("weight", item.get("score", 0.0)))
            rels.append(
                {
                    "source": src,
                    "target": tgt,
                    "type": item.get("type"),
                    "weight": weight,
                    "explanation": item.get("explanation") or item.get("description"),
                }
            )
        payload["relationships"] = rels

        # KEYWORDS
        kws: List[Dict[str, Any]] = []
        for item in as_list(data.get("keywords")):
            if isinstance(item, str):
                token = item.strip()
                if not token:
                    continue
                kw = {
                    "token": token.lower(),
                    "weight": 0.0,
                    "brands": [],
                    "products": [],
                    "competitors": [],
                    "context": None,
                }
                kws.append(kw)
                continue

            if not isinstance(item, dict):
                continue

            token = (
                item.get("token")
                or item.get("keyword")
                or item.get("text")
                or item.get("term")
            )
            if not token:
                continue
            kw = {
                "token": str(token).strip().lower(),
                "weight": GeminiSemanticService._round01(item.get("weight", item.get("score", item.get("relevance", 0.0)))),
                "brands": clean_str_list(item.get("brands")),
                "products": clean_str_list(item.get("products")),
                "competitors": clean_str_list(item.get("competitors")),
                "context": item.get("context"),
            }
            kws.append(kw)
        kws.sort(key=KEYWORD_SORT_KEY, reverse=True)
        payload["keywords"] = kws[:MAX_KEYWORDS]

        # PERCEPTION
        perception = as_dict(data.get("perception"))
        if perception:
            # Normaliza enum
            prim = (perception.get("primary_category") or "").strip().lower()
            if prim not in {"inovacao", "tradicao", "custo", "atendimento"}:
                prim = ""
            perception["primary_category"] = prim
            perception["secondary_categories"] = clean_str_list(perception.get("secondary_categories"))
            # Clamp
            perception["confidence"] = GeminiSemanticService._round01(perception.get("confidence", 0.0))
            scores = perception.get("scores")
            if scores is not None and not isinstance(scores, dict):
                perception["scores"] = {}
        payload["perception"] = perception

        # SUMMARY
        summary = as_dict(data.get("summary"))
        if summary:
            bullet_sources: List[str] = []
            summary["bullets"] = [
                str(item).strip()
                for item in as_list(summary.get("bullets"))
                if str(item).strip()
            ]
            # Coletar alternativas para pontos-chave
            key_candidates: List[Any] = [
                summary.get("key_points"),
                summary.get("key_findings"),
                summary.get("highlights"),
                summary.get("insights"),
            ]
            for candidate in key_candidates:
                for item in as_list(candidate):
                    text_val = str(item).strip()
                    if text_val:
                        bullet_sources.append(text_val)
            if not summary["bullets"] and bullet_sources:
                summary["bullets"] = bullet_sources
            # opportunities
            opportunities = []
            for opp in as_list(summary.get("opportunities")):
                if isinstance(opp, dict):
                    opp = {k: v for k, v in opp.items() if v not in (None, "")}
                    if opp.get("text"):
                        opportunities.append(opp)
                else:
                    text_val = str(opp).strip()
                    if text_val:
                        opportunities.append({"text": text_val})
            if opportunities:
                summary["opportunities"] = opportunities
            # risks
            risks_clean = []
            for risk in as_list(summary.get("risks")):
                if isinstance(risk, dict):
                    risk = {k: v for k, v in risk.items() if v not in (None, "")}
                    if risk.get("text"):
                        risks_clean.append(risk)
                else:
                    text_val = str(risk).strip()
                    if text_val:
                        risks_clean.append({"text": text_val})
            if risks_clean:
                summary["risks"] = risks_clean
            if not summary.get("headline"):
                headline_source = summary.get("main_topic") or bullet_sources
                if isinstance(headline_source, list) and headline_source:
                    summary["headline"] = headline_source[0]
                elif isinstance(headline_source, str) and headline_source.strip():
                    summary["headline"] = headline_source.strip()
        payload["summary"] = summary

        # COMPETITORS
        comps: List[Dict[str, Any]] = []
        for comp in as_list(data.get("competitors")):
            if not isinstance(comp, dict):
                continue
            name = comp.get("name")
            if not name:
                continue
            entry = {
                "name": name,
                "category": comp.get("category"),
                "mentions": to_int(comp.get("mentions")),
                "keywords": clean_str_list(comp.get("keywords")),
                "presence": clean_str_list(comp.get("presence")),
                "urls": clean_str_list(comp.get("urls")),
            }
            comps.append(entry)
        filtered_comps: List[Dict[str, Any]] = []
        seen_names: Set[str] = set()
        for comp in comps:
            name = (comp.get("name") or "").strip()
            if not name:
                continue

            normalized_name = name.lower()
            is_financial = any(keyword in normalized_name for keyword in FINANCIAL_KEYWORDS)

            if not is_financial:
                urls = comp.get("urls") or []
                for raw_url in urls:
                    domain = normalize_domain(raw_url)
                    if domain in FINANCIAL_BASE_DOMAINS:
                        is_financial = True
                        break

            if not is_financial:
                continue

            display_name = _format_competitor_name(name, comp.get("urls") or [])
            if not display_name:
                continue

            if display_name in seen_names:
                continue

            seen_names.add(display_name)
            clean_comp = comp.copy()
            clean_comp["name"] = display_name
            filtered_comps.append(clean_comp)

        payload["competitors"] = filtered_comps

        # WORDCLOUD derivado
        payload["wordcloud"] = [
            {"token": kw["token"], "weight": kw["weight"], "brands": clean_str_list(kw.get("brands"))}
            for kw in payload["keywords"]
            if kw.get("token")
        ]

        # Defaults para meta
        defaults = {k: v for k, v in (meta_defaults or {}).items() if v not in (None, "", [])}
        if defaults:
            if not payload["meta"]:
                payload["meta"] = defaults
            else:
                for key, value in defaults.items():
                    payload["meta"].setdefault(key, value)

        return payload

    # -------------------------
    # PROMPT Builder (curto)
    # -------------------------
    def build_prompt(
        self,
        *,
        question: str,
        response_text: str,
        citations_text: str,
        project_name: Optional[str] = None,
        meta_context: Optional[str] = None,
    ) -> str:
        # Hints automáticos por citações
        _hints = self._infer_brand_domain_hints(project_name, self._last_normalized_citations or [])
        brand_hint = _hints.get("brand_hint", "")
        domain_hint = _hints.get("domain_hint", "")

        rules = (
            "- Retorne JSON puro (sem markdown).\n"
            "- Use snake_case nas chaves.\n"
            "- Máx. 10 entidades e 10 keywords, ordenadas por confiança/peso desc.\n"
            "- confidence/weight ∈ [0,1], 2 casas decimais.\n"
            "- Não alucine: use apenas o que aparece na resposta ou nas citações.\n"
            "- Categorias: brand|product|feature|competitor|other.\n"
            "- perception.primary_category: inovacao|tradicao|custo|atendimento.\n"
            "- Se não houver dados, use arrays vazios ou valores neutros.\n"
            "- Concorrentes tem que ser relacionado ao setor bancario, apenas empresas relacionadas a financas. Empresas que nao sao concorrentes: app store e youtube."
        )

        return f"""
Você é um analista de SEO/IA. Extraia **apenas JSON** restrito ao esquema conhecido.

{brand_hint}
{domain_hint}
{(meta_context or '').strip()}

### Pergunta
{question}

### Resposta (texto plano)
{response_text}

### Citações (resumo)
{citations_text}

### Regras
{rules}

### Estrutura esperada (top-level, ordem sugerida)
{{
  "meta": {{}},
  "entities": [],
  "relationships": [],
  "keywords": [],
  "perception": {{}},
  "summary": {{}},
  "competitors": [],
  "seo_metrics": {{}},
  "evidence": {{}}
}}
""".strip()

    # -------------------------
    # Execução principal
    # -------------------------
    def analyze(
        self,
        *,
        question: str,
        response_text: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        project_name: Optional[str] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        citations = citations or []
        normalized_citations = self._prepare_citations(citations)
        # guarda para hints automáticos dentro do prompt
        self._last_normalized_citations = normalized_citations[:]  # type: ignore[attr-defined]
        citations_text = self._format_citations(normalized_citations)

        meta_defaults = {
            "query": question,
            "locale": "pt-BR",
            "country": "BR",
            "device": "unknown",
            "source": "google",
        }

        # Tentar com prompt normal, depois simplificado se bloquear
        response = None
        for attempt in range(max_retries):
            use_simplified = attempt > 0
            prompt = self.build_prompt(
                question=question,
                response_text=response_text,
                citations_text=citations_text,
                project_name=project_name,
            )
            try:
                print(f"[SEMANTIC] Tentativa {attempt + 1}/{max_retries}: Gemini (JSON mode)...")
                response = self.model.generate_content(prompt)
                print("[SEMANTIC] Gemini respondeu.")
            except Exception as e:
                print(f"[SEMANTIC] Erro na chamada Gemini: {e}")
                if attempt < max_retries - 1:
                    continue
                return self._get_empty_structure()

            # Se bloqueou por safety/other, tenta novamente simplificado
            if getattr(response, "candidates", None):
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", None)
                if finish_reason in [2, 3, 4]:  # SAFETY/RECITATION/OTHER (nomes variam por SDK)
                    print(f"[SEMANTIC] Bloqueado (finish_reason={finish_reason}); retry simples.")
                    if attempt < max_retries - 1:
                        continue
                    return self._get_empty_structure()
            break

        # Obter texto cru (JSON esperado)
        raw_text: Optional[str] = None
        try:
            raw_text = response.text  # type: ignore[assignment]
        except Exception:
            # fallback: juntar parts
            if getattr(response, "candidates", None):
                parts: List[str] = []
                for cand in response.candidates:
                    content = getattr(cand, "content", None)
                    if content:
                        for part in getattr(content, "parts", []) or []:
                            t = getattr(part, "text", None)
                            if t:
                                parts.append(t)
                raw_text = "\n".join(parts) if parts else None

        if not raw_text:
            print("[SEMANTIC] Resposta vazia; retornando estrutura vazia.")
            return self._get_empty_structure()

        print(f"[SEMANTIC] Raw length: {len(raw_text)}")
        data = self._safe_json_loads(raw_text)

        # Validação por schema (opcional)
        if JSONSCHEMA_AVAILABLE:
            try:
                jsonschema.validate(instance=data, schema=JSON_OUTPUT_SCHEMA)
            except Exception as e:
                print(f"[SEMANTIC] JSON não validou no schema: {e}")
                # Segue com normalização mesmo assim, para não perder dados

        normalized = self._normalize_payload(
            data,
            response_text=response_text,
            project_name=project_name,
            normalized_citations=normalized_citations,
            meta_defaults=meta_defaults,
        )

        usage = getattr(response, "usage_metadata", None)
        if usage:
            normalized["usage"] = {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "candidates_tokens": getattr(usage, "candidates_token_count", None),
                "total_tokens": getattr(usage, "total_token_count", None),
            }

        return normalized