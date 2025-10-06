"""
SerpAPI Analyzer - Extrai métricas avançadas de dados do Google SERP.

Este módulo analisa os dados retornados pelo SerpAPI para calcular:
- SERP Features Presence (Featured Snippet, Knowledge Graph, PAA, etc.)
- Posição Orgânica e CTR esperado
- Long-tail Coverage (Related Questions, Related Searches)
- Schema Detection (Rich Snippets)
- Competitors Analysis
"""

from typing import Dict, List, Any, Optional, Tuple


class SerpAnalyzer:
    """Analisador de dados SerpAPI para métricas IM-SEO/IM-SEOIA."""
    
    # Sistrix CTR Curve - CTR esperado por posição orgânica
    SISTRIX_CTR = {
        1: 28.5, 2: 15.7, 3: 11.0, 4: 8.0, 5: 7.2,
        6: 5.1, 7: 4.0, 8: 3.2, 9: 2.8, 10: 2.5,
        11: 2.3, 12: 2.1, 13: 1.9, 14: 1.7, 15: 1.5,
        16: 1.4, 17: 1.3, 18: 1.2, 19: 1.1, 20: 1.0
    }
    
    @staticmethod
    def analyze_serp_data(raw_data: Dict[str, Any], project_domains: List[str] = None) -> Dict[str, Any]:
        """
        Analisa dados do SerpAPI e retorna métricas calculadas.
        
        Args:
            raw_data: Dados brutos do SerpAPI (evidence.parsed_json.raw)
            project_domains: Lista de domínios do projeto (para detectar posição)
            
        Returns:
            Dict com métricas calculadas
        """
        if not raw_data:
            return SerpAnalyzer._empty_metrics()
        
        # Acessar dados do SerpAPI na estrutura correta
        # evidence.parsed_json.raw.serpapi_search contém os dados SERP
        serpapi_data = raw_data.get('raw', {}).get('serpapi_search', {})
        
        # Detectar SERP Features
        serp_features = SerpAnalyzer._detect_serp_features(raw_data, serpapi_data)

        # Analisar posição orgânica
        organic_analysis = SerpAnalyzer._analyze_organic_position(
            serpapi_data, project_domains or []
        )
        # Analisar long-tail
        longtail_analysis = SerpAnalyzer._analyze_longtail(serpapi_data)
        
        # Detectar schemas
        schema_analysis = SerpAnalyzer._detect_schemas(serpapi_data)
        
        # Calcular score agregado de SERP Features Presence
        serp_features_score = SerpAnalyzer._calculate_serp_features_score(serp_features)

        # Calcular Share of Voice baseado em posição orgânica
        share_of_voice = SerpAnalyzer._calculate_share_of_voice(
            organic_analysis["position"],
            organic_analysis["competitors_top10"]
        )

        paa_items = SerpAnalyzer._extract_paa_items(serpapi_data)
        knowledge_panel = SerpAnalyzer._extract_knowledge_panel(serpapi_data)
        ai_overview = SerpAnalyzer._extract_ai_overview(raw_data)
        featured_snippet = SerpAnalyzer._extract_featured_snippet(serpapi_data)

        return {
            "serp_features": serp_features,
            "serp_features_presence": serp_features_score,
            "organic_position": organic_analysis["position"],
            "organic_url": organic_analysis["url"],
            "ctr_expected": organic_analysis["ctr_expected"],
            "share_of_voice": share_of_voice,
            "competitors_top10": organic_analysis["competitors_top10"],
            "longtail_terms_top10": longtail_analysis["terms_top10"],
            "longtail_terms_top20": longtail_analysis["terms_top20"],
            "longtail_coverage_score": longtail_analysis["coverage_score"],
            "schema_types_detected": schema_analysis["types"],
            "schema_coverage_score": schema_analysis["coverage_score"],
            "ia_resources_detected": serp_features.get("ai_overview", 0) + serp_features.get("knowledge_graph", 0),
            "ia_serp_presence_score": SerpAnalyzer._calculate_ia_presence_score(serp_features),
            "paa_items": paa_items,
            "knowledge_panel": knowledge_panel,
            "ai_overview": ai_overview,
            "featured_snippet": featured_snippet,
        }
    
    @staticmethod
    def _detect_serp_features(raw_data: Dict, serpapi_data: Dict) -> Dict[str, int]:
        """
        Detecta presença de SERP Features.
        
        Returns:
            Dict com flags (0 ou 1) para cada feature
        """
        # AI Overview está em raw.serpapi_ai
        features = {
            "ai_overview": 1 if raw_data.get("raw", {}).get("serpapi_ai") else 0,
            "featured_snippet": 1 if "answer_box" in serpapi_data else 0,
            "knowledge_graph": 1 if "knowledge_graph" in serpapi_data else 0,
            "people_also_ask": 1 if serpapi_data.get("related_questions") else 0,
            "local_pack": 1 if "local_results" in serpapi_data else 0,
            "video_carousel": 1 if "inline_videos" in serpapi_data else 0,
            "image_pack": 1 if "inline_images" in serpapi_data else 0,
            "shopping_results": 1 if "shopping_results" in serpapi_data else 0,
            "top_stories": 1 if "top_stories" in serpapi_data else 0,
            "related_searches": 1 if "related_searches" in serpapi_data else 0
        }
        
        return features
    
    @staticmethod
    def _analyze_organic_position(serpapi_data: Dict, project_domains: List[str]) -> Dict[str, Any]:
        """
        Analisa posição orgânica do projeto nos resultados.
        
        Returns:
            Dict com position, url, ctr_expected, competitors_top10
        """
        organic_results = serpapi_data.get("organic_results", [])
        
        if not organic_results:
            return {
                "position": None,
                "url": None,
                "ctr_expected": 0.0,
                "competitors_top10": 0
            }
        
        # Normalizar domínios do projeto
        normalized_domains = [d.lower().replace("www.", "") for d in project_domains]
        
        # Procurar posição do projeto
        our_position = None
        our_url = None
        
        for idx, result in enumerate(organic_results, start=1):
            link = result.get("link", "")
            try:
                from urllib.parse import urlparse
                domain = urlparse(link).netloc.lower().replace("www.", "")
                
                if any(proj_domain in domain for proj_domain in normalized_domains):
                    our_position = idx
                    our_url = link
                    break
            except:
                continue
        
        # Calcular CTR esperado
        ctr_expected = SerpAnalyzer.SISTRIX_CTR.get(our_position, 0.5) if our_position else 0.0
        
        # Contar competidores no top 10
        competitors_top10 = min(len(organic_results), 10)
        if our_position and our_position <= 10:
            competitors_top10 -= 1  # Excluir nós mesmos
        
        return {
            "position": our_position,
            "url": our_url,
            "ctr_expected": ctr_expected,
            "competitors_top10": competitors_top10
        }
    
    @staticmethod
    def _analyze_longtail(serpapi_data: Dict) -> Dict[str, Any]:
        """
        Analisa cobertura de long-tail (PAA, Related Searches).
        
        Returns:
            Dict com terms_top10, terms_top20, coverage_score
        """
        # People Also Ask
        paa_questions = serpapi_data.get("related_questions", [])
        paa_count = len(paa_questions)
        
        # Related Searches
        related_searches = serpapi_data.get("related_searches", [])
        related_count = len(related_searches)
        
        # Total de termos long-tail detectados
        total_terms = paa_count + related_count
        
        # Classificar em top10 e top20
        terms_top10 = min(total_terms, 10)
        terms_top20 = min(total_terms, 20)
        
        # Calcular coverage score (0-100)
        # Ideal: 10+ PAA + 8+ Related Searches = 18 termos
        ideal_count = 18
        coverage_score = min(100, (total_terms / ideal_count) * 100)
        
        return {
            "terms_top10": terms_top10,
            "terms_top20": terms_top20,
            "coverage_score": round(coverage_score, 2)
        }
    
    @staticmethod
    def _detect_schemas(serpapi_data: Dict) -> Dict[str, Any]:
        """
        Detecta schemas/rich snippets nos resultados orgânicos.
        
        Returns:
            Dict com types (lista de schemas) e coverage_score
        """
        organic_results = serpapi_data.get("organic_results", [])
        
        detected_schemas = set()
        results_with_schema = 0
        
        for result in organic_results:
            rich_snippet = result.get("rich_snippet", {})
            
            if rich_snippet:
                results_with_schema += 1
                
                # Detectar tipos de schema
                top = rich_snippet.get("top", {})
                detected_extensions = top.get("detected_extensions", {})
                
                if "rating" in detected_extensions:
                    detected_schemas.add("rating")
                if "reviews" in detected_extensions or "review_count" in detected_extensions:
                    detected_schemas.add("reviews")
                if "price" in detected_extensions:
                    detected_schemas.add("price")
                
                # Outros tipos comuns
                if "extensions" in top:
                    detected_schemas.add("extensions")
        
        # Answer box pode indicar FAQ/HowTo schema
        if "answer_box" in serpapi_data:
            answer_type = serpapi_data["answer_box"].get("type", "")
            if "faq" in answer_type.lower():
                detected_schemas.add("faq")
            if "howto" in answer_type.lower() or "how_to" in answer_type.lower():
                detected_schemas.add("howto")
        
        # Calcular coverage score
        total_results = len(organic_results)
        if total_results > 0:
            coverage_score = (results_with_schema / total_results) * 100
        else:
            coverage_score = 0.0
        
        return {
            "types": ",".join(sorted(detected_schemas)) if detected_schemas else None,
            "coverage_score": round(coverage_score, 2)
        }
    
    @staticmethod
    def _calculate_serp_features_score(features: Dict[str, int]) -> float:
        """
        Calcula score de presença de SERP Features (0-100).
        
        Representa quantos tipos de features estão presentes na SERP.
        Mais features = SERP mais rica = score maior.
        """
        # Contar quantos TIPOS de features estão presentes (valor > 0)
        features_present = sum(1 for count in features.values() if count > 0)
        max_features = len(features)  # Total de tipos possíveis (10)
        
        if max_features == 0:
            return 0.0
        
        # Percentual de tipos de features presentes
        score = (features_present / max_features) * 100
        
        return round(score, 2)
    
    @staticmethod
    def _calculate_share_of_voice(position: Optional[int], competitors: int) -> float:
        """
        Calcula Share of Voice baseado na posição orgânica (0-100).
        
        Quanto melhor a posição, maior o share of voice.
        Leva em conta o número de competidores.
        """
        if position is None:
            return 0.0
        
        # CTR esperado pela posição (Sistrix)
        ctr = SerpAnalyzer.SISTRIX_CTR.get(position, 0.5)
        
        # Normalizar para 0-100
        # Posição 1 = ~28.5% CTR = score alto
        # Posição 10 = ~2.5% CTR = score baixo
        base_score = min(100, (ctr / 28.5) * 100)
        
        # Penalizar se há muitos competidores
        if competitors > 5:
            competition_penalty = min(20, (competitors - 5) * 2)
            base_score = max(0, base_score - competition_penalty)
        
        return round(base_score, 2)
    
    @staticmethod
    def _calculate_ia_presence_score(features: Dict[str, int]) -> float:
        """
        Calcula score de presença de recursos de IA na SERP (0-100).
        
        AI Overview + Knowledge Graph = recursos de IA
        """
        ai_features = features.get("ai_overview", 0) + features.get("knowledge_graph", 0)

        # Se tem AI Overview ou Knowledge Graph, score é alto
        if ai_features > 0:
            return 100.0

        # Se tem Featured Snippet, score médio
        if features.get("featured_snippet", 0):
            return 50.0

        return 0.0

    @staticmethod
    def _extract_paa_items(serpapi_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for idx, entry in enumerate(serpapi_data.get("related_questions", []) or [], start=1):
            question = entry.get("question")
            if not question:
                continue
            items.append(
                {
                    "position": idx,
                    "question": question,
                    "snippet": entry.get("answer") or entry.get("snippet"),
                    "link": entry.get("link"),
                    "title": entry.get("title"),
                }
            )
        return items[:20]

    @staticmethod
    def _extract_knowledge_panel(serpapi_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        knowledge = serpapi_data.get("knowledge_graph") or {}
        if not knowledge:
            return None

        return {
            "title": knowledge.get("title") or knowledge.get("name"),
            "type": knowledge.get("type"),
            "website": knowledge.get("website"),
            "description": knowledge.get("description") or knowledge.get("summary"),
            "source": knowledge.get("source") or knowledge.get("source_link"),
            "attributes": knowledge.get("attributes") or knowledge.get("infobox"),
        }

    @staticmethod
    def _extract_ai_overview(raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # AI Overview está em raw.serpapi_ai
        ai_data = raw_data.get("raw", {}).get("serpapi_ai") or {}
        if not ai_data:
            return None

        text_blocks = ai_data.get("text_blocks") or []
        references = ai_data.get("references") or []
        follow_up = ai_data.get("follow_up_questions") or []

        summary_parts: List[str] = []
        for block in text_blocks[:10]:
            snippet = block.get("snippet")
            if snippet:
                summary_parts.append(snippet)
        summary_text = " ".join(summary_parts)[:2000] if summary_parts else None

        clean_refs = [
            {
                "title": ref.get("title"),
                "url": ref.get("link") or ref.get("url"),
                "domain": ref.get("domain") or ref.get("source"),
            }
            for ref in references[:10]
            if ref.get("title") or ref.get("link") or ref.get("url")
        ]

        return {
            "summary": summary_text,
            "text_blocks": text_blocks[:10],
            "references": clean_refs,
            "follow_up_questions": follow_up[:10] if isinstance(follow_up, list) else follow_up,
        }

    @staticmethod
    def _extract_featured_snippet(serpapi_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        snippet = serpapi_data.get("answer_box") or {}
        if not snippet:
            return None
        return {
            "title": snippet.get("title"),
            "answer": snippet.get("answer"),
            "snippet": snippet.get("snippet"),
            "link": snippet.get("link"),
            "type": snippet.get("type"),
        }
    
    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Retorna métricas vazias quando não há dados SerpAPI."""
        return {
            "serp_features": {},
            "serp_features_presence": None,
            "organic_position": None,
            "organic_url": None,
            "ctr_expected": None,
            "competitors_top10": None,
            "longtail_terms_top10": None,
            "longtail_terms_top20": None,
            "longtail_coverage_score": None,
            "schema_types_detected": None,
            "schema_coverage_score": None,
            "ia_resources_detected": None,
            "ia_serp_presence_score": None,
            "paa_items": [],
            "knowledge_panel": None,
            "ai_overview": None,
            "featured_snippet": None,
        }


def analyze_serp_for_run(evidence_data: Dict[str, Any], project_domains: List[str] = None) -> Dict[str, Any]:
    """
    Helper function para analisar dados SERP de uma run.
    
    Args:
        evidence_data: Dados do evidence (parsed_json)
        project_domains: Lista de domínios do projeto
        
    Returns:
        Dict com métricas calculadas
    """
    if not evidence_data:
        return SerpAnalyzer._empty_metrics()
    
    raw_data = evidence_data.get("raw", {})
    
    return SerpAnalyzer.analyze_serp_data(raw_data, project_domains)
