#!/usr/bin/env python3
"""Test script to verify GEO metrics calculation"""

import sys
sys.path.append('backend')

from app.services.geo_metrics import calculate_all_geo_metrics

# Test data simulating an OpenAI response about Banco do Brasil
response_text = """
O Banco do Brasil é uma das maiores instituições financeiras do país, oferecendo diversos produtos e serviços.

Para MEIs, o BB oferece conta corrente com tarifas competitivas e acesso a linhas de crédito específicas.
As principais vantagens incluem:

- Conta digital sem mensalidade
- Acesso a crédito com taxas especiais
- Aplicativo completo para gestão financeira
- Atendimento personalizado

Outros bancos que também atendem MEIs incluem Nubank, Itaú e Bradesco. Confira as opções no site oficial do Banco do Brasil para mais detalhes.

Fontes:
- https://www.bb.com.br/pj/mei
- https://www.nubank.com.br/pj
- https://www.itau.com.br/empresas
"""

# Test citations
citations = [
    {"domain": "bb.com.br", "url": "https://www.bb.com.br/pj/mei", "anchor": "site oficial do Banco do Brasil", "position": "1", "is_ours": True},
    {"domain": "nubank.com.br", "url": "https://www.nubank.com.br/pj", "anchor": "Nubank", "position": "2", "is_ours": False},
    {"domain": "itau.com.br", "url": "https://www.itau.com.br/empresas", "anchor": "Itaú", "position": "3", "is_ours": False},
]

# Test competitors
competitors_from_gemini = [
    {"name": "Nubank", "mentions": 1},
    {"name": "Itaú", "mentions": 1},
    {"name": "Bradesco", "mentions": 1},
]

print("=" * 80)
print("TESTING GEO METRICS CALCULATION")
print("=" * 80)

try:
    # Calculate GEO metrics
    geo_metrics = calculate_all_geo_metrics(
        response_text=response_text,
        project_name="Banco do Brasil",
        citations=citations,
        competitors_from_gemini=competitors_from_gemini,
        project_domains=["bb.com.br"],
        brand_variations=["BB", "Banco do Brasil"],
        domain_variants_map={},
    )

    print("\n✓ GEO METRICS CALCULATED SUCCESSFULLY\n")
    print("-" * 80)
    print("BRAND PRESENCE:")
    print(f"  • Brand Mention Count: {geo_metrics.get('brand_mention_count')}")
    print(f"  • First Mention Position: {geo_metrics.get('brand_first_mention_position')}%")
    print(f"  • Mention Density: {geo_metrics.get('brand_mention_density')}")
    print(f"  • Prominence Score: {geo_metrics.get('brand_prominence_score')}")

    print("\nCITATION QUALITY:")
    print(f"  • Citation Rate (Observed): {geo_metrics.get('citation_rate_observed')}%")
    print(f"  • Citation Rate (Corrected): {geo_metrics.get('citation_rate_corrected')}%")
    print(f"  • Citation Quality Score: {geo_metrics.get('citation_quality_score')}")
    print(f"  • First Citation Position: {geo_metrics.get('first_citation_position')}")

    print("\nCOMPETITIVE INTELLIGENCE:")
    print(f"  • Competitor Mention Ratio: {geo_metrics.get('competitor_mention_ratio')}")
    print(f"  • Share of Voice (LLM): {geo_metrics.get('share_of_voice_llm')}%")
    print(f"  • Co-citation Competitors: {geo_metrics.get('cocitation_competitors')}")

    print("\nENGAGEMENT:")
    print(f"  • Conversational Trigger Count: {geo_metrics.get('conversational_trigger_count')}")
    print(f"  • Engagement Score: {geo_metrics.get('engagement_score')}")

    print("\nADVANCED METRICS:")
    print(f"  • Zero-Click Presence: {geo_metrics.get('zero_click_presence')}")
    print(f"  • Authority Score: {geo_metrics.get('authority_score')}")
    print(f"  • Relevance Score: {geo_metrics.get('relevance_score')}")
    print(f"  • Clarity Score: {geo_metrics.get('clarity_score')}")
    print(f"  • Conversion Potential: {geo_metrics.get('conversion_potential')}")
    print(f"  • Conversion Potential Score: {geo_metrics.get('conversion_potential_score')}")

    print("\nPRODUCT CATEGORY:")
    print(f"  • Category: {geo_metrics.get('product_category')}")

    print("\n" + "=" * 80)
    print("✓ TEST PASSED - All GEO metrics calculated successfully!")
    print("=" * 80)

except Exception as e:
    print("\n✗ TEST FAILED")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
