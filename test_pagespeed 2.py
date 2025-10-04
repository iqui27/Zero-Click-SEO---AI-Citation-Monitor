#!/usr/bin/env python3
"""Testa o PageSpeedAnalyzer."""

import sys
import asyncio
sys.path.insert(0, 'backend')

from app.services.pagespeed_analyzer import PageSpeedAnalyzer

async def test():
    print("🧪 Testando PageSpeed Insights API...")
    print(f"   API Key: {'✅ Configurada' if PageSpeedAnalyzer.API_KEY else '❌ Não configurada'}")
    
    # Testar com uma URL real
    url = "https://www.google.com"
    print(f"\n🔍 Analisando: {url}")
    
    result = await PageSpeedAnalyzer.analyze_url(url, strategy="mobile")
    
    print(f"\n📊 Resultados:")
    print(f"   Performance Score: {result.get('performance_score')}")
    print(f"   Core Web Vitals Score: {result.get('core_web_vitals_score')}")
    print(f"   LCP: {result.get('lcp_value')}s (score: {result.get('lcp_score')})")
    print(f"   FID: {result.get('fid_value')}ms (score: {result.get('fid_score')})")
    print(f"   INP: {result.get('inp_value')}ms (score: {result.get('inp_score')})")
    print(f"   CLS: {result.get('cls_value')} (score: {result.get('cls_score')})")
    print(f"   Strategy: {result.get('strategy')}")
    
    if result.get('core_web_vitals_score'):
        print(f"\n✅ PageSpeed API funcionando perfeitamente!")
    else:
        print(f"\n❌ PageSpeed API retornou dados vazios")

if __name__ == "__main__":
    asyncio.run(test())
