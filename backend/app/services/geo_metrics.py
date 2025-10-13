"""
Módulo para cálculo de métricas GEO (Generative Engine Optimization).

Métricas implementadas:
- Brand Presence: menções, posição, densidade, prominence
- Citation Quality: qualidade e posição de citações
- Competitive Intelligence: share of voice, ratios
- Engagement: triggers conversacionais
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
from difflib import SequenceMatcher


# Taxonomia de Produtos (Banco do Brasil)
PRODUCT_TAXONOMY = {
    "cartoes": [
        "cartão", "card", "cartões", "crédito rotativo", "débito", "mastercard", "visa",
        "ourocard", "elo", "bandeira", "anuidade", "limite de crédito", "fatura"
    ],
    "credito": [
        "empréstimo", "financiamento", "crédito pessoal", "consignado", "cheque especial",
        "refinanciamento", "antecipação", "crédito imobiliário", "crédito veículo",
        "parcela", "juros", "taxa de juros", "cet"
    ],
    "investimentos": [
        "investir", "investimento", "aplicação", "renda fixa", "renda variável",
        "poupança", "cdb", "lci", "lca", "tesouro direto", "ações", "fundos",
        "previdência", "rentabilidade", "liquidez"
    ],
    "conta": [
        "conta corrente", "conta poupança", "conta digital", "abertura de conta",
        "tarifa", "manutenção", "saldo", "extrato", "transferência", "pix",
        "ted", "doc", "pacote de serviços"
    ],
    "seguros": [
        "seguro", "proteção", "cobertura", "sinistro", "apólice", "prêmio",
        "seguro de vida", "seguro auto", "seguro residencial", "seguro viagem",
        "assistência", "indenização"
    ],
    "empresarial": [
        "mei", "pj", "pessoa jurídica", "cnpj", "empresa", "empresarial",
        "capital de giro", "antecipação de recebíveis", "maquininha", "pos",
        "conta empresarial", "folha de pagamento"
    ],
    "digital": [
        "app", "aplicativo", "internet banking", "mobile", "digital",
        "online", "token", "senha", "biometria", "notificação"
    ],
}


def normalize_brand_name(name: str) -> str:
    """Normaliza nome de marca para busca case-insensitive."""
    return name.strip().lower()


def fuzzy_match(text: str, pattern: str, threshold: float = 0.90) -> bool:
    """Verifica se texto tem similaridade >= threshold com pattern."""
    ratio = SequenceMatcher(None, text.lower(), pattern.lower()).ratio()
    return ratio >= threshold


def classify_product_category(response_text: str, project_name: str = "") -> Optional[str]:
    """
    Classifica a categoria de produto mencionada na resposta.
    
    Usa keyword matching com a taxonomia definida.
    Para classificação mais precisa, pode-se usar Gemini (futuro).
    
    Args:
        response_text: Texto completo da resposta
        project_name: Nome do projeto (opcional, para contexto)
    
    Returns:
        Categoria principal detectada ou None
    """
    if not response_text:
        return None
    
    text_lower = response_text.lower()
    
    # Contar matches por categoria
    category_scores: Dict[str, int] = {}
    
    for category, keywords in PRODUCT_TAXONOMY.items():
        score = 0
        for keyword in keywords:
            # Contar ocorrências do keyword
            count = text_lower.count(keyword.lower())
            score += count
        
        if score > 0:
            category_scores[category] = score
    
    # Retornar categoria com maior score
    if not category_scores:
        return None
    
    # Ordenar por score e retornar a principal
    sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    primary_category = sorted_categories[0][0]
    
    # Se houver empate ou scores muito próximos, considerar "multiproduto"
    if len(sorted_categories) >= 2:
        top_score = sorted_categories[0][1]
        second_score = sorted_categories[1][1]
        
        # Se diferença < 30%, é multiproduto
        if second_score >= top_score * 0.7:
            return "multiproduto"
    
    return primary_category


def find_all_mentions(text: str, brand_name: str, brand_variations: Optional[List[str]] = None) -> List[int]:
    """
    Encontra todas as posições (em caracteres) onde a marca é mencionada.
    
    Args:
        text: Texto completo da resposta
        brand_name: Nome principal da marca
        brand_variations: Variações do nome (ex: ["PagBank", "Pag Bank", "PagSeguro"])
    
    Returns:
        Lista de posições (índices de caracteres) onde a marca aparece
    """
    positions: List[int] = []
    text_lower = text.lower()
    brand_lower = brand_name.lower()
    
    # Busca exata do nome principal
    start = 0
    while True:
        pos = text_lower.find(brand_lower, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
    
    # Busca por variações
    if brand_variations:
        for variation in brand_variations:
            var_lower = variation.lower()
            start = 0
            while True:
                pos = text_lower.find(var_lower, start)
                if pos == -1:
                    break
                # Evitar duplicatas (posições muito próximas)
                if not any(abs(pos - existing) < 5 for existing in positions):
                    positions.append(pos)
                start = pos + 1
    
    return sorted(positions)


def calculate_brand_presence_metrics(
    response_text: str,
    project_name: str,
    project_domains: Optional[List[str]] = None,
    brand_variations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Calcula métricas de presença de marca na resposta de LLM.
    
    Args:
        response_text: Texto completo da resposta
        project_name: Nome do projeto/marca principal
        project_domains: Lista de domínios do projeto (para detectar menções indiretas)
        brand_variations: Variações do nome da marca
    
    Returns:
        {
            "brand_mention_count": int,
            "brand_first_mention_position": int | None,
            "brand_mention_density": float,
            "brand_prominence_score": float
        }
    """
    if not response_text or not project_name:
        return {
            "brand_mention_count": 0,
            "brand_first_mention_position": None,
            "brand_mention_density": 0.0,
            "brand_prominence_score": 0.0,
        }
    
    text_length = len(response_text)
    if text_length == 0:
        return {
            "brand_mention_count": 0,
            "brand_first_mention_position": None,
            "brand_mention_density": 0.0,
            "brand_prominence_score": 0.0,
        }
    
    # Encontrar todas as menções
    positions = find_all_mentions(response_text, project_name, brand_variations)
    mention_count = len(positions)
    
    # Primeira posição (None se não houver menções)
    first_position_char = positions[0] if positions else None
    
    # Converter para percentual da resposta (0-100%)
    # 0% = início, 100% = final. Quanto menor, melhor!
    first_position_pct = None
    if first_position_char is not None:
        first_position_pct = round((first_position_char / text_length) * 100, 2)
    
    # Densidade: menções por 1000 caracteres
    density = (mention_count / text_length) * 1000.0
    
    # Prominence Score (0-100)
    prominence = 0.0
    
    if mention_count > 0 and first_position_char is not None:
        # Componente 1: Posição da primeira menção (40 pts)
        # Primeiros 20% do texto = 40 pts, últimos 20% = 0 pts
        first_pos_ratio = first_position_char / text_length
        if first_pos_ratio <= 0.20:
            prominence += 40.0
        elif first_pos_ratio <= 0.40:
            prominence += 30.0
        elif first_pos_ratio <= 0.60:
            prominence += 20.0
        elif first_pos_ratio <= 0.80:
            prominence += 10.0
        # else: 0 pts
        
        # Componente 2: Densidade de menções (30 pts)
        # > 2 por 1000 chars = alta densidade
        if density >= 3.0:
            prominence += 30.0
        elif density >= 2.0:
            prominence += 25.0
        elif density >= 1.0:
            prominence += 15.0
        elif density >= 0.5:
            prominence += 10.0
        else:
            prominence += 5.0
        
        # Componente 3: Menção no primeiro parágrafo (30 pts)
        # Assumir que primeiro parágrafo = primeiros 300 chars ou até primeiro \n\n
        first_paragraph_end = response_text.find("\n\n")
        if first_paragraph_end == -1:
            first_paragraph_end = min(300, text_length)
        
        if first_position_char < first_paragraph_end:
            prominence += 30.0
    
    return {
        "brand_mention_count": mention_count,
        "brand_first_mention_position": first_position_pct,  # Agora retorna percentual 0-100
        "brand_mention_density": round(density, 2),
        "brand_prominence_score": round(prominence, 2),
    }


