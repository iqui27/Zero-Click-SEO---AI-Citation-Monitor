"""
Funnel Stage Classifier - Classifica perguntas em etapas do funil de marketing.

Etapas:
- Reconhecimento: Usuário está descobrindo o problema/necessidade
- Consideração: Usuário está avaliando opções e comparando
- Conversão: Usuário está pronto para tomar ação
"""

from typing import Optional


class FunnelClassifier:
    """Classifica perguntas em etapas do funil de marketing."""
    
    # Palavras-chave por etapa do funil
    RECONHECIMENTO_KEYWORDS = [
        "o que é", "o que são", "como funciona", "quais são", "tipos de",
        "para que serve", "qual a diferença", "diferença entre",
        "significado", "definição", "conceito", "entenda",
        "saiba mais", "conheça", "descubra", "aprenda"
    ]
    
    CONSIDERACAO_KEYWORDS = [
        "melhor", "melhores", "comparar", "comparação", "vantagens",
        "desvantagens", "prós e contras", "qual escolher", "vale a pena",
        "ou", "versus", "vs", "diferença", "opções",
        "alternativas", "recomendação", "indicação", "review",
        "avaliação", "ranking", "top", "lista"
    ]
    
    CONVERSAO_KEYWORDS = [
        "como abrir", "como fazer", "como criar", "passo a passo",
        "cadastrar", "cadastro", "contratar", "contratação",
        "solicitar", "pedido", "comprar", "adquirir",
        "ativar", "habilitar", "configurar", "instalar",
        "quanto custa", "preço", "valor", "tarifa",
        "gratuito", "grátis", "sem custo", "taxa"
    ]
    
    @staticmethod
    def classify(prompt_text: str, response_text: Optional[str] = None) -> str:
        """
        Classifica a etapa do funil baseado no texto da pergunta e resposta.
        
        Args:
            prompt_text: Texto da pergunta
            response_text: Texto da resposta (opcional, usado para desempate)
            
        Returns:
            "reconhecimento" | "consideracao" | "conversao" | "nao_classificado"
        """
        if not prompt_text:
            return "nao_classificado"
        
        # Normalizar texto
        text = prompt_text.lower().strip()
        
        # Contar matches por categoria
        reconhecimento_score = sum(
            1 for keyword in FunnelClassifier.RECONHECIMENTO_KEYWORDS
            if keyword in text
        )
        
        consideracao_score = sum(
            1 for keyword in FunnelClassifier.CONSIDERACAO_KEYWORDS
            if keyword in text
        )
        
        conversao_score = sum(
            1 for keyword in FunnelClassifier.CONVERSAO_KEYWORDS
            if keyword in text
        )
        
        # Se houver empate, usar resposta como desempate
        if response_text and reconhecimento_score == consideracao_score == conversao_score:
            response_lower = response_text.lower()
            
            # Respostas longas e explicativas geralmente são reconhecimento
            if len(response_text) > 1000 and any(
                term in response_lower for term in ["conceito", "definição", "significa"]
            ):
                return "reconhecimento"
            
            # Respostas com comparações são consideração
            if any(term in response_lower for term in ["melhor", "comparar", "vantagem"]):
                return "consideracao"
            
            # Respostas com instruções são conversão
            if any(term in response_lower for term in ["passo", "cadastr", "abrir", "criar"]):
                return "conversao"
        
        # Retornar categoria com maior score
        max_score = max(reconhecimento_score, consideracao_score, conversao_score)
        
        if max_score == 0:
            return "nao_classificado"
        
        if reconhecimento_score == max_score:
            return "reconhecimento"
        elif conversao_score == max_score:
            return "conversao"
        else:
            return "consideracao"
    
    @staticmethod
    def classify_with_confidence(
        prompt_text: str,
        response_text: Optional[str] = None
    ) -> tuple[str, float]:
        """
        Classifica e retorna confiança da classificação.
        
        Returns:
            (stage, confidence) onde confidence é 0.0-1.0
        """
        stage = FunnelClassifier.classify(prompt_text, response_text)
        
        if stage == "nao_classificado":
            return (stage, 0.0)
        
        text = prompt_text.lower()
        
        # Calcular confiança baseado em quantos keywords matcharam
        if stage == "reconhecimento":
            keywords = FunnelClassifier.RECONHECIMENTO_KEYWORDS
        elif stage == "consideracao":
            keywords = FunnelClassifier.CONSIDERACAO_KEYWORDS
        else:  # conversao
            keywords = FunnelClassifier.CONVERSAO_KEYWORDS
        
        matches = sum(1 for keyword in keywords if keyword in text)
        confidence = min(1.0, matches / 3.0)  # 3+ matches = 100% confiança
        
        return (stage, confidence)
