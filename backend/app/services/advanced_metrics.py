"""
Sistema Avançado de Métricas Zero-Click
Implementa classificação de intenção, análise competitiva e métricas de valor.
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

class UserIntent(str, Enum):
    """Classificação de intenção do usuário"""
    INFORMATIONAL = "informational"  # Busca informações/conceitos
    TRANSACTIONAL = "transactional"  # Quer realizar ação/compra
    NAVIGATIONAL = "navigational"    # Busca site/página específica
    COMMERCIAL = "commercial"        # Pesquisa produtos/comparação

class ConversionPotential(str, Enum):
    """Potencial de conversão da consulta"""
    ALTO = "alto"      # Alta probabilidade de conversão
    MEDIO = "medio"    # Probabilidade média
    BAIXO = "baixo"    # Baixa probabilidade

@dataclass
class AdvancedMetrics:
    """Resultado das métricas avançadas"""
    user_intent: UserIntent
    satisfaction_score: float  # 0.0-1.0
    competitive_mentions: int
    financial_value_score: float  # 0.0-10.0
    content_gap_detected: bool
    conversion_potential: ConversionPotential
    reasoning: Dict[str, str]

class AdvancedMetricsAnalyzer:
    """Analisador de métricas avançadas para Zero-Click"""

    def __init__(self, bank_keywords: List[str] = None, competitor_keywords: List[str] = None):
        self.bank_keywords = bank_keywords or [
            "banco do brasil", "bb", "bb.com.br",
            "banco do brasil s.a.", "contas bb"
        ]

        self.competitor_keywords = competitor_keywords or [
            "itaú", "bradesco", "caixa", "santander", "nubank",
            "inter", "c6", "original", "safra", "votorantim",
            "btg", "pan", "neon", "picpay", "99pay"
        ]

        self._setup_patterns()

    def _setup_patterns(self):
        """Configura padrões de detecção"""

        # Padrões para intenção do usuário
        self.intent_patterns = {
            UserIntent.INFORMATIONAL: [
                r"o que é", r"como funciona", r"qual.*diferença",
                r"definição", r"significado", r"conceito",
                r"tipos de", r"vantagens", r"desvantagens"
            ],
            UserIntent.TRANSACTIONAL: [
                r"como abrir", r"como solicitar", r"quero abrir",
                r"preciso de", r"onde posso", r"como fazer",
                r"abrir conta", r"solicitar cartão", r"contratar"
            ],
            UserIntent.NAVIGATIONAL: [
                r"site do", r"portal", r"login", r"acessar",
                r"entrar no", r"página do", r"app do"
            ],
            UserIntent.COMMERCIAL: [
                r"melhor banco", r"qual banco", r"comparar",
                r"versus", r"vs", r"preços", r"taxas",
                r"ofertas", r"promoções"
            ]
        }

        # Padrões para produtos bancários e valores
        self.product_patterns = {
            "conta_corrente": {
                "patterns": [r"conta corrente", r"conta poupança", r"conta salário"],
                "base_value": 8.0
            },
            "cartao_credito": {
                "patterns": [r"cartão de crédito", r"cartão", r"ourocard"],
                "base_value": 7.0
            },
            "emprestimo": {
                "patterns": [r"empréstimo", r"financiamento", r"crédito"],
                "base_value": 9.5
            },
            "investimentos": {
                "patterns": [r"investimento", r"poupança", r"cdb", r"tesouro"],
                "base_value": 6.0
            },
            "previdencia": {
                "patterns": [r"previdência", r"aposentadoria", r"brasilprev"],
                "base_value": 8.5
            },
            "seguros": {
                "patterns": [r"seguro", r"proteção", r"bb seguro"],
                "base_value": 7.5
            }
        }

        # Padrões para satisfação (qualidade da resposta)
        self.satisfaction_indicators = {
            "high": [
                r"passo a passo", r"detalhadamente", r"completo",
                r"todas.*informações", r"requisitos", r"documentos"
            ],
            "medium": [
                r"resumo", r"principais", r"básico",
                r"em geral", r"normalmente"
            ],
            "low": [
                r"consulte", r"verifique", r"mais informações",
                r"entre em contato", r"procure"
            ]
        }

    def analyze_metrics(self, prompt_text: str, response_text: str,
                       citations: List[Dict] = None) -> AdvancedMetrics:
        """
        Analisa métricas avançadas para uma run

        Args:
            prompt_text: Texto da pergunta/prompt
            response_text: Texto da resposta
            citations: Lista de citações

        Returns:
            AdvancedMetrics com todas as métricas calculadas
        """
        citations = citations or []

        # Normalizar textos
        prompt_norm = self._normalize_text(prompt_text)
        response_norm = self._normalize_text(response_text)

        # Analisar cada métrica
        user_intent = self._classify_user_intent(prompt_norm, response_norm)
        satisfaction_score = self._calculate_satisfaction_score(response_norm, citations)
        competitive_mentions = self._count_competitive_mentions(response_norm)
        financial_value_score = self._calculate_financial_value(prompt_norm, response_norm, user_intent)
        content_gap_detected = self._detect_content_gap(response_norm, citations)
        conversion_potential = self._assess_conversion_potential(user_intent, satisfaction_score, financial_value_score)

        # Gerar justificativas
        reasoning = self._generate_reasoning(
            user_intent, satisfaction_score, competitive_mentions,
            financial_value_score, content_gap_detected, conversion_potential
        )

        return AdvancedMetrics(
            user_intent=user_intent,
            satisfaction_score=satisfaction_score,
            competitive_mentions=competitive_mentions,
            financial_value_score=financial_value_score,
            content_gap_detected=content_gap_detected,
            conversion_potential=conversion_potential,
            reasoning=reasoning
        )

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para análise"""
        if not text:
            return ""
        return text.lower().strip()

    def _classify_user_intent(self, prompt: str, response: str) -> UserIntent:
        """Classifica a intenção do usuário baseado no prompt"""
        if not prompt:
            return UserIntent.INFORMATIONAL

        # Calcular scores por intenção
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, prompt, re.IGNORECASE))
                score += matches
            intent_scores[intent] = score

        # Retornar intenção com maior score
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent

        return UserIntent.INFORMATIONAL

    def _calculate_satisfaction_score(self, response: str, citations: List[Dict]) -> float:
        """Calcula score de satisfação baseado na qualidade da resposta"""
        if not response:
            return 0.0

        base_score = 0.5  # Score base

        # Fatores positivos
        if len(response) > 200:  # Resposta substantiva
            base_score += 0.2

        if len(citations) > 1:  # Múltiplas fontes
            base_score += 0.2

        # Indicadores de alta qualidade
        high_quality_score = sum(1 for pattern in self.satisfaction_indicators["high"]
                               if re.search(pattern, response, re.IGNORECASE))
        base_score += min(high_quality_score * 0.1, 0.2)

        # Indicadores de baixa qualidade (penalizam)
        low_quality_score = sum(1 for pattern in self.satisfaction_indicators["low"]
                              if re.search(pattern, response, re.IGNORECASE))
        base_score -= min(low_quality_score * 0.15, 0.3)

        return max(0.0, min(1.0, base_score))

    def _count_competitive_mentions(self, response: str) -> int:
        """Conta menções a concorrentes na resposta"""
        if not response:
            return 0

        mentions = 0
        for competitor in self.competitor_keywords:
            if competitor.lower() in response:
                mentions += 1

        return mentions

    def _calculate_financial_value(self, prompt: str, response: str, intent: UserIntent) -> float:
        """Calcula valor financeiro estimado da consulta"""
        if not prompt and not response:
            return 0.0

        combined_text = f"{prompt} {response}"
        base_value = 0.0

        # Identificar produtos mencionados
        for product, config in self.product_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    base_value = max(base_value, config["base_value"])

        # Ajustar por intenção
        intent_multipliers = {
            UserIntent.TRANSACTIONAL: 1.5,  # Maior valor
            UserIntent.COMMERCIAL: 1.2,
            UserIntent.NAVIGATIONAL: 0.8,
            UserIntent.INFORMATIONAL: 0.6   # Menor valor
        }

        final_value = base_value * intent_multipliers.get(intent, 1.0)
        return min(10.0, final_value)

    def _detect_content_gap(self, response: str, citations: List[Dict]) -> bool:
        """Detecta se há gap de conteúdo (concorrentes citados mas BB ausente)"""
        if not response:
            return False

        # Verificar se há menções a concorrentes
        competitor_mentioned = any(
            comp.lower() in response for comp in self.competitor_keywords
        )

        # Verificar se BB está ausente
        bb_mentioned = any(
            keyword.lower() in response for keyword in self.bank_keywords
        )

        # Verificar citações de domínios BB
        bb_domain_cited = False
        if citations:
            bb_domain_cited = any(
                "bb.com.br" in citation.get("domain", "").lower()
                for citation in citations
            )

        # Gap detectado se concorrente mencionado mas BB ausente
        return competitor_mentioned and not (bb_mentioned or bb_domain_cited)

    def _assess_conversion_potential(self, intent: UserIntent, satisfaction: float,
                                   financial_value: float) -> ConversionPotential:
        """Avalia potencial de conversão"""

        # Score combinado ponderado
        intent_scores = {
            UserIntent.TRANSACTIONAL: 0.9,
            UserIntent.COMMERCIAL: 0.7,
            UserIntent.NAVIGATIONAL: 0.5,
            UserIntent.INFORMATIONAL: 0.3
        }

        intent_score = intent_scores.get(intent, 0.3)
        combined_score = (intent_score * 0.4) + (satisfaction * 0.3) + (financial_value / 10.0 * 0.3)

        if combined_score >= 0.7:
            return ConversionPotential.ALTO
        elif combined_score >= 0.4:
            return ConversionPotential.MEDIO
        else:
            return ConversionPotential.BAIXO

    def _generate_reasoning(self, user_intent: UserIntent, satisfaction_score: float,
                          competitive_mentions: int, financial_value_score: float,
                          content_gap_detected: bool, conversion_potential: ConversionPotential) -> Dict[str, str]:
        """Gera justificativas para as métricas"""
        return {
            "user_intent": f"Classificado como {user_intent.value} baseado em padrões do prompt",
            "satisfaction_score": f"Score {satisfaction_score:.2f} baseado em qualidade e completude da resposta",
            "competitive_mentions": f"{competitive_mentions} concorrentes mencionados na resposta",
            "financial_value_score": f"Valor {financial_value_score:.1f}/10.0 baseado em produtos identificados",
            "content_gap_detected": "Gap detectado: concorrentes citados mas BB ausente" if content_gap_detected else "Sem gap de conteúdo detectado",
            "conversion_potential": f"Potencial {conversion_potential.value} baseado em intenção e qualidade"
        }


def analyze_run_advanced_metrics(prompt_text: str, response_text: str,
                               citations: List[Dict] = None) -> AdvancedMetrics:
    """
    Função de conveniência para análise de métricas avançadas

    Args:
        prompt_text: Texto do prompt
        response_text: Texto da resposta
        citations: Lista de citações

    Returns:
        AdvancedMetrics
    """
    analyzer = AdvancedMetricsAnalyzer()
    return analyzer.analyze_metrics(prompt_text, response_text, citations)