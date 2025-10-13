"""
GEO Semantic Analyzer Service - Gemini-powered semantic quality analysis.

Analyzes semantic quality of LLM responses across dimensions:
- Authority: Credibility and expertise signals
- Relevance: Match to user intent
- Clarity: Readability and organization
- Context: Contextual understanding
- Precision: Accuracy and specificity
- Freshness: Timeliness of information
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from app.models.models import Run, PromptVersion

logger = logging.getLogger(__name__)


def analyze_semantic_scores(run: Run, db: Session) -> Dict[str, Optional[float]]:
    """
    Analyze semantic quality of run using Gemini API.

    Returns dictionary with scores (0-100) for:
    - authority: Credibility, expertise signals, source quality
    - relevance: Match to user intent and query
    - clarity: Readability, structure, organization
    - context: Contextual understanding and appropriateness
    - precision: Accuracy, specificity, detail level
    - freshness: Timeliness and currency of information

    Args:
        run: Run object to analyze
        db: Database session

    Returns:
        Dictionary with semantic scores (0-100) or None if analysis fails
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini library not available, skipping semantic analysis")
        return {
            "authority": None,
            "relevance": None,
            "clarity": None,
            "context": None,
            "precision": None,
            "freshness": None,
        }

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not found, skipping semantic analysis")
        return {
            "authority": None,
            "relevance": None,
            "clarity": None,
            "context": None,
            "precision": None,
            "freshness": None,
        }

    # Get prompt text from PromptVersion
    prompt_text = ""
    if run.prompt_version_id:
        prompt_version = db.get(PromptVersion, run.prompt_version_id)
        if prompt_version:
            prompt_text = prompt_version.text or ""

    response_text = run.response_text or ""

    if not prompt_text or not response_text:
        logger.warning(f"Run {run.id} missing prompt or response text")
        return {
            "authority": None,
            "relevance": None,
            "clarity": None,
            "context": None,
            "precision": None,
            "freshness": None,
        }

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-flash-latest")

        analysis_prompt = f"""Analise a qualidade semântica desta resposta de chatbot em 6 dimensões.

PERGUNTA DO USUÁRIO:
{prompt_text[:1000]}

RESPOSTA DO CHATBOT:
{response_text[:2500]}

Avalie a resposta em uma escala de 0 a 100 para cada dimensão:

**authority** (Autoridade e Credibilidade):
- 90-100: Múltiplas fontes confiáveis, dados verificáveis, expertise clara
- 70-89: Fontes identificadas, informações consistentes
- 50-69: Algumas referências, credibilidade moderada
- 30-49: Poucas fontes, credibilidade questionável
- 0-29: Sem fontes, informações genéricas ou duvidosas

**relevance** (Relevância ao Intent):
- 90-100: Resposta diretamente endereça a pergunta, altamente relevante
- 70-89: Boa correspondência, alguns pontos tangenciais
- 50-69: Parcialmente relevante, informações secundárias
- 30-49: Baixa relevância, desvia do tópico
- 0-29: Irrelevante ou fora do contexto

**clarity** (Clareza e Organização):
- 90-100: Estrutura lógica clara, linguagem simples, bem formatada
- 70-89: Boa organização, fácil de seguir
- 50-69: Organização aceitável, alguma confusão
- 30-49: Desorganizada, difícil de acompanhar
- 0-29: Confusa, mal estruturada

**context** (Compreensão Contextual):
- 90-100: Entende nuances, considera contexto do usuário
- 70-89: Bom entendimento contextual
- 50-69: Contexto básico considerado
- 30-49: Pouca consideração do contexto
- 0-29: Ignora contexto

**precision** (Precisão e Especificidade):
- 90-100: Informações específicas, detalhadas, precisas
- 70-89: Bom nível de detalhe e precisão
- 50-69: Informações genéricas mas corretas
- 30-49: Vago, falta especificidade
- 0-29: Impreciso ou incorreto

**freshness** (Atualidade):
- 90-100: Informações recentes (2024-2025), menciona datas
- 70-89: Informações atualizadas (últimos 2 anos)
- 50-69: Informações geralmente atuais
- 30-49: Possivelmente desatualizado
- 0-29: Claramente desatualizado ou sem indicação temporal

Retorne APENAS um objeto JSON válido (sem markdown, sem explicações) com esta estrutura:
{{
  "authority": 85,
  "relevance": 92,
  "clarity": 78,
  "context": 88,
  "precision": 75,
  "freshness": 90
}}

Retorne APENAS o JSON com os 6 scores numéricos (0-100)."""

        response = model.generate_content(analysis_prompt)

        if not response or not response.text:
            logger.warning(f"Empty response from Gemini for run {run.id}")
            return {
                "authority": None,
                "relevance": None,
                "clarity": None,
                "context": None,
                "precision": None,
                "freshness": None,
            }

        # Clean response text (remove markdown code blocks if present)
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON
        scores = json.loads(response_text)

        # Validate and clamp scores to 0-100
        result = {}
        expected_keys = ["authority", "relevance", "clarity", "context", "precision", "freshness"]

        for key in expected_keys:
            value = scores.get(key)
            if value is None:
                result[key] = None
            elif not isinstance(value, (int, float)):
                logger.warning(f"Invalid type for {key} in run {run.id}: {type(value)}")
                result[key] = None
            else:
                # Clamp to 0-100
                result[key] = max(0.0, min(100.0, float(value)))

        logger.info(f"Analyzed semantic scores for run {run.id}: {result}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON for run {run.id}: {e}")
        logger.error(f"Response text: {response.text[:500]}")
        return {
            "authority": None,
            "relevance": None,
            "clarity": None,
            "context": None,
            "precision": None,
            "freshness": None,
        }

    except Exception as e:
        logger.error(f"Error analyzing semantic scores for run {run.id}: {e}")
        return {
            "authority": None,
            "relevance": None,
            "clarity": None,
            "context": None,
            "precision": None,
            "freshness": None,
        }
