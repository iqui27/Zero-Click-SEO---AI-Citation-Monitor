
from __future__ import annotations

import os
import re
from typing import List, Optional, Dict, Any

from openai import OpenAI

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation


URL_RE = re.compile(r"https?://[\w\-\.\?\,\'\/\+&%\$#_=:\(\)\*]+", re.IGNORECASE)


class OpenAIAdapter:
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        # Keep env override but allow per-request override in fetch()
        # Default to a widely available model for compatibility
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    async def fetch(self, input: FetchInput) -> RawEvidence:
        """Call OpenAI Responses API, optionally with web_search_preview."""
        if not self.client:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}

        cfg: Dict[str, Any] = (input.get("config") or {})

        # Use `instructions` (system prompt) per Responses API best-practice
        system = cfg.get("system") or (
            "Você é um analista objetivo de busca na Web. Não faça perguntas nem peça confirmações. "
            "Responda diretamente, de forma assertiva e organizada. Sempre use web search. "
            "Sempre liste as fontes no final com URLs completas (http) e sem encurtadores."
        )

        # Allow model + token limit override via config
        model = cfg.get("model") or self.model
        # aumentar default para evitar cortes prematuros
        max_output_tokens = int(cfg.get("max_output_tokens") or 2048)

        # Optional web search tool (Responses API)
        # Sinalizadores aceitos em Engine.config_json:
        #   web_search: bool
        #   user_location: {type: "approximate", country: "GB", city: "London", region: "London"}
        #   search_context_size: "low" | "medium" | "high"
        #   web_search_tool_choice: "auto" | {"type": "web_search_preview"}
        #   web_search_force: bool (atalho para tool_choice={type:"web_search_preview"})
        #   web_search_options: dict (compatibilidade antiga; extrai subchaves conhecidas)
        use_web_search = cfg.get("web_search", True)
        web_search_options = cfg.get("web_search_options") or {}
        user_location = cfg.get("user_location") or web_search_options.get("user_location")
        # padrão mais econômico
        search_context_size = (
            cfg.get("search_context_size")
            or web_search_options.get("search_context_size")
            or "low"
        )
        tools: List[Dict[str, Any]] = []
        if use_web_search:
            tool: Dict[str, Any] = {"type": "web_search_preview"}
            if isinstance(user_location, dict) and user_location:
                tool["user_location"] = user_location
            if isinstance(search_context_size, str) and search_context_size:
                tool["search_context_size"] = search_context_size
            tools.append(tool)

        # Apenas Responses API (sem fallback)
        try:
            if not hasattr(self.client, "responses"):
                raise RuntimeError("OpenAI client sem suporte a Responses API")
            kwargs: Dict[str, Any] = {
                "model": model,
                "instructions": system,
                # Conforme documentação: input pode ser string simples
                "input": input["query"],
                "max_output_tokens": max_output_tokens,
            }
            # Reduzir gasto só em raciocínio e garantir resposta
            reasoning_effort = (cfg.get("reasoning_effort") or "low")
            kwargs["reasoning"] = {"effort": reasoning_effort}
            if tools:
                kwargs["tools"] = tools
                # tool_choice configurable
                tool_choice_cfg = cfg.get("web_search_tool_choice")
                if tool_choice_cfg:
                    kwargs["tool_choice"] = tool_choice_cfg
                elif cfg.get("web_search_force"):
                    kwargs["tool_choice"] = {"type": "web_search_preview"}
                else:
                    kwargs["tool_choice"] = "auto"
            resp = self.client.responses.create(**kwargs)  # type: ignore[attr-defined]
            # Extrair de forma robusta o dict completo da resposta
            raw_dict: Dict[str, Any] = {}
            try:
                if hasattr(resp, "model_dump"):
                    raw_dict = resp.model_dump()  # type: ignore[attr-defined]
                elif hasattr(resp, "to_dict"):
                    raw_dict = resp.to_dict()  # type: ignore[attr-defined]
                elif hasattr(resp, "dict"):
                    raw_dict = resp.dict()  # type: ignore[attr-defined]
                else:
                    import json
                    to_json = getattr(resp, "model_dump_json", None) or getattr(resp, "to_json", None)
                    if callable(to_json):
                        raw_dict = json.loads(to_json())
            except Exception:
                raw_dict = {}

            # Alguns SDKs expõem `output` como atributo, garantir preservação
            output_attr = getattr(resp, "output", None)
            if output_attr and not raw_dict.get("output"):
                try:
                    raw_dict["output"] = output_attr  # pode ser list nativo
                except Exception:
                    pass

            # Se não houver mensagem no output, faz um turn de finalização usando previous_response_id
            def _has_message(d: Dict[str, Any]) -> bool:
                try:
                    for item in (d.get("output") or []):
                        if isinstance(item, dict) and item.get("type") == "message":
                            return True
                except Exception:
                    pass
                return False

            final_dict = raw_dict
            previous_dict = None
            if not _has_message(raw_dict):
                try:
                    finalize_text = (
                        "Forneça a resposta final agora em texto corrido (sem perguntas), "
                        "organizada e com 3–5 fontes ao final usando URLs completas (http)."
                    )
                    resp2 = self.client.responses.create(  # type: ignore[attr-defined]
                        model=model,
                        previous_response_id=raw_dict.get("id"),
                        input=finalize_text,
                        max_output_tokens=max_output_tokens,
                    )
                    if hasattr(resp2, "model_dump"):
                        final_dict = resp2.model_dump()  # type: ignore[attr-defined]
                    elif hasattr(resp2, "to_dict"):
                        final_dict = resp2.to_dict()  # type: ignore[attr-defined]
                    previous_dict = raw_dict
                except Exception:
                    # fallback: manter raw_dict mesmo sem message
                    final_dict = raw_dict

            raw_payload: Dict[str, Any] = {
                "response": final_dict,
                "previous_response": previous_dict,
                "output_text": getattr(resp, "output_text", None),
                "model": model,
            }
            return {"raw_url": None, "raw": raw_payload}
        except Exception as e:
            sanitized_request = {
                "model": model,
                "has_tools": bool(tools),
                "with_web_search": bool(use_web_search),
                "web_search_options": web_search_options if isinstance(web_search_options, dict) else None,
                "max_output_tokens": max_output_tokens,
            }
            return {"raw_url": None, "raw": {"error": "openai_request_failed", "message": str(e), "request": sanitized_request}}

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        data: Dict[str, Any] = raw.get("raw") or {}

        # Prefer the SDK-provided output_text; fallback para reconstruir a partir do dict
        content: str = data.get("output_text") or ""
        if not content:
            rd = data.get("response") or {}
            # 1) Tentar extrair de output[].content[] com type=output_text
            try:
                outputs = rd.get("output") or []
                parts: list[str] = []
                for item in outputs:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "message":
                        for c in (item.get("content") or []):
                            if isinstance(c, dict):
                                t = c.get("text") or c.get("content")
                                if isinstance(t, str) and t.strip():
                                    parts.append(t)
                if parts:
                    content = "\n".join(parts).strip()
            except Exception:
                pass
            # 2) Fallback legado para formatos alternativos
            if not content:
                content = self._extract_text_from_response_dict(rd)

        # Extract possible URLs from the text and also append URL citations from annotations if present
        links: List[Dict[str, str]] = []
        for m in URL_RE.findall(content or ""):
            links.append({"url": m})

        # Anotações (citations) no formato Responses API: output[].content[].annotations[] com type=url_citation
        try:
            rd = data.get("response") or {}
            # contabilizar web_search_call
            web_search_calls = 0
            output = rd.get("output") or []
            for item in output:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "web_search_call":
                    web_search_calls += 1
                if item.get("type") == "message":
                    for c in (item.get("content") or []):
                        ann_list = (c or {}).get("annotations") or []
                        for ann in ann_list:
                            if isinstance(ann, dict) and ann.get("type") == "url_citation":
                                url = ann.get("url")
                                title = ann.get("title")
                                if url and all(l.get("url") != url for l in links):
                                    links.append({"url": url, "title": title})
        except Exception:
            pass

        usage: Dict[str, Any] = {}
        response_dict: Dict[str, Any] = data.get("response") or {}
        try:
            # Normalizar usage da Responses API. Alguns modelos retornam dentro de output[...].usage
            u = response_dict.get("usage")
            if not isinstance(u, dict):
                # tentar em output[].usage
                output = response_dict.get("output") or []
                for item in output:
                    if isinstance(item, dict) and isinstance(item.get("usage"), dict):
                        u = item.get("usage")
                        break
            if not isinstance(u, dict):
                u = {}
            usage = {
                "input_tokens": u.get("input_tokens") or u.get("prompt_tokens") or u.get("input"),
                "output_tokens": u.get("output_tokens") or u.get("completion_tokens") or u.get("output"),
                "total_tokens": u.get("total_tokens") or (
                    (u.get("input_tokens") or u.get("prompt_tokens") or u.get("input") or 0)
                    + (u.get("output_tokens") or u.get("completion_tokens") or u.get("output") or 0)
                    if (u.get("input_tokens") is not None or u.get("prompt_tokens") is not None or u.get("input") is not None
                        or u.get("output_tokens") is not None or u.get("completion_tokens") is not None or u.get("output") is not None)
                    else None
                ),
            }
        except Exception:
            usage = (response_dict.get("usage") or {}) if isinstance(response_dict, dict) else {}

        # Meta adicional: sinalizar se web search foi usado e tamanho de contexto se disponível
        web_search_calls = 0
        try:
            out = (response_dict or {}).get("output") or []
            for it in out:
                if isinstance(it, dict) and it.get("type") == "web_search_call":
                    web_search_calls += 1
        except Exception:
            web_search_calls = 0
        context_size = None
        try:
            for t in (response_dict or {}).get("tools") or []:
                if isinstance(t, dict) and t.get("type") == "web_search_preview":
                    csz = t.get("search_context_size")
                    if isinstance(csz, str):
                        context_size = csz
                        break
        except Exception:
            context_size = None

        return {
            "text": content,
            "blocks": [],
            "links": links,
            "meta": {
                "engine": self.name,
                "model": data.get("model") or (response_dict.get("model") if isinstance(response_dict, dict) else None),
                "raw_usage": usage,
                "web_search_calls": web_search_calls,
                "web_search_used": bool(web_search_calls),
                "search_context_size": context_size,
            },
        }

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:
        citations: List[Citation] = []
        seen = set()
        for link in parsed.get("links", []):
            url = link.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            citations.append(
                {
                    "domain": url,
                    "url": url,
                    "anchor": link.get("title") or None,
                    "position": None,
                    "type": "link",
                }
            )
        return citations

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:
        return parsed

    # -------------------- helpers --------------------
    def _extract_text_from_response_dict(self, response_dict: Dict[str, Any]) -> str:
        """Best-effort text extraction for Responses API dicts (when output_text is absent)."""
        if not isinstance(response_dict, dict):
            return ""

        # New Responses format usually has a top-level "output" list with assistant messages
        output = response_dict.get("output")
        if isinstance(output, list):
            parts: List[str] = []
            for item in output:
                # Expecting items with structure like {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "..."}, ...]}
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    content_list = item.get("content")
                    if isinstance(content_list, list):
                        for c in content_list:
                            if isinstance(c, dict):
                                # The SDK uses various keys; prefer "text" if present
                                text_val = c.get("text") or c.get("content")
                                if isinstance(text_val, str):
                                    parts.append(text_val)
            if parts:
                return "\n".join(parts).strip()

        # Fallbacks: some beta responses may store a string under "content"
        content = response_dict.get("content")
        if isinstance(content, str):
            return content

        # Legacy compatibility: try to mimic Chat Completions-style shape if present
        choices = response_dict.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] or {}
            msg = first.get("message") or {}
            if isinstance(msg, dict):
                txt = msg.get("content")
                if isinstance(txt, str):
                    return txt
        return ""