def calculate_citation_quality_score(
    citations: List[Dict[str, Any]],
    response_text: str
) -> Dict[str, Any]:
    """
    Calcula score de qualidade das citações "nossas" (is_ours=True).
    
    Args:
        citations: Lista de dicts com keys: is_ours, position, anchor, url, domain
        response_text: Texto completo (para análise de contexto)
    
    Returns:
        {
            "citation_quality_score": float,  # 0-100
            "first_citation_position": int | None  # posição ordinal (1-N)
        }
    """
    our_citations = [c for c in citations if c.get("is_ours")]
    
    if not our_citations:
        return {
            "citation_quality_score": 0.0,
            "first_citation_position": None,
        }
    
    # Encontrar primeira citação nossa (menor posição)
    positions = [c.get("position") for c in our_citations if c.get("position")]
    try:
        positions_int = [int(p) for p in positions if p is not None]
        first_position = min(positions_int) if positions_int else None
    except (ValueError, TypeError):
        first_position = None
    
    # Calcular score para cada citação
    scores: List[float] = []
    
    for citation in our_citations:
        score = 0.0
        
        # 1. Score de Posição (40 pts)
        pos = citation.get("position")
        if pos:
            try:
                pos_int = int(pos)
                if pos_int == 1:
                    score += 40.0
                elif pos_int <= 3:
                    score += 30.0
                elif pos_int <= 5:
                    score += 20.0
                elif pos_int <= 10:
                    score += 10.0
                else:
                    score += 5.0
            except (ValueError, TypeError):
                score += 5.0
        
        # 2. Score de Anchor Text (20 pts)
        anchor = citation.get("anchor", "")
        if anchor and len(anchor) > 5:
            # Anchor descritivo (não-genérico)
            generic_anchors = {"clique aqui", "saiba mais", "leia mais", "veja", "acesse", "link", "fonte"}
            if anchor.lower() not in generic_anchors:
                score += 20.0
            else:
                score += 5.0
        else:
            score += 5.0
        
        # 3. Score de Contexto (30 pts)
        # Detectar se citação aparece em contexto positivo/recomendação
        url = citation.get("url", "")
        domain = citation.get("domain", "")
        
        # Buscar menção do domínio no texto
        context_positive_keywords = [
            "recomenda", "melhor", "ideal", "ótim", "excelente", "destaca",
            "líder", "referência", "principal", "especialista", "autoridade"
        ]
        
        # Janela de contexto: 200 chars ao redor da menção do domínio
        if domain and domain in response_text.lower():
            domain_pos = response_text.lower().find(domain.lower())
            start = max(0, domain_pos - 100)
            end = min(len(response_text), domain_pos + 100)
            context_window = response_text[start:end].lower()
            
            if any(kw in context_window for kw in context_positive_keywords):
                score += 30.0
            else:
                score += 10.0
        else:
            score += 10.0
        
        # 4. Score de Tipo de Domínio (10 pts)
        # Domínio direto (not subdomain) = mais autoridade
        if domain and "." in domain:
            parts = domain.split(".")
            if len(parts) == 2:  # ex: pagbank.com.br (primary)
                score += 10.0
            else:  # subdomain
                score += 5.0
        
        scores.append(score)
    
    # Média ponderada
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    return {
        "citation_quality_score": round(avg_score, 2),
        "first_citation_position": first_position,
    }


