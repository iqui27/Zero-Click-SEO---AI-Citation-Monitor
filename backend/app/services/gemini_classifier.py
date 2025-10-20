"""
Classificador avançado usando Gemini 2.5 Pro para análise retroativa
Fornece classificações mais precisas e insights detalhados para métricas Zero-Click.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from app.core.config import settings


class ResponseType(str, Enum):
    DIRETA = "direta"
    EXPLICATIVA = "explicativa"
    INSTRUCIONAL = "instrucional"
    COMPARATIVA = "comparativa"
    CONSULTIVA = "consultiva"
    NAVEGACIONAL = "navegacional"


class SufficiencyLevel(str, Enum):
    TOTAL = "total"
    PARCIAL = "parcial"
    INSUFICIENTE = "insuficiente"


class ActionabilityType(str, Enum):
    TRANSACIONAL = "transacional"
    INFORMATIVA = "informativa"


class TrustSource(str, Enum):
    CITADA = "citada"
    GENERICA = "generica"


class BrandPositioning(str, Enum):
    PROTAGONISTA = "protagonista"
    COMPETIDOR = "competidor"
    AUSENTE = "ausente"


class QuestionType(str, Enum):
    MARCA = "marca"
    PRODUTO = "produto"
    INFORMACAO = "informacao"
    COMPARACAO = "comparacao"


class FunnelStage(str, Enum):
    RECONHECIMENTO = "reconhecimento"
    CONSIDERACAO = "consideracao"
    CONVERSAO = "conversao"


class UserIntent(str, Enum):
    INFORMATIONAL = "informational"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"
    COMMERCIAL = "commercial"


class ConversionPotential(str, Enum):
    ALTO = "alto"
    MEDIO = "medio"
    BAIXO = "baixo"


@dataclass
class AdvancedMetrics:
    user_intent: UserIntent
    satisfaction_score: float
    competitive_mentions: int
    financial_value_score: float
    content_gap_detected: bool
    conversion_potential: ConversionPotential


@dataclass
class ClassificationResult:
    response_type: ResponseType
    sufficiency_level: SufficiencyLevel
    actionability_type: ActionabilityType
    trust_source: TrustSource
    brand_positioning: BrandPositioning
    question_type: QuestionType
    funnel_stage: FunnelStage
    confidence: float
    reasoning: Dict[str, str]

@dataclass
class GeminiAnalysisResult:
    """Resultado completo da análise pelo Gemini"""
    # Classificação básica
    response_type: ResponseType
    sufficiency_level: SufficiencyLevel
    actionability_type: ActionabilityType
    trust_source: TrustSource
    brand_positioning: BrandPositioning
    question_type: QuestionType
    funnel_stage: FunnelStage

    # Métricas avançadas
    user_intent: UserIntent
    satisfaction_score: float
    competitive_mentions: int
    financial_value_score: float
    content_gap_detected: bool
    conversion_potential: ConversionPotential

    # Insights e justificativas
    confidence: float
    reasoning: Dict[str, str]
    strategic_insights: List[str]
    optimization_suggestions: List[str]

class GeminiZeroClickAnalyzer:
    """Analisador Zero-Click usando Gemini 2.5 Pro"""

    def __init__(self, api_key: str = None, model_name: str = "gemini-2.5-pro"):
        if not GENAI_AVAILABLE:
            raise ImportError("google-generativeai não está instalado")

        self.api_key = api_key or settings.google_api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("API key do Google/Gemini não configurada")

        self.model_name = model_name
        genai.configure(api_key=self.api_key)

        # Configurar modelo com parâmetros otimizados
        generation_config = {
            "temperature": 0.1,  # Baixa para análise consistente
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 4000,
            "response_mime_type": "application/json",
        }

        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        # Configurar domínios e concorrentes do Banco do Brasil
        self.target_domains = ["bb.com.br", "bancodobrasil.com.br"]
        self.bank_keywords = ["banco do brasil", "bb", "banco do brasil s.a.", "ourocard"]
        self.competitor_keywords = [
            "itaú", "bradesco", "caixa", "santander", "nubank", "inter",
            "c6", "original", "safra", "btg", "pan", "neon", "picpay"
        ]

    def analyze_with_gemini(self, prompt_text: str, response_text: str,
                          citations: List[Dict] = None) -> GeminiAnalysisResult:
        """
        Executa análise completa usando Gemini 2.5 Pro

        Args:
            prompt_text: Pergunta/prompt original
            response_text: Resposta do LLM a ser analisada
            citations: Lista de citações encontradas

        Returns:
            GeminiAnalysisResult com análise completa
        """
        citations = citations or []

        # Construir contexto para o Gemini
        analysis_prompt = self._build_analysis_prompt(prompt_text, response_text, citations)

        try:
            # Executar análise
            response = self.model.generate_content(analysis_prompt)

            # Parse da resposta JSON
            analysis_data = json.loads(response.text)

            # Converter para objetos estruturados
            return self._parse_gemini_response(analysis_data)

        except Exception as e:
            print(f"[GEMINI_CLASSIFIER] Erro na análise: {e}")
            raise

    def _build_analysis_prompt(self, prompt: str, response: str, citations: List[Dict]) -> str:
        """Constrói prompt estruturado para análise do Gemini"""

        citations_text = ""
        if citations:
            citations_text = "\n".join([
                f"- {cite.get('domain', 'N/A')}: {cite.get('url', 'N/A')}"
                for cite in citations[:10]  # Limitar a 10 citações
            ])

        return f"""
