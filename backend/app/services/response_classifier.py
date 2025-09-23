"""
Serviço de Classificação de Respostas Zero-Click
Implementa o sistema de classificação baseado no documento de conceitos fornecido.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ResponseType(str, Enum):
    """Tipo de Resposta (Classificação Primária)"""
    DIRETA = "direta"               # Fornece informação objetiva e concisa
    EXPLICATIVA = "explicativa"     # Define ou explica um conceito
    INSTRUCIONAL = "instrucional"   # Apresenta passo a passo
    COMPARATIVA = "comparativa"     # Compara produtos/serviços
    CONSULTIVA = "consultiva"       # Oferece opinião/recomendação
    NAVEGACIONAL = "navegacional"   # Direciona para links específicos

class SufficiencyLevel(str, Enum):
    """Nível de Autossuficiência da Resposta"""
    TOTAL = "total"         # Esgota completamente a dúvida
    PARCIAL = "parcial"     # Útil mas incentiva clique adicional
    INSUFICIENTE = "insuficiente"  # Genérica, força busca adicional

class ActionabilityType(str, Enum):
    """Tipo de Acionabilidade"""
    TRANSACIONAL = "transacional"  # Leva a ação direta
    INFORMATIVA = "informativa"    # Apenas informa

class TrustSource(str, Enum):
    """Fonte de Confiança"""
    CITADA = "citada"      # Inclui citações e links confiáveis
    GENERICA = "generica"  # Sem fontes ou conhecimento geral

class BrandPositioning(str, Enum):
    """Posicionamento da Marca"""
    PROTAGONISTA = "protagonista"  # Marca é solução principal
    COMPETIDOR = "competidor"      # Marca listada entre várias opções
    AUSENTE = "ausente"           # Marca não mencionada

@dataclass
class ClassificationResult:
    """Resultado da classificação de uma resposta"""
    response_type: ResponseType
    sufficiency_level: SufficiencyLevel
    actionability_type: ActionabilityType
    trust_source: TrustSource
    brand_positioning: BrandPositioning
    confidence: float  # 0.0-1.0
    reasoning: Dict[str, str]  # Justificativas para cada classificação

class ResponseClassifier:
    """Classificador principal de respostas Zero-Click"""

    def __init__(self, target_domains: List[str] = None, brand_keywords: List[str] = None):
        """
        Inicializa o classificador

        Args:
            target_domains: Lista de domínios alvo (ex: ['bb.com.br'])
            brand_keywords: Palavras-chave da marca (ex: ['Banco do Brasil', 'BB'])
        """
        self.target_domains = target_domains or []
        self.brand_keywords = brand_keywords or []
        self.version = "1.0"

        # Padrões de detecção
        self._setup_patterns()

    def _setup_patterns(self):
        """Configura padrões de regex para detecção"""
        # Padrões para tipos de resposta
        self.type_patterns = {
            ResponseType.DIRETA: [
                r"é\s+(.{1,50})",
                r"telefone\s+(?:é|:)\s*(\d+)",
                r"endereço\s+(?:é|:)\s*(.+)",
                r"horário\s+(?:é|:)\s*(.+)",
            ],
            ResponseType.EXPLICATIVA: [
                r"o\s+que\s+é",
                r"trata-se\s+de",
                r"consiste\s+em",
                r"é\s+um(?:a)?\s+(?:tipo|forma|modalidade)",
            ],
            ResponseType.INSTRUCIONAL: [
                r"(?:como|para)\s+.+:",
                r"(?:passo|etapa)\s+\d+",
                r"primeiro.+segundo.+terceiro",
                r"siga\s+(?:os\s+)?passos",
            ],
            ResponseType.COMPARATIVA: [
                r"(?:versus|vs\.?|comparado)",
                r"vantagens\s+(?:e\s+)?desvantagens",
                r"diferenças?\s+entre",
                r"melhor\s+opção",
            ],
            ResponseType.CONSULTIVA: [
                r"vale\s+a\s+pena",
                r"recomend(?:o|amos)",
                r"aconselho",
                r"sugiro",
                r"na\s+minha\s+opinião",
            ],
            ResponseType.NAVEGACIONAL: [
                r"acesse\s+(?:o\s+)?(?:link|site)",
                r"clique\s+(?:aqui|no\s+link)",
                r"visite\s+(?:o\s+)?site",
                r"disponível\s+em:",
            ]
        }

        # Padrões para acionabilidade
        self.action_patterns = {
            "transacional": [
                r"(?:clique|acesse|visite|ligue|entre\s+em\s+contato)",
                r"(?:abra|crie|solicite|contrate)",
                r"(?:telefone|whatsapp|email):\s*",
                r"(?:cadastre-se|inscreva-se|registre-se)",
            ],
            "informativa": [
                r"(?:entenda|compreenda|saiba\s+mais)",
                r"(?:informações|detalhes|características)",
                r"(?:conceito|definição|explicação)",
            ]
        }

        # Padrões para fontes de confiança
        self.trust_patterns = {
            "citada": [
                r"(?:fonte|segundo|conforme|de\s+acordo\s+com):",
                r"http[s]?://",
                r"(?:site|portal|página)\s+oficial",
                r"(?:documento|relatório|estudo)\s+oficial",
            ]
        }

    def classify_response(self, response_text: str, citations: List[Dict] = None,
                         prompt_text: str = None) -> ClassificationResult:
        """
        Classifica uma resposta completa

        Args:
            response_text: Texto da resposta a ser classificada
            citations: Lista de citações encontradas na resposta
            prompt_text: Texto original do prompt (opcional, para contexto)

        Returns:
            ClassificationResult com todas as classificações
        """
        citations = citations or []

        # Normalizar texto para análise
        normalized_text = self._normalize_text(response_text)

        # Classificar cada dimensão
        response_type = self._classify_response_type(normalized_text, prompt_text)
        sufficiency_level = self._classify_sufficiency(normalized_text, citations)
        actionability_type = self._classify_actionability(normalized_text)
        trust_source = self._classify_trust_source(normalized_text, citations)
        brand_positioning = self._classify_brand_positioning(normalized_text, citations)

        # Calcular confiança geral (média ponderada)
        confidence = self._calculate_confidence(
            response_type, sufficiency_level, actionability_type,
            trust_source, brand_positioning, normalized_text
        )

        # Gerar justificativas
        reasoning = self._generate_reasoning(
            normalized_text, citations, response_type, sufficiency_level,
            actionability_type, trust_source, brand_positioning
        )

        return ClassificationResult(
            response_type=response_type,
            sufficiency_level=sufficiency_level,
            actionability_type=actionability_type,
            trust_source=trust_source,
            brand_positioning=brand_positioning,
            confidence=confidence,
            reasoning=reasoning
        )

    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para análise"""
        if not text:
            return ""

        # Lowercase e remove caracteres especiais em excesso
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Múltiplos espaços -> 1 espaço

        return normalized

    def _classify_response_type(self, text: str, prompt_text: str = None) -> ResponseType:
        """Classifica o tipo principal da resposta"""
        if not text:
            return ResponseType.DIRETA

        # Verificar padrões em ordem de especificidade
        type_scores = {}

        for response_type, patterns in self.type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            type_scores[response_type] = score

        # Considerar também o prompt se disponível
        if prompt_text:
            prompt_lower = prompt_text.lower()
            if any(word in prompt_lower for word in ["como", "passo", "etapa"]):
                type_scores[ResponseType.INSTRUCIONAL] += 2
            elif any(word in prompt_lower for word in ["o que é", "definição", "conceito"]):
                type_scores[ResponseType.EXPLICATIVA] += 2
            elif any(word in prompt_lower for word in ["vs", "versus", "comparar", "diferença"]):
                type_scores[ResponseType.COMPARATIVA] += 2

        # Retornar tipo com maior score, ou DIRETA como padrão
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] > 0:
                return best_type

        return ResponseType.DIRETA

    def _classify_sufficiency(self, text: str, citations: List[Dict]) -> SufficiencyLevel:
        """Classifica o nível de autossuficiência"""
        if not text:
            return SufficiencyLevel.INSUFICIENTE

        # Fatores que indicam alta suficiência
        high_sufficiency_indicators = [
            len(text) > 200,  # Resposta substantiva
            len(citations) > 2,  # Múltiplas fontes
            "detalhes" in text or "informações completas" in text,
            re.search(r'\d+.*(?:passos?|etapas?)', text),  # Passos numerados
        ]

        # Fatores que indicam baixa suficiência
        low_sufficiency_indicators = [
            len(text) < 50,  # Resposta muito curta
            "consulte" in text or "verifique" in text,
            "mais informações" in text,
            text.count("?") > 2,  # Muitas perguntas não respondidas
        ]

        # Fatores que indicam suficiência parcial
        partial_indicators = [
            "clique" in text or "acesse" in text,
            "para mais detalhes" in text,
            len(citations) == 1 or len(citations) == 2,
        ]

        high_score = sum(high_sufficiency_indicators)
        low_score = sum(low_sufficiency_indicators)
        partial_score = sum(partial_indicators)

        if high_score >= 2 and low_score == 0:
            return SufficiencyLevel.TOTAL
        elif low_score >= 2:
            return SufficiencyLevel.INSUFICIENTE
        else:
            return SufficiencyLevel.PARCIAL

    def _classify_actionability(self, text: str) -> ActionabilityType:
        """Classifica o tipo de acionabilidade"""
        if not text:
            return ActionabilityType.INFORMATIVA

        transactional_score = 0
        for pattern in self.action_patterns["transacional"]:
            transactional_score += len(re.findall(pattern, text, re.IGNORECASE))

        return ActionabilityType.TRANSACIONAL if transactional_score > 0 else ActionabilityType.INFORMATIVA

    def _classify_trust_source(self, text: str, citations: List[Dict]) -> TrustSource:
        """Classifica o nível de confiança das fontes"""
        if not text:
            return TrustSource.GENERICA

        # Verificar se há citações de domínios confiáveis
        if citations:
            for citation in citations:
                domain = citation.get('domain', '').lower()
                if any(target in domain for target in self.target_domains):
                    return TrustSource.CITADA

        # Verificar padrões de citação no texto
        citation_score = 0
        for pattern in self.trust_patterns["citada"]:
            citation_score += len(re.findall(pattern, text, re.IGNORECASE))

        return TrustSource.CITADA if citation_score > 0 else TrustSource.GENERICA

    def _classify_brand_positioning(self, text: str, citations: List[Dict]) -> BrandPositioning:
        """Classifica o posicionamento da marca"""
        if not text and not citations:
            return BrandPositioning.AUSENTE

        # Verificar menções da marca no texto
        brand_mentions = 0
        competitor_mentions = 0

        for keyword in self.brand_keywords:
            brand_mentions += len(re.findall(rf'\b{re.escape(keyword.lower())}\b', text))

        # Palavras que indicam competição
        competitor_keywords = ["outras opções", "alternativas", "concorrentes", "também", "além"]
        for keyword in competitor_keywords:
            competitor_mentions += text.count(keyword)

        # Verificar citações para domínios alvo
        has_target_citation = False
        total_citations = len(citations)

        if citations:
            for citation in citations:
                domain = citation.get('domain', '').lower()
                if any(target in domain for target in self.target_domains):
                    has_target_citation = True
                    break

        # Lógica de classificação
        if brand_mentions == 0 and not has_target_citation:
            return BrandPositioning.AUSENTE
        elif competitor_mentions > 0 or total_citations > 3:
            return BrandPositioning.COMPETIDOR
        else:
            return BrandPositioning.PROTAGONISTA

    def _calculate_confidence(self, response_type: ResponseType, sufficiency_level: SufficiencyLevel,
                            actionability_type: ActionabilityType, trust_source: TrustSource,
                            brand_positioning: BrandPositioning, text: str) -> float:
        """Calcula a confiança geral da classificação"""
        # Fatores base de confiança
        base_confidence = 0.7

        # Ajustes por qualidade do texto
        text_length_factor = min(len(text) / 500, 1.0) * 0.1  # Máximo +0.1

        # Ajustes por classificações claras
        classification_clarity = 0.0

        # ResponseType: instrucionais e navegacionais são mais fáceis de detectar
        if response_type in [ResponseType.INSTRUCIONAL, ResponseType.NAVEGACIONAL]:
            classification_clarity += 0.1

        # BrandPositioning: ausente ou protagonista são mais claros
        if brand_positioning in [BrandPositioning.AUSENTE, BrandPositioning.PROTAGONISTA]:
            classification_clarity += 0.1

        # TrustSource: citada é mais clara
        if trust_source == TrustSource.CITADA:
            classification_clarity += 0.05

        final_confidence = min(base_confidence + text_length_factor + classification_clarity, 1.0)
        return round(final_confidence, 2)

    def _generate_reasoning(self, text: str, citations: List[Dict],
                          response_type: ResponseType, sufficiency_level: SufficiencyLevel,
                          actionability_type: ActionabilityType, trust_source: TrustSource,
                          brand_positioning: BrandPositioning) -> Dict[str, str]:
        """Gera justificativas para cada classificação"""
        reasoning = {}

        # Response Type
        type_reasons = {
            ResponseType.DIRETA: "Resposta objetiva e concisa",
            ResponseType.EXPLICATIVA: "Explica conceitos ou define termos",
            ResponseType.INSTRUCIONAL: "Apresenta passos ou instruções",
            ResponseType.COMPARATIVA: "Compara opções ou alternativas",
            ResponseType.CONSULTIVA: "Oferece recomendações ou opiniões",
            ResponseType.NAVEGACIONAL: "Direciona para links específicos"
        }
        reasoning["response_type"] = type_reasons.get(response_type, "Classificação automática")

        # Sufficiency Level
        sufficiency_reasons = {
            SufficiencyLevel.TOTAL: f"Resposta completa com {len(text)} caracteres e {len(citations)} citações",
            SufficiencyLevel.PARCIAL: "Resposta útil mas pode requerer informações adicionais",
            SufficiencyLevel.INSUFICIENTE: "Resposta genérica ou muito superficial"
        }
        reasoning["sufficiency_level"] = sufficiency_reasons.get(sufficiency_level, "Classificação automática")

        # Actionability Type
        reasoning["actionability_type"] = (
            "Contém chamadas para ação explícitas" if actionability_type == ActionabilityType.TRANSACIONAL
            else "Foco em informar sem direcionamento para ação"
        )

        # Trust Source
        reasoning["trust_source"] = (
            f"Inclui {len(citations)} citações de fontes" if trust_source == TrustSource.CITADA
            else "Baseado em conhecimento geral sem citações específicas"
        )

        # Brand Positioning
        brand_count = sum(1 for keyword in self.brand_keywords if keyword.lower() in text)
        positioning_reasons = {
            BrandPositioning.PROTAGONISTA: f"Marca mencionada {brand_count} vezes como solução principal",
            BrandPositioning.COMPETIDOR: f"Marca listada entre {len(citations)} opções",
            BrandPositioning.AUSENTE: "Marca não mencionada na resposta"
        }
        reasoning["brand_positioning"] = positioning_reasons.get(brand_positioning, "Classificação automática")

        return reasoning

def classify_run_response(run_id: str, response_text: str, citations: List[Dict] = None,
                         prompt_text: str = None, target_domains: List[str] = None,
                         brand_keywords: List[str] = None) -> ClassificationResult:
    """
    Função de conveniência para classificar a resposta de uma run

    Args:
        run_id: ID da run sendo classificada
        response_text: Texto da resposta
        citations: Lista de citações
        prompt_text: Texto do prompt original
        target_domains: Domínios alvo da empresa
        brand_keywords: Palavras-chave da marca

    Returns:
        ClassificationResult
    """
    classifier = ResponseClassifier(
        target_domains=target_domains or [],
        brand_keywords=brand_keywords or []
    )

    return classifier.classify_response(
        response_text=response_text,
        citations=citations,
        prompt_text=prompt_text
    )