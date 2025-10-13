"""
GEO Classifier Service - Gemini-powered classification for runs.

Classifies runs into:
- Funnel Stage (consciencia, consideracao, decisao, pos_compra)
- Question Type (informacional, transacional, navegacional, comparativa)
- Product Category (cartoes, credito, investimentos, conta, seguros, etc.)
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


def classify_run_with_gemini(run: Run, db: Session) -> Dict[str, Optional[str]]:
    """
    Classify run using Gemini API.

    Returns dictionary with:
    - funnel_stage: consciencia | consideracao | decisao | pos_compra
    - question_type: informacional | transacional | navegacional | comparativa
    - product_category: cartoes | credito | investimentos | conta | seguros | empresarial | digital | multiproduto

    Args:
        run: Run object to classify
        db: Database session

    Returns:
        Dictionary with classification results
    """
    if not GEMINI_AVAILABLE:
        logger.warning("Gemini library not available, skipping classification")
        return {"funnel_stage": None, "question_type": None, "product_category": None}

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not found, skipping classification")
        return {"funnel_stage": None, "question_type": None, "product_category": None}

    # Get prompt text from PromptVersion
    prompt_text = ""
    if run.prompt_version_id:
        prompt_version = db.get(PromptVersion, run.prompt_version_id)
        if prompt_version:
            prompt_text = prompt_version.text or ""

    response_text = run.response_text or ""

    if not prompt_text or not response_text:
        logger.warning(f"Run {run.id} missing prompt or response text")
        return {"funnel_stage": None, "question_type": None, "product_category": None}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-flash-latest")

        classification_prompt = f"""Analise o seguinte par de pergunta-resposta de um chatbot e classifique em três dimensões:

PERGUNTA:
{prompt_text[:1000]}

RESPOSTA:
{response_text[:2000]}

Retorne APENAS um objeto JSON válido (sem markdown, sem texto adicional) com esta estrutura exata:
{{
  "funnel_stage": "consciencia" | "consideracao" | "decisao" | "pos_compra",
  "question_type": "informacional" | "transacional" | "navegacional" | "comparativa",
  "product_category": "cartoes" | "credito" | "investimentos" | "conta" | "seguros" | "empresarial" | "digital" | "multiproduto"
}}

CRITÉRIOS DE CLASSIFICAÇÃO:

**funnel_stage** (Estágio do Funil):
- consciencia: Usuário está descobrindo o problema/necessidade (ex: "o que é...", "como funciona...")
- consideracao: Usuário está avaliando soluções (ex: "qual o melhor...", "vantagens de...")
- decisao: Usuário está pronto para escolher (ex: "como contratar...", "onde abrir...")
- pos_compra: Usuário já é cliente buscando suporte (ex: "como cancelar...", "esqueci a senha...")

**question_type** (Tipo de Pergunta):
- informacional: Busca informações gerais (ex: "o que é cartão de crédito")
- transacional: Quer realizar uma ação (ex: "abrir conta", "solicitar cartão")
- navegacional: Busca site/marca específica (ex: "site do banco X", "login banco Y")
- comparativa: Compara opções (ex: "banco X vs Y", "qual melhor entre...")

**product_category** (Categoria de Produto):
- cartoes: Cartões de crédito/débito
- credito: Empréstimos, financiamentos, crédito pessoal
- investimentos: Aplicações, renda fixa/variável, fundos
- conta: Contas corrente, poupança, digital
- seguros: Seguros em geral
- empresarial: Produtos PJ, MEI
- digital: Serviços bancários digitais, apps
- multiproduto: Múltiplos produtos ou serviços bancários gerais

Retorne APENAS o JSON, sem explicações."""

        response = model.generate_content(classification_prompt)

        if not response or not response.text:
            logger.warning(f"Empty response from Gemini for run {run.id}")
            return {"funnel_stage": None, "question_type": None, "product_category": None}

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
        classification = json.loads(response_text)

        # Validate fields
        valid_funnel_stages = {"consciencia", "consideracao", "decisao", "pos_compra"}
        valid_question_types = {"informacional", "transacional", "navegacional", "comparativa"}
        valid_categories = {"cartoes", "credito", "investimentos", "conta", "seguros", "empresarial", "digital", "multiproduto"}

        funnel_stage = classification.get("funnel_stage")
        question_type = classification.get("question_type")
        product_category = classification.get("product_category")

        # Validate or set to None
        if funnel_stage not in valid_funnel_stages:
            logger.warning(f"Invalid funnel_stage '{funnel_stage}' for run {run.id}")
            funnel_stage = None

        if question_type not in valid_question_types:
            logger.warning(f"Invalid question_type '{question_type}' for run {run.id}")
            question_type = None

        if product_category not in valid_categories:
            logger.warning(f"Invalid product_category '{product_category}' for run {run.id}")
            product_category = None

        logger.info(f"Classified run {run.id}: funnel={funnel_stage}, type={question_type}, category={product_category}")

        return {
            "funnel_stage": funnel_stage,
            "question_type": question_type,
            "product_category": product_category,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON for run {run.id}: {e}")
        logger.error(f"Response text: {response.text[:500]}")
        return {"funnel_stage": None, "question_type": None, "product_category": None}

    except Exception as e:
        logger.error(f"Error classifying run {run.id} with Gemini: {e}")
        return {"funnel_stage": None, "question_type": None, "product_category": None}