Você é um especialista em SEO Zero-Click e análise de respostas de IA. Analise a interação abaixo e forneça uma classificação completa.

## CONTEXTO
- **Marca analisada**: Banco do Brasil (BB)
- **Domínios alvo**: {', '.join(self.target_domains)}
- **Concorrentes**: {', '.join(self.competitor_keywords)}

## DADOS PARA ANÁLISE

**PERGUNTA ORIGINAL:**
{prompt}

**RESPOSTA DA IA:**
{response}

**CITAÇÕES ENCONTRADAS:**
{citations_text if citations_text else "Nenhuma citação"}

## INSTRUÇÕES DE ANÁLISE

Analise todos os aspectos e retorne um JSON com a seguinte estrutura EXATA:

```json
{{
  "classification": {{
    "response_type": "direta|explicativa|instrucional|comparativa|consultiva|navegacional",
    "sufficiency_level": "total|parcial|insuficiente",
    "actionability_type": "transacional|informativa",
    "trust_source": "citada|generica",
    "brand_positioning": "protagonista|competidor|ausente",
    "question_type": "marca|produto|informacao|comparacao",
    "funnel_stage": "reconhecimento|consideracao|conversao"
  }},
  "advanced_metrics": {{
    "user_intent": "informational|transactional|navigational|commercial",
    "satisfaction_score": 0.85,
    "competitive_mentions": 2,
    "financial_value_score": 7.5,
    "content_gap_detected": true,
    "conversion_potential": "alto|medio|baixo"
  }},
  "analysis": {{
    "confidence": 0.90,
    "reasoning": {{
      "response_type": "Explicação da classificação do tipo",
      "brand_positioning": "Análise do posicionamento da marca",
      "question_type": "Justificativa do tipo de pergunta",
      "funnel_stage": "Motivo do estágio de funil atribuído",
      "user_intent": "Justificativa da intenção identificada",
      "satisfaction_score": "Razão do score de satisfação",
      "content_gap": "Análise de gaps de conteúdo"
    }},
    "strategic_insights": [
      "Insight estratégico 1 sobre oportunidades",
      "Insight estratégico 2 sobre riscos"
    ],
    "optimization_suggestions": [
      "Sugestão 1 para otimização de conteúdo",
      "Sugestão 2 para melhorar posicionamento"
    ]
  }}
}}
```

## CRITÉRIOS ESPECÍFICOS

**RESPONSE_TYPE:**
- direta: Resposta objetiva e factual
- explicativa: Explica conceitos bancários
- instrucional: Guia passo-a-passo
- comparativa: Compara produtos/bancos
- consultiva: Recomendação ou opinião
- navegacional: Direcionamento para site/app

**BRAND_POSITIONING:**
- protagonista: BB é a solução principal mencionada
- competidor: BB aparece junto com outros bancos
- ausente: BB não é mencionado mas deveria estar

