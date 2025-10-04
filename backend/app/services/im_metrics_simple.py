"""
Versão simplificada das métricas IM-SEO e IM-SEOIA sem dependências externas.
Implementa cálculos básicos usando heurísticas e dados já disponíveis.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import re


class SimpleIMMetrics:
    """Calculadora de métricas IM-SEO e IM-SEOIA simplificada."""

    @staticmethod
    def calculate_all(
        run_data: Dict,
        citations: List[Dict],
        response_text: Optional[str] = None,
        serp_data: Optional[Dict] = None,
        project_domains: Optional[List[str]] = None,
        target_url: Optional[str] = None
    ) -> Dict:
        """
        Calcula todas as métricas IM de forma simplificada.
        
        Args:
            run_data: Dicionário com dados da run (amr_flag, dcr_flag, zcrs, etc.)
            citations: Lista de citações extraídas
            response_text: Texto completo da resposta (opcional)
            serp_data: Dados do SerpAPI (opcional)
            project_domains: Lista de domínios do projeto (opcional)
            target_url: URL alvo para análise de Core Web Vitals (opcional)
        
        Returns:
            Dicionário com todas as métricas calculadas
        """
        
        # Analisar dados do SerpAPI se disponíveis
        serp_metrics = {}
        if serp_data:
            try:
                from app.services.serp_analyzer import SerpAnalyzer
                serp_metrics = SerpAnalyzer.analyze_serp_data(serp_data, project_domains or [])
            except Exception as e:
                print(f"[IM_METRICS] Erro ao analisar SerpAPI: {e}")
                serp_metrics = {}
        
        # Buscar Core Web Vitals reais se URL disponível
        cwv_metrics = {}
        if target_url:
            print(f"[IM_METRICS] Buscando Core Web Vitals para URL: {target_url}")
            try:
                from app.services.pagespeed_analyzer import PageSpeedAnalyzer
                import asyncio
                # Executar análise assíncrona (compatível com Celery)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                cwv_metrics = loop.run_until_complete(PageSpeedAnalyzer.analyze_url(target_url))
                print(f"[IM_METRICS] PageSpeed OK: CWV={cwv_metrics.get('core_web_vitals_score')}")
            except Exception as e:
                print(f"[IM_METRICS] Erro ao buscar Core Web Vitals: {e}")
                import traceback
                traceback.print_exc()
                cwv_metrics = {}
        else:
            print(f"[IM_METRICS] Sem URL alvo - Core Web Vitals será None")
        
        # 1. IM-SEO (usando dados já existentes + SerpAPI)
        autoridade = (float(run_data.get("amr_flag") or 0) + float(run_data.get("dcr_flag") or 0)) / 2 * 100
        
        # Usar Core Web Vitals real se disponível, senão None
        lighthouse = cwv_metrics.get("core_web_vitals_score")
        
        # Usar share_of_voice do SERP se disponível (baseado em posição orgânica)
        # Senão usar serp_features_presence ou ZCRS como fallback
        share_trafego = (
            serp_metrics.get("share_of_voice") or 
            serp_metrics.get("serp_features_presence") or 
            run_data.get("zcrs") or 
            0
        )
        engajamento = run_data.get("zcrs") or 0

        # IM-SEO com peso duplo para share de tráfego (conforme documento)
        # Se lighthouse não disponível, ajusta o cálculo para não distorcer
        if lighthouse is not None:
            # Com Core Web Vitals: fórmula completa
            im_seo = (autoridade + lighthouse + (share_trafego * 2) + engajamento) / 5
        else:
            # Sem Core Web Vitals: ajusta pesos (remove lighthouse do denominador)
            im_seo = (autoridade + (share_trafego * 2) + engajamento) / 4

        # 2. E-E-A-T (análise básica)
        eeat = SimpleIMMetrics._calculate_eeat_simple(response_text or "")

        # 3. IA-Ready Blocks
        ia_ready = SimpleIMMetrics._detect_ia_blocks(response_text or "")

        # 4. IRZC (simulado baseado em citações)
        irzc = SimpleIMMetrics._calculate_irzc_simple(len(citations))

        # 5. Entidades (análise básica)
        entities = SimpleIMMetrics._detect_entities_simple(response_text or "")

        # 6. IM-SEOIA (composição com dados reais do SerpAPI)
        ia_serp_score = serp_metrics.get("ia_serp_presence_score", 50.0)
        longtail_score = serp_metrics.get("longtail_coverage_score", 50.0)
        schema_score = serp_metrics.get("schema_coverage_score", 50.0)
        
        # IM-SEOIA ajustado se lighthouse não disponível
        if lighthouse is not None:
            # Com Core Web Vitals: fórmula completa
            im_seoia = (
                lighthouse * 0.10 +
                share_trafego * 0.15 +
                ia_serp_score * 0.15 +
                longtail_score * 0.15 +
                eeat["overall"] * 0.15 +
                entities["connection_score"] * 0.10 +
                schema_score * 0.10 +
                ia_ready["score"] * 0.10
            )
        else:
            # Sem Core Web Vitals: redistribui o peso (10%) entre outras métricas
            im_seoia = (
                share_trafego * 0.17 +  # +2%
                ia_serp_score * 0.17 +  # +2%
                longtail_score * 0.17 +  # +2%
                eeat["overall"] * 0.17 +  # +2%
                entities["connection_score"] * 0.11 +  # +1%
                schema_score * 0.11 +  # +1%
                ia_ready["score"] * 0.10
            )

        return {
            "im_seo_score": round(im_seo, 2),
            "im_seoia_score": round(im_seoia, 2),
            "core_web_vitals_score": lighthouse,
            "lcp_score": cwv_metrics.get("lcp_score"),
            "fid_score": cwv_metrics.get("fid_score"),
            "cls_score": cwv_metrics.get("cls_score"),
            "share_of_voice_serp": share_trafego,
            "organic_position": serp_metrics.get("organic_position"),
            "competitors_top10": serp_metrics.get("competitors_top10"),
            "serp_features_presence": serp_metrics.get("serp_features_presence"),
            "ia_resources_detected": serp_metrics.get("ia_resources_detected"),
            "ia_serp_presence_score": ia_serp_score,
            "longtail_terms_top10": serp_metrics.get("longtail_terms_top10"),
            "longtail_terms_top20": serp_metrics.get("longtail_terms_top20"),
            "longtail_coverage_score": longtail_score,
            "schema_types_detected": serp_metrics.get("schema_types_detected"),
            "schema_coverage_score": schema_score,
            "eeat": eeat,
            "ia_ready": ia_ready,
            "irzc": irzc,
            "entities": entities,
            "serp_paa_items": serp_metrics.get("paa_items"),
            "serp_knowledge_panel": serp_metrics.get("knowledge_panel"),
            "serp_ai_overview": serp_metrics.get("ai_overview"),
            "serp_featured_snippet": serp_metrics.get("featured_snippet"),
            "serp_metrics": serp_metrics,
        }

    @staticmethod
    def _calculate_eeat_simple(text: str) -> Dict:
        """
        E-E-A-T baseado em heurísticas simples.
        
        Critérios:
        - Expertise: termos técnicos, números, dados estatísticos
        - Experience: uso de primeira pessoa, relatos práticos
        - Authoritativeness: citações de autoridade, links externos
        - Trustworthiness: transparência, fontes verificáveis
        """
        if not text:
            return {
                "overall": 0.0,
                "expertise": 0.0,
                "experience": 0.0,
                "authoritativeness": 0.0,
                "trustworthiness": 0.0,
            }

        # Expertise: termos técnicos, números, dados
        # Conta percentuais, decimais, siglas
        expertise_indicators = len(re.findall(r'\d+%|\d+\.\d+|[A-Z]{2,}', text))
        expertise = min(100, expertise_indicators * 5)

        # Experience: primeira pessoa
        experience_patterns = r'\b(eu|meu|minha|nosso|nossa|meus|minhas|nossos|nossas)\b'
        has_first_person = bool(re.search(experience_patterns, text, re.IGNORECASE))
        experience = 70.0 if has_first_person else 40.0

        # Authoritativeness: citações, fontes, links
        authority_indicators = text.count('http') + text.count('fonte') * 2 + text.count('segundo') * 1.5
        authoritativeness = min(100, authority_indicators * 10)

        # Trustworthiness: linguagem clara, tamanho adequado
        trustworthiness = 80.0 if len(text) > 200 else 50.0
        # Penaliza se muito curto
        if len(text) < 50:
            trustworthiness = 30.0

        overall = (expertise + experience + authoritativeness + trustworthiness) / 4

        return {
            "overall": round(overall, 2),
            "expertise": round(expertise, 2),
            "experience": round(experience, 2),
            "authoritativeness": round(authoritativeness, 2),
            "trustworthiness": round(trustworthiness, 2),
        }

    @staticmethod
    def _detect_ia_blocks(text: str) -> Dict:
        """
        Detecta blocos estruturados IA-ready no conteúdo.
        
        Blocos detectados:
        - Listas (bullets, numeradas)
        - FAQs (perguntas e respostas)
        - Tabelas (markdown ou estruturadas)
        - Passo-a-passo (instruções sequenciais)
        """
        if not text:
            return {
                "score": 0.0,
                "blocks_count": 0,
                "has_lists": False,
                "has_faqs": False,
                "has_tables": False,
                "has_step_by_step": False,
            }

        # Listas: bullets ou numeradas
        has_lists = bool(re.search(r'(?:^|\n)\s*[-*•\d+\.]\s+', text, re.MULTILINE))

        # FAQs: palavras-chave relacionadas
        faq_patterns = r'\b(?:pergunta|resposta|faq|dúvida|questão|como|por que|o que é)\b'
        has_faqs = bool(re.search(faq_patterns, text, re.IGNORECASE))

        # Tabelas: markdown ou estruturadas
        has_tables = bool(re.search(r'\|.*\|', text))

        # Passo-a-passo: instruções sequenciais
        step_patterns = r'(?:passo|etapa|primeiro|segundo|terceiro|quarto|quinto|\d+\)|\d+\.)'
        has_step_by_step = bool(re.search(step_patterns, text, re.IGNORECASE))

        blocks_count = sum([has_lists, has_faqs, has_tables, has_step_by_step])
        score = (blocks_count / 4) * 100

        return {
            "score": round(score, 2),
            "blocks_count": blocks_count,
            "has_lists": has_lists,
            "has_faqs": has_faqs,
            "has_tables": has_tables,
            "has_step_by_step": has_step_by_step,
        }

    @staticmethod
    def _calculate_irzc_simple(citations_count: int) -> Dict:
        """
        IRZC simplificado baseado em número de citações.
        
        Lógica:
        - Quanto mais citações, menor o risco (mais autoridade)
        - Score alto = alto risco de zero-click
        - Score baixo = baixo risco (boas chances de CTR)
        """
        # Quanto mais citações, menor o risco
        # 0 citações = 100 (risco máximo)
        # 10+ citações = 0 (risco mínimo)
        score = max(0, 100 - (citations_count * 10))

        # CTR esperado baseado em posição simulada
        # Como não temos posição real, usamos proxy baseado em citações
        if citations_count >= 5:
            ctr_expected = 15.0  # Top 3
        elif citations_count >= 3:
            ctr_expected = 8.0   # Top 5
        elif citations_count >= 1:
            ctr_expected = 4.0   # Top 10
        else:
            ctr_expected = 1.0   # Fora do top 10

        risk_level = "alto" if score > 70 else "médio" if score > 40 else "baixo"

        return {
            "score": round(score, 2),
            "ctr_expected": ctr_expected,
            "risk_level": risk_level,
        }

    @staticmethod
    def _detect_entities_simple(text: str) -> Dict:
        """
        Detecção simplificada de entidades (sem Google NLP).
        
        Detecta:
        - Nomes próprios (palavras capitalizadas)
        - Organizações (padrões comuns)
        - Localizações (cidades, países)
        """
        if not text:
            return {
                "detected": 0,
                "relevance_score": 0.0,
                "connection_score": 0.0,
            }

        # Detectar palavras capitalizadas (possíveis entidades)
        # Ignora início de frase
        sentences = text.split('.')
        entities = []
        
        for sentence in sentences:
            # Pega palavras capitalizadas que não estão no início
            words = sentence.split()
            for i, word in enumerate(words):
                if i > 0 and word and word[0].isupper() and len(word) > 2:
                    # Remove pontuação
                    clean_word = re.sub(r'[^\w\s]', '', word)
                    if clean_word and len(clean_word) > 2:
                        entities.append(clean_word)

        # Contar entidades únicas
        unique_entities = set(entities)
        detected = len(unique_entities)

        # Relevância baseada em frequência
        if detected > 0:
            avg_mentions = len(entities) / detected
            relevance_score = min(1.0, avg_mentions / 5)  # Normaliza para 0-1
        else:
            relevance_score = 0.0

        # Connection score (0-100)
        connection_score = min(100, detected * 10)

        return {
            "detected": detected,
            "relevance_score": round(relevance_score, 2),
            "connection_score": round(connection_score, 2),
        }

    @staticmethod
    def calculate_im_seo(
        amr_flag: bool,
        dcr_flag: bool,
        zcrs: float,
        core_web_vitals_score: float
    ) -> float:
        """
        Calcula IM-SEO isoladamente.
        
        Fórmula: (Autoridade + Lighthouse + Share de Tráfego + Engajamento) / 4
        """
        autoridade = (float(amr_flag or 0) + float(dcr_flag or 0)) / 2 * 100
        lighthouse = core_web_vitals_score or 75.0
        share_trafego = zcrs or 0
        engajamento = zcrs or 0

        im_seo = (autoridade + lighthouse + share_trafego + engajamento) / 4
        return round(im_seo, 2)

    @staticmethod
    def calculate_im_seoia(
        core_web_vitals_score: float,
        share_of_voice: float,
        eeat_score: float,
        ia_ready_score: float,
        entity_connection_score: float,
        ia_serp_score: float = 50.0,
        long_tail_score: float = 50.0,
        schema_score: float = 50.0,
    ) -> float:
        """
        Calcula IM-SEOIA isoladamente.
        
        Média ponderada de 8 sub-índices.
        """
        weights = {
            "performance": 0.10,
            "traffic": 0.15,
            "ia_serp": 0.15,
            "long_tail": 0.15,
            "eeat": 0.15,
            "entities": 0.10,
            "schema": 0.10,
            "ia_ready": 0.10,
        }

        scores = {
            "performance": core_web_vitals_score or 0,
            "traffic": share_of_voice or 0,
            "ia_serp": ia_serp_score,
            "long_tail": long_tail_score,
            "eeat": eeat_score or 0,
            "entities": entity_connection_score or 0,
            "schema": schema_score,
            "ia_ready": ia_ready_score or 0,
        }

        weighted_sum = sum(scores[k] * weights[k] for k in weights)
        total_weight = sum(weights.values())

        im_seoia = (weighted_sum / total_weight) if total_weight > 0 else 0
        return round(im_seoia, 2)