def calculate_competitive_metrics(
    response_text: str,
    project_name: str,
    competitors_from_gemini: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calcula métricas competitivas: share of voice e ratios.
    
    Args:
        response_text: Texto completo da resposta
        project_name: Nome da marca principal
        competitors_from_gemini: Lista de competitors do payload Gemini
            [{"name": "Nubank", "mentions": 3}, ...]
    
    Returns:
        {
            "competitor_mention_ratio": float,  # 0-1
            "share_of_voice_llm": float  # 0-100
        }
    """
    if not response_text or not project_name:
        return {
            "competitor_mention_ratio": 0.0,
            "share_of_voice_llm": 0.0,
        }
    
    # Contar menções da nossa marca
    our_positions = find_all_mentions(response_text, project_name)
    our_count = len(our_positions)
    
    # Contar menções de competidores
    competitor_counts: Dict[str, int] = {}
    total_competitor_mentions = 0
    
    for comp in competitors_from_gemini:
        comp_name = comp.get("name", "")
        if not comp_name:
            continue
        
        # Tentar usar o campo "mentions" se disponível
        if "mentions" in comp and comp["mentions"]:
            try:
                count = int(comp["mentions"])
                competitor_counts[comp_name] = count
                total_competitor_mentions += count
                continue
            except (ValueError, TypeError):
                pass
        
        # Fallback: contar no texto
        comp_positions = find_all_mentions(response_text, comp_name)
        count = len(comp_positions)
        competitor_counts[comp_name] = count
        total_competitor_mentions += count
    
    # Calcular ratios
    total_mentions = our_count + total_competitor_mentions
    
    if total_mentions == 0:
        return {
            "competitor_mention_ratio": 0.0,
            "share_of_voice_llm": 0.0,
        }
    
    ratio = our_count / total_mentions
    share_of_voice = ratio * 100.0
    
    return {
        "competitor_mention_ratio": round(ratio, 4),
        "share_of_voice_llm": round(share_of_voice, 2),
    }


def calculate_engagement_metrics(response_text: str) -> Dict[str, Any]:
    """
    Detecta gatilhos conversacionais e calcula score de engajamento.
    
    Triggers detectados:
    - CTAs explícitos: "visite", "saiba mais", "conheça"
    - Perguntas abertas: "você pode", "considere"
    - Indicadores de continuação: "além disso", "também"
    - Links/URLs
    - Benefícios específicos: "economiza", "garante"
    
    Returns:
        {
            "conversational_trigger_count": int,
            "engagement_score": float  # 0-100
        }
    """
    if not response_text:
        return {
            "conversational_trigger_count": 0,
            "engagement_score": 0.0,
        }
    
    text_lower = response_text.lower()
    trigger_count = 0
    
    # 1. CTAs explícitos (peso 2)
    cta_keywords = [
        r"\bvisite\b", r"\bsaiba mais\b", r"\bconheça\b", r"\bexperimente\b",
        r"\bcompare\b", r"\bverifique\b", r"\bacesse\b", r"\bconsulte\b",
        r"\bconfira\b", r"\bdescubra\b", r"\bentre em contato\b"
    ]
    for pattern in cta_keywords:
        matches = re.findall(pattern, text_lower)
        trigger_count += len(matches) * 2
    
    # 2. Perguntas abertas (peso 1)
    question_patterns = [
        r"\bvocê pode\b", r"\bconsidere\b", r"\bque tal\b", r"\bpor que não\b",
        r"\bpense em\b", r"\bavalie\b", r"\bimportante lembrar\b"
    ]
    for pattern in question_patterns:
        matches = re.findall(pattern, text_lower)
        trigger_count += len(matches)
    
    # 3. Indicadores de continuação (peso 0.5)
    continuation_patterns = [
        r"\balém disso\b", r"\btambém\b", r"\bvale lembrar\b", r"\boutra opção\b",
        r"\badicionalmente\b", r"\bpor outro lado\b"
    ]
    for pattern in continuation_patterns:
        matches = re.findall(pattern, text_lower)
        trigger_count += len(matches) * 0.5
    
    # 4. URLs/Links (peso 1 cada)
    url_pattern = r"https?://[^\s]+"
    urls = re.findall(url_pattern, response_text)
    trigger_count += len(urls)
    
    # 5. Menções de benefícios (peso 1)
    benefit_keywords = [
        r"\beconomiza\b", r"\bgarante\b", r"\bfacilita\b", r"\bagiliza\b",
        r"\bsem custo\b", r"\bgratuito\b", r"\bbonus\b", r"\bvantagem\b",
        r"\bdesconto\b", r"\boferta\b", r"\bbenefico\b"
    ]
    for pattern in benefit_keywords:
        matches = re.findall(pattern, text_lower)
        trigger_count += len(matches)
    
    # Calcular engagement score com escala contínua mais realista
    # 0 triggers = 0
    # 1-5 triggers = 10-40 (baixo)
    # 6-12 triggers = 40-70 (médio)
    # 13-20 triggers = 70-90 (alto)
    # 21+ triggers = 90-100 (excepcional)

    if trigger_count == 0:
        score = 0.0
    elif trigger_count <= 5:
        # 10 base + 6 por trigger
        score = 10.0 + (trigger_count * 6.0)
    elif trigger_count <= 12:
        # 40 base + 4.3 por trigger adicional
        score = 40.0 + ((trigger_count - 5) * 4.3)
    elif trigger_count <= 20:
        # 70 base + 2.5 por trigger adicional
        score = 70.0 + ((trigger_count - 12) * 2.5)
    else:
        # 90 base + 0.5 por trigger adicional (cap em 100)
        score = min(100.0, 90.0 + ((trigger_count - 20) * 0.5))
    
    return {
        "conversational_trigger_count": int(trigger_count),
        "engagement_score": score,
    }


def calculate_citation_rates(
    citations: List[Dict[str, Any]],
    domain_variants_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Calcula Citation Rate (CR) observado e corrigido.
    
    Args:
        citations: Lista de citações com is_ours e domain
        domain_variants_map: Mapeamento de variantes → canonical
            Ex: {"bancodobrasil.com.br": "bb.com.br", "ourocard.com.br": "bb.com.br"}
    
    Returns:
        {
            "citation_rate_observed": float,  # % simples
            "citation_rate_corrected": float,  # % ajustado por variantes
            "cocitation_competitors": str  # JSON array
        }
    """
    if not citations:
        return {
            "citation_rate_observed": 0.0,
            "citation_rate_corrected": 0.0,
            "cocitation_competitors": "[]",
        }
    
    total_citations = len(citations)
    
    # CR Observado: contagem simples de is_ours
    our_citations_observed = sum(1 for c in citations if c.get("is_ours"))
    cr_observed = (our_citations_observed / total_citations) * 100.0 if total_citations > 0 else 0.0
    
    # CR Corrigido: considerar variantes de domínio
    our_citations_corrected = our_citations_observed
    
    if domain_variants_map:
        # Contar citações de domínios variantes como "nossas"
        for citation in citations:
            if citation.get("is_ours"):
                continue  # já contado
            
            domain = citation.get("domain", "").lower()
            if domain in domain_variants_map:
                our_citations_corrected += 1
    
    cr_corrected = (our_citations_corrected / total_citations) * 100.0 if total_citations > 0 else 0.0
    
    # Co-citação: lista de domínios de concorrentes que aparecem junto
    competitor_domains: List[str] = []
    for citation in citations:
        if not citation.get("is_ours"):
            domain = citation.get("domain")
            if domain and domain not in competitor_domains:
                # Verificar se é variante nossa
                if domain_variants_map and domain.lower() in domain_variants_map:
                    continue
                competitor_domains.append(domain)
    
    # Retornar JSON array como string
    import json
    cocitation_json = json.dumps(competitor_domains[:20])  # limitar top 20
    
    return {
        "citation_rate_observed": round(cr_observed, 2),
        "citation_rate_corrected": round(cr_corrected, 2),
        "cocitation_competitors": cocitation_json,
    }


def calculate_all_geo_metrics(
    response_text: str,
    project_name: str,
    citations: List[Dict[str, Any]],
    competitors_from_gemini: List[Dict[str, Any]],
    project_domains: Optional[List[str]] = None,
    brand_variations: Optional[List[str]] = None,
    domain_variants_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Calcula TODAS as métricas GEO de uma vez.
    
    Args:
        response_text: Texto completo da resposta do LLM
        project_name: Nome do projeto/marca
        citations: Lista de citações
        competitors_from_gemini: Concorrentes do payload Gemini
        project_domains: Domínios do projeto
        brand_variations: Variações do nome da marca
        domain_variants_map: Mapeamento de variantes de domínio
    
    Returns:
        Dict com todas as keys necessárias para atualizar modelo Run.
    """
    metrics = {}
    
    # Brand Presence
    brand_metrics = calculate_brand_presence_metrics(
        response_text=response_text,
        project_name=project_name,
        project_domains=project_domains,
        brand_variations=brand_variations,
    )
    metrics.update(brand_metrics)
    
    # Citation Quality
    citation_metrics = calculate_citation_quality_score(
        citations=citations,
        response_text=response_text,
    )
    metrics.update(citation_metrics)
    
    # Citation Rates
    citation_rates = calculate_citation_rates(
        citations=citations,
        domain_variants_map=domain_variants_map,
    )
    metrics.update(citation_rates)
    
    # Competitive
    comp_metrics = calculate_competitive_metrics(
        response_text=response_text,
        project_name=project_name,
        competitors_from_gemini=competitors_from_gemini,
    )
    metrics.update(comp_metrics)
    
    # Engagement
    engagement = calculate_engagement_metrics(response_text=response_text)
    metrics.update(engagement)
    
    # Advanced Metrics (Phase 2+)
    advanced = calculate_advanced_metrics(
        response_text=response_text,
        citations=citations,
        project_name=project_name,
        engagement_score=engagement.get("engagement_score", 0.0),
    )
    metrics.update(advanced)
    
    # Product Category Classification
    product_category = classify_product_category(response_text, project_name)
    metrics["product_category"] = product_category
    
    return metrics


def calculate_advanced_metrics(
    response_text: str,
    citations: List[Dict[str, Any]],
    project_name: str,
    engagement_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Calcula métricas avançadas GEO (Phase 2+).
    
    Returns:
        {
            "zero_click_presence": float,  # 0-100
            "authority_score": float,  # 0-100
            "relevance_score": float,  # 0-100
            "clarity_score": float,  # 0-100
            "conversion_potential": str,  # "alto" | "medio" | "baixo"
            "conversion_potential_score": float,  # 0-100
        }
    """
    if not response_text:
        return {
            "zero_click_presence": 0.0,
            "authority_score": 0.0,
            "relevance_score": 0.0,
            "clarity_score": 0.0,
        }
    
    # 1. Zero-Click Presence
    # Heurística: resposta completa (>500 chars) + menção da marca + sem muitos links externos
    zero_click = 0.0
    text_length = len(response_text)
    
    if text_length >= 500:
        zero_click += 40.0  # Resposta substancial
    elif text_length >= 300:
        zero_click += 25.0
    elif text_length >= 150:
        zero_click += 10.0
    
    # Marca mencionada
    if project_name.lower() in response_text.lower():
        zero_click += 30.0
    
    # Poucos links externos (indica resposta auto-contida)
    external_links = len([c for c in citations if not c.get("is_ours")])
    if external_links == 0:
        zero_click += 30.0
    elif external_links <= 2:
        zero_click += 20.0
    elif external_links <= 5:
        zero_click += 10.0
    
    # 2. Authority Score
    # Detectar linguagem de autoridade + citações oficiais
    authority = 0.0
    text_lower = response_text.lower()

    # Palavras-chave de autoridade expandidas
    authority_keywords = [
        "líder", "referência", "especialista", "autoridade", "principal",
        "reconhecid", "estabelecid", "tradicional", "maior", "melhor",
        "expertise", "experiência", "confiável", "sólid", "respeitad",
        "oficial", "certificad", "aprovad", "regulamentad", "licenciad",
        "premiado", "destaque", "top", "ranking", "primeiro lugar",
        "fundad", "história", "anos de mercado", "pioneiro"
    ]

    # Palavras-chave negativas (reduzem authority)
    negative_keywords = [
        "problema", "reclamação", "falha", "defeito", "insatisfação",
        "não recomend", "evite", "cuidado", "atenção", "risco"
    ]

    # Componente 1: Keywords de autoridade próximas à marca (40 pts)
    brand_lower = project_name.lower()
    if brand_lower in text_lower:
        brand_pos = text_lower.find(brand_lower)
        # Janela de 200 chars ao redor
        start = max(0, brand_pos - 100)
        end = min(len(text_lower), brand_pos + 100)
        context = text_lower[start:end]

        authority_count = sum(1 for kw in authority_keywords if kw in context)
        negative_count = sum(1 for kw in negative_keywords if kw in context)

        # Cada keyword positiva = +10 pts, negativa = -15 pts
        authority_from_keywords = (authority_count * 10.0) - (negative_count * 15.0)
        authority += max(0, min(40.0, authority_from_keywords))

    # Componente 2: Citações oficiais (60 pts)
    # URLs do domínio oficial = forte sinal de autoridade
    our_citations_count = sum(1 for c in citations if c.get("is_ours"))
    if our_citations_count >= 3:
        authority += 60.0  # 3+ citações = máxima autoridade
    elif our_citations_count == 2:
        authority += 45.0
    elif our_citations_count == 1:
        authority += 30.0

    authority = min(100.0, authority)
    
    # 3. Relevance Score
    # Heurística: marca mencionada + contexto relevante + sem desvios
    relevance = 0.0
    
    if brand_lower in text_lower:
        relevance += 50.0  # Marca presente
        
        # Múltiplas menções = mais relevante
        mention_count = text_lower.count(brand_lower)
        if mention_count >= 3:
            relevance += 30.0
        elif mention_count >= 2:
            relevance += 20.0
        else:
            relevance += 10.0
        
        # Menção no início = mais relevante
        first_mention_pos = text_lower.find(brand_lower)
        if first_mention_pos < len(text_lower) * 0.2:
            relevance += 20.0
        elif first_mention_pos < len(text_lower) * 0.5:
            relevance += 10.0
    
    relevance = min(100.0, relevance)
    
    # 4. Clarity Score
    # Heurística: estrutura clara + parágrafos + listas + sem ambiguidade
    clarity = 0.0
    
    # Estrutura em parágrafos
    paragraph_count = response_text.count("\n\n") + 1
    if paragraph_count >= 3:
        clarity += 30.0
    elif paragraph_count >= 2:
        clarity += 20.0
    else:
        clarity += 10.0
    
    # Listas/bullets
    if any(marker in response_text for marker in ["- ", "* ", "• ", "1.", "2."]):
        clarity += 30.0
    
    # Sentenças claras (não muito longas)
    sentences = response_text.split(".")
    avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
    if avg_sentence_length < 150:  # Sentenças concisas
        clarity += 20.0
    elif avg_sentence_length < 250:
        clarity += 10.0
    
    # Uso de números/dados (clareza objetiva)
    import re
    numbers = re.findall(r'\d+', response_text)
    if len(numbers) >= 5:
        clarity += 20.0
    elif len(numbers) >= 3:
        clarity += 10.0
    
    clarity = min(100.0, clarity)
    
    # 5. Conversion Potential
    # Fórmula: média ponderada de engagement, authority, relevance e zero-click
    # Pesos rebalanceados após melhorias nas métricas
    conversion_potential_score = (
        engagement_score * 0.30 +  # Engagement (gatilhos conversacionais)
        authority * 0.30 +          # Autoridade (citações + keywords) - aumentado
        relevance * 0.25 +          # Relevância (menções e contexto)
        zero_click * 0.15           # Zero-click (reduz fricção)
    )
    
    # Classificar em categorias
    if conversion_potential_score >= 75:
        conversion_potential = "alto"
    elif conversion_potential_score >= 50:
        conversion_potential = "medio"
    else:
        conversion_potential = "baixo"
    
    return {
        "zero_click_presence": round(zero_click, 2),
        "authority_score": round(authority, 2),
        "relevance_score": round(relevance, 2),
        "clarity_score": round(clarity, 2),
        "conversion_potential": conversion_potential,
        "conversion_potential_score": round(conversion_potential_score, 2),
    }