**QUESTION_TYPE:**
- marca: Usuário busca informações sobre a marca/instituição
- produto: Usuário cita produtos/serviços específicos
- informacao: Usuário procura contexto ou explicação geral
- comparacao: Usuário compara opções, pergunta diferenças ou alternativas

**FUNNEL_STAGE:**
- reconhecimento: Topo de funil, intenção de aprendizado/descoberta
- consideracao: Meio de funil, comparação e avaliação de alternativas
- conversao: Fundo de funil, intenção de ação direta ou contratação

**USER_INTENT:**
- informational: Busca entender conceitos
- transactional: Quer realizar ação (abrir conta, etc.)
- navigational: Procura site/app específico
- commercial: Compara produtos antes de decidir

**SATISFACTION_SCORE:** (0.0-1.0)
- 0.8-1.0: Resposta completa, precisa, acionável
- 0.5-0.7: Resposta útil mas incompleta
- 0.0-0.4: Resposta vaga ou incorreta

**FINANCIAL_VALUE_SCORE:** (0.0-10.0)
- 8.0-10.0: Produtos de alto valor (empréstimos, investimentos)
- 5.0-7.9: Produtos médios (cartão, conta)
- 0.0-4.9: Informações gerais ou baixo valor

**CONTENT_GAP_DETECTED:**
- true: Concorrentes mencionados mas BB ausente
- false: BB adequadamente representado ou sem concorrentes

Seja preciso, objetivo e foque em insights acionáveis para otimização SEO.
"""

    def _parse_gemini_response(self, data: Dict[str, Any]) -> GeminiAnalysisResult:
        """Converte resposta JSON do Gemini para objetos estruturados"""

        classification = data.get("classification", {})
        advanced = data.get("advanced_metrics", {})
        analysis = data.get("analysis", {})

        # Parse classificação básica
        response_type = ResponseType(classification.get("response_type", "direta"))
        sufficiency_level = SufficiencyLevel(classification.get("sufficiency_level", "parcial"))
        actionability_type = ActionabilityType(classification.get("actionability_type", "informativa"))
        trust_source = TrustSource(classification.get("trust_source", "generica"))
        brand_positioning = BrandPositioning(classification.get("brand_positioning", "ausente"))
        question_type = QuestionType(classification.get("question_type", "informacao"))
        funnel_stage = FunnelStage(classification.get("funnel_stage", "reconhecimento"))

        # Parse métricas avançadas
        user_intent = UserIntent(advanced.get("user_intent", "informational"))
        satisfaction_score = float(advanced.get("satisfaction_score", 0.5))
        competitive_mentions = int(advanced.get("competitive_mentions", 0))
        financial_value_score = float(advanced.get("financial_value_score", 0.0))
        content_gap_detected = bool(advanced.get("content_gap_detected", False))
        conversion_potential = ConversionPotential(advanced.get("conversion_potential", "baixo"))

        # Parse análise
        confidence = float(analysis.get("confidence", 0.7))
        reasoning = analysis.get("reasoning", {})
        strategic_insights = analysis.get("strategic_insights", [])
        optimization_suggestions = analysis.get("optimization_suggestions", [])

        return GeminiAnalysisResult(
            response_type=response_type,
            sufficiency_level=sufficiency_level,
            actionability_type=actionability_type,
            trust_source=trust_source,
            brand_positioning=brand_positioning,
            question_type=question_type,
            funnel_stage=funnel_stage,
            user_intent=user_intent,
            satisfaction_score=satisfaction_score,
            competitive_mentions=competitive_mentions,
            financial_value_score=financial_value_score,
            content_gap_detected=content_gap_detected,
            conversion_potential=conversion_potential,
            confidence=confidence,
            reasoning=reasoning,
            strategic_insights=strategic_insights,
            optimization_suggestions=optimization_suggestions
        )

def analyze_with_gemini_classifier(prompt_text: str, response_text: str,
                                 citations: List[Dict] = None) -> GeminiAnalysisResult:
    """
    Função de conveniência para análise com Gemini

    Args:
        prompt_text: Texto da pergunta
        response_text: Texto da resposta
        citations: Lista de citações

    Returns:
        GeminiAnalysisResult
    """
    analyzer = GeminiZeroClickAnalyzer()
    return analyzer.analyze_with_gemini(prompt_text, response_text, citations)
