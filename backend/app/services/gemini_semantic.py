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
    def _get_empty_structure() -> Dict[str, Any]:
        """Retorna estrutura vazia válida para quando Gemini falha."""
        return {
            "entities": [],
            "relationships": [],
            "keywords": [],
            "perception": {},
            "summary": {},
            "competitors": [],
            "wordcloud": []
        }
    
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
        """Extrai JSON de resposta do Gemini com limpeza agressiva."""
        import re
        
        # 1. Remover espaços em branco extras
        cleaned = raw.strip()
        
        # 2. Remover markdown code blocks
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remover primeira linha (```json ou ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remover última linha se for ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        
        # 3. Tentar parse direto
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # 4. Remover texto antes e depois do JSON
        # Procurar primeiro { e último }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        
        if start != -1 and end != -1 and end > start:
            json_candidate = cleaned[start : end + 1]
            
            # 5. Tentar parse do trecho extraído
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError:
                pass
            
            # 6. Limpeza agressiva: remover linhas que não são JSON
            lines = json_candidate.split("\n")
            json_lines = []
            for line in lines:
                stripped = line.strip()
                # Manter apenas linhas que parecem JSON
                if (stripped.startswith("{") or stripped.startswith("[") or 
                    stripped.startswith('"') or stripped.startswith("}") or 
                    stripped.startswith("]") or stripped.endswith(",") or
                    ":" in stripped or stripped == ""):
                    json_lines.append(line)
            
            cleaned_json = "\n".join(json_lines)
            
            # 7. Última tentativa
            try:
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                pass
        
        # 8. Se tudo falhar, retornar estrutura vazia ao invés de erro
        print(f"[SEMANTIC] Aviso: Não foi possível parsear JSON. Retornando estrutura vazia.")
        print(f"[SEMANTIC] Resposta original (primeiros 200 chars): {raw[:200]}")
        
        # Retornar estrutura mínima válida ao invés de lançar erro
        return GeminiSemanticService._get_empty_structure()

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
        simplified: bool = False,
    ) -> str:
        # Prompt simplificado para retry (mais neutro, menos chance de bloqueio)
        if simplified:
            return f"""
Analise o seguinte texto e extraia informações estruturadas em formato JSON.

Texto para análise:
{response_text[:1500]}

Retorne APENAS um objeto JSON com esta estrutura:
{{
  "entities": [
    {{"name": "nome", "category": "brand|product|other", "confidence": 0.8}}
  ],
  "keywords": [
    {{"token": "palavra", "weight": 0.7}}
  ],
  "summary": {{
    "headline": "resumo breve"
  }}
}}

Importante: Retorne APENAS o JSON, sem texto adicional.
"""
        
        # Prompt completo normal
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

### Instruções CRÍTICAS - SIGA EXATAMENTE
1. **RETORNE APENAS JSON PURO** - Nada mais, nenhum texto antes ou depois
2. **NÃO USE MARKDOWN** - Sem ```json, sem ```, sem formatação
3. **COMECE COM {{** e **TERMINE COM }}** - Primeira e última caractere
4. **SEM EXPLICAÇÕES** - Não adicione "Aqui está", "Observação", etc.
5. **SEM COMENTÁRIOS** - Não inclua // ou /* */ no JSON
6. Identifique entidades relevantes (marcas, produtos, categorias, concorrentes) com confiança 0-1
7. Relacione marcas com produtos e concorrentes
8. Extraia as top palavras-chave (token) com peso 0-1, associando a quais marcas/produtos aparecem
9. Classifique a percepção/valor predominante entre: inovacao, tradicao, custo, atendimento
10. Gere um resumo (headline + bullets) com oportunidades e riscos

**EXEMPLO DE RESPOSTA CORRETA:**
{{
  "entities": [...],
  "relationships": [...],
  ...
}}

**EXEMPLO DE RESPOSTA INCORRETA (NÃO FAÇA ISSO):**
Aqui está a análise:
```json
{{...}}
```
Observação: Alguns dados podem estar incompletos.

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
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        citations = citations or []
        citations_text = self._format_citations(citations)
        
        # Tentar com prompt normal primeiro, depois com prompt simplificado
        for attempt in range(max_retries):
            # No retry, usar prompt mais neutro/simplificado
            use_simplified = attempt > 0
            
            prompt = self.build_prompt(
                question=question,
                response_text=response_text,
                citations_text=citations_text,
                project_name=project_name,
                simplified=use_simplified,
            )

            try:
                response = self.model.generate_content(prompt)
            except Exception as e:
                print(f"[SEMANTIC] Tentativa {attempt + 1}/{max_retries}: Erro ao chamar Gemini API: {e}")
                if attempt < max_retries - 1:
                    continue  # Tentar novamente
                print(f"[SEMANTIC] Todas as tentativas falharam. Retornando estrutura vazia.")
                return self._get_empty_structure()
            
            # Verificar finish_reason para detectar bloqueios
            if response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", None)
                
                # finish_reason 2 = SAFETY (bloqueado por filtro de segurança)
                # finish_reason 3 = RECITATION (bloqueado por recitação)
                # finish_reason 4 = OTHER (outros bloqueios)
                if finish_reason in [2, 3, 4]:
                    reason_names = {2: "SAFETY", 3: "RECITATION", 4: "OTHER"}
                    reason_name = reason_names.get(finish_reason, str(finish_reason))
                    print(f"[SEMANTIC] Tentativa {attempt + 1}/{max_retries}: Gemini bloqueou resposta: finish_reason={reason_name}")
                    
                    if attempt < max_retries - 1:
                        print(f"[SEMANTIC] Tentando novamente com prompt simplificado...")
                        continue  # Tentar com prompt simplificado
                    
                    print(f"[SEMANTIC] Todas as tentativas bloqueadas. Retornando estrutura vazia.")
                    return self._get_empty_structure()
            
            # Se chegou aqui, não foi bloqueado - continuar processamento
            break
        
        # Tentar obter texto da resposta
        raw_text = None
        try:
            raw_text = response.text
        except (ValueError, AttributeError) as e:
            # response.text pode lançar erro se não houver partes válidas
            print(f"[SEMANTIC] Erro ao acessar response.text: {e}")
            
            # Fallback: tentar concatenar partes manualmente
            if response.candidates:
                raw_parts = []
                for candidate in response.candidates:
                    content = getattr(candidate, "content", None)
                    if content:
                        parts = getattr(content, "parts", []) or []
                        for part in parts:
                            text = getattr(part, "text", None)
                            if text:
                                raw_parts.append(text)
                if raw_parts:
                    raw_text = "\n".join(raw_parts)
        
        if not raw_text:
            print(f"[SEMANTIC] Gemini retornou resposta vazia")
            print(f"[SEMANTIC] Retornando estrutura vazia")
            return self._get_empty_structure()

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
