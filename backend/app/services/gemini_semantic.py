"""Serviço para gerar insights semânticos usando Gemini."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmBlockThreshold, HarmCategory
    GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - dependência opcional
    GENAI_AVAILABLE = False

from app.core.config import settings



class GeminiSemanticService:
    """Wrapper simples para chamar Gemini e extrair insights estruturados."""

    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None) -> None:
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
            "max_output_tokens": 5500,
        }

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

    @staticmethod
    def _format_citations(citations: List[Dict[str, Any]]) -> str:
        if not citations:
            return "Nenhuma citação disponível."
        lines = []
        for cite in citations[:12]:
            domain = cite.get("domain") or cite.get("url") or "desconhecido"
            url = cite.get("url") or ""
            lines.append(f"- {domain}: {url}")
        return "\n".join(lines)

    @staticmethod
    def _safe_json_loads(raw: str) -> Dict[str, Any]:
        # Remover markdown code blocks se existirem
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remover ```json ou ``` do início
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Tentar extrair trecho JSON válido
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError("Resposta do Gemini não pôde ser interpretada como JSON")

    @staticmethod
    def _normalize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
        def as_list(value: Any) -> List[Any]:
            if isinstance(value, list):
                return value
            if value is None:
                return []
            return [value]

        payload = {
            "entities": [],
            "relationships": [],
            "keywords": [],
            "perception": {},
            "summary": {},
            "competitors": [],
            "wordcloud": [],
        }

        payload["entities"] = [
            {
                "name": item.get("name"),
                "category": item.get("category") or item.get("type"),
                "roles": as_list(item.get("roles")),
                "confidence": item.get("confidence", 0.0),
                "citations": as_list(item.get("citations")),
                "description": item.get("description"),
            }
            for item in as_list(data.get("entities"))
            if item and item.get("name")
        ]

        payload["relationships"] = [
            {
                "source": item.get("source") or item.get("from"),
                "target": item.get("target") or item.get("to"),
                "type": item.get("type"),
                "weight": item.get("weight", 0.0),
                "explanation": item.get("explanation") or item.get("description"),
            }
            for item in as_list(data.get("relationships") or data.get("relations"))
            if item and (item.get("source") or item.get("from")) and (item.get("target") or item.get("to"))
        ]

        payload["keywords"] = [
            {
                "token": item.get("token") or item.get("keyword"),
                "weight": item.get("weight", item.get("score", 0.0)),
                "brands": as_list(item.get("brands")),
                "products": as_list(item.get("products")),
                "competitors": as_list(item.get("competitors")),
                "context": item.get("context"),
            }
            for item in as_list(data.get("keywords"))
            if item and (item.get("token") or item.get("keyword"))
        ]

        payload["perception"] = data.get("perception") or {}
        payload["summary"] = data.get("summary") or {}
        payload["competitors"] = as_list(data.get("competitors"))
        payload["wordcloud"] = [
            {
                "token": kw.get("token") or kw.get("keyword"),
                "weight": kw.get("weight", kw.get("score", 0.0)),
                "brands": as_list(kw.get("brands")),
            }
            for kw in payload["keywords"]
            if kw.get("token")
        ]

        return payload

    def build_prompt(
        self,
        *,
        question: str,
        response_text: str,
        citations_text: str,
        project_name: Optional[str] = None,
    ) -> str:
        brand_hint = f"Projeto/Marca principal: {project_name}." if project_name else ""

        return f"""
Você é um analista de SEO e posicionamento de marcas para respostas de AI Overview em português.
Extraia insights semânticos estruturados seguindo as instruções abaixo.

{brand_hint}

### Pergunta original
{question}

### Resposta da IA (texto plano)
{response_text}

### Citações detectadas
{citations_text}

### Instruções IMPORTANTES
1. Retorne APENAS um objeto JSON válido
2. NÃO inclua markdown, comentários ou texto adicional
3. NÃO use ```json ou qualquer formatação
4. Comece diretamente com {{ e termine com }}
5. Identifique entidades relevantes (marcas, produtos, categorias, concorrentes) com confiança 0-1
6. Relacione marcas com produtos e concorrentes
7. Extraia as top palavras-chave (token) com peso 0-1, associando a quais marcas/produtos aparecem
8. Classifique a percepção/valor predominante entre: inovacao, tradicao, custo, atendimento
9. Gere um resumo (headline + bullets) com oportunidades e riscos

### Estrutura esperada
{{
  "entities": [{{
      "name": "Banco do Brasil",
      "category": "brand|product|feature|competitor|other",
      "roles": ["brand"],
      "confidence": 0.92,
      "citations": ["https://www.bb.com.br"],
      "description": ""}}
  ],
  "relationships": [{{
      "source": "Banco do Brasil",
      "target": "Conta Digital",
      "type": "brand_product",
      "weight": 0.76,
      "explanation": "Produto próprio destacado como principal oferta"
  }}],
  "keywords": [{{
      "token": "conta digital",
      "weight": 0.81,
      "brands": ["Banco do Brasil"],
      "products": ["Conta Digital"],
      "competitors": ["Nubank"],
      "context": "Termo associado a conta sem tarifa"
  }}],
  "perception": {{
      "primary_category": "inovacao",
      "secondary_categories": ["custo"],
      "confidence": 0.74,
      "rationale": "Resposta destaca experiências digitais e tarifas competitivas"
  }},
  "summary": {{
      "headline": "BB visto como alternativa moderna para contas digitais",
      "bullets": ["AI Overview prioriza apps móveis", "Concorrentes Nubank e Inter citados"],
      "opportunities": ["Reforçar diferenciais em atendimento humano"]
  }},
  "competitors": [{{
      "name": "Nubank",
      "mentions": 2,
      "keywords": ["cartão sem anuidade"]
  }}]
}}
"""

    def analyze(
        self,
        *,
        question: str,
        response_text: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        project_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        citations = citations or []
        citations_text = self._format_citations(citations)
        prompt = self.build_prompt(
            question=question,
            response_text=response_text,
            citations_text=citations_text,
            project_name=project_name,
        )

        response = self.model.generate_content(prompt)
        raw_text = getattr(response, "text", None)

        if not raw_text and response.candidates:
            # Fallback: concatenar partes retornadas
            raw_parts = []
            for candidate in response.candidates:
                for part in getattr(candidate.content, "parts", []) or []:
                    text = getattr(part, "text", None)
                    if text:
                        raw_parts.append(text)
            raw_text = "\n".join(raw_parts)

        if not raw_text:
            raise ValueError("Gemini retornou resposta vazia ao gerar insights semânticos")

        data = self._safe_json_loads(raw_text)
        normalized = self._normalize_payload(data)

        usage = getattr(response, "usage_metadata", None)
        if usage:
            normalized["usage"] = {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "candidates_tokens": getattr(usage, "candidates_token_count", None),
                "total_tokens": getattr(usage, "total_token_count", None),
            }

        return normalized
