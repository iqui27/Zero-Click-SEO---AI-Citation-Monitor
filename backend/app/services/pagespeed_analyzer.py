"""
PageSpeed Insights Analyzer - Busca Core Web Vitals reais via API do Google.

Este módulo integra com a PageSpeed Insights API para obter:
- LCP (Largest Contentful Paint)
- FID (First Input Delay) / INP (Interaction to Next Paint)
- CLS (Cumulative Layout Shift)
- Performance Score (0-100)
"""

from __future__ import annotations
from typing import Dict, Optional, Any, Tuple
import httpx
import os
import time


class PageSpeedAnalyzer:
    """Analisador de Core Web Vitals via PageSpeed Insights API."""
    
    # API Key do Google PageSpeed Insights (opcional mas recomendado)
    API_KEY = os.getenv("PAGESPEED_API_KEY", "")
    BASE_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    CACHE_TTL_SECONDS = int(os.getenv("PAGESPEED_CACHE_TTL", "900"))  # 15 minutos por padrão
    _cache: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
    
    # Thresholds do Google para Core Web Vitals
    THRESHOLDS = {
        "lcp": {"good": 2500, "poor": 4000},  # ms
        "fid": {"good": 100, "poor": 300},    # ms
        "inp": {"good": 200, "poor": 500},    # ms
        "cls": {"good": 0.1, "poor": 0.25},   # score
    }
    
    @staticmethod
    async def analyze_url(url: str, strategy: str = "mobile") -> Dict[str, Any]:
        """
        Analisa uma URL via PageSpeed Insights API.
        
        Args:
            url: URL a ser analisada
            strategy: 'mobile' ou 'desktop'
            
        Returns:
            Dict com métricas de Core Web Vitals
        """
        cache_key = (url, strategy)
        cached = PageSpeedAnalyzer._get_cached(cache_key, allow_stale=False)
        if cached is not None:
            print(f"[PAGESPEED] Usando cache válido para {url} ({strategy})")
            return cached

        try:
            params = {
                "url": url,
                "strategy": strategy,
                "category": "performance",
            }
            
            if PageSpeedAnalyzer.API_KEY:
                params["key"] = PageSpeedAnalyzer.API_KEY
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(PageSpeedAnalyzer.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
            
            result = PageSpeedAnalyzer._parse_pagespeed_data(data)
            PageSpeedAnalyzer._cache[cache_key] = (time.time(), result)
            return result
            
        except httpx.TimeoutException:
            print(f"[PAGESPEED] Timeout ao analisar {url}")
            fallback = PageSpeedAnalyzer._get_cached(cache_key, allow_stale=True)
            if fallback is not None:
                print(f"[PAGESPEED] Usando cache antigo para {url} ({strategy}) após timeout")
                return fallback
            return PageSpeedAnalyzer._empty_metrics()
        except httpx.HTTPStatusError as e:
            print(f"[PAGESPEED] Erro HTTP {e.response.status_code} ao analisar {url}")
            fallback = PageSpeedAnalyzer._get_cached(cache_key, allow_stale=True)
            if fallback is not None:
                print(f"[PAGESPEED] Usando cache antigo para {url} ({strategy}) após erro HTTP")
                return fallback
            return PageSpeedAnalyzer._empty_metrics()
        except Exception as e:
            print(f"[PAGESPEED] Erro ao analisar {url}: {e}")
            fallback = PageSpeedAnalyzer._get_cached(cache_key, allow_stale=True)
            if fallback is not None:
                print(f"[PAGESPEED] Usando cache antigo para {url} ({strategy}) após erro inesperado")
                return fallback
            return PageSpeedAnalyzer._empty_metrics()
    
    @staticmethod
    def _parse_pagespeed_data(data: Dict) -> Dict[str, Any]:
        """
        Extrai métricas relevantes da resposta da API.
        """
        lighthouse = data.get("lighthouseResult", {})
        audits = lighthouse.get("audits", {})
        categories = lighthouse.get("categories", {})
        
        # Performance Score (0-100)
        performance_score = categories.get("performance", {}).get("score", 0) * 100
        
        # Core Web Vitals
        lcp_audit = audits.get("largest-contentful-paint", {})
        fid_audit = audits.get("max-potential-fid", {})  # FID estimado
        inp_audit = audits.get("interaction-to-next-paint", {})  # INP (novo)
        cls_audit = audits.get("cumulative-layout-shift", {})
        
        lcp_value = lcp_audit.get("numericValue", 0) / 1000  # converter para segundos
        fid_value = fid_audit.get("numericValue", 0)
        inp_value = inp_audit.get("numericValue", 0)
        cls_value = cls_audit.get("numericValue", 0)
        
        # Calcular scores individuais (0-100)
        lcp_score = PageSpeedAnalyzer._calculate_metric_score(lcp_value * 1000, "lcp")
        fid_score = PageSpeedAnalyzer._calculate_metric_score(fid_value, "fid")
        inp_score = PageSpeedAnalyzer._calculate_metric_score(inp_value, "inp")
        cls_score = PageSpeedAnalyzer._calculate_metric_score(cls_value, "cls")
        
        # Core Web Vitals Score agregado
        cwv_score = (lcp_score + max(fid_score, inp_score) + cls_score) / 3
        
        return {
            "performance_score": round(performance_score, 2),
            "core_web_vitals_score": round(cwv_score, 2),
            "lcp_value": round(lcp_value, 2),
            "lcp_score": round(lcp_score, 2),
            "fid_value": round(fid_value, 2),
            "fid_score": round(fid_score, 2),
            "inp_value": round(inp_value, 2),
            "inp_score": round(inp_score, 2),
            "cls_value": round(cls_value, 3),
            "cls_score": round(cls_score, 2),
            "strategy": data.get("lighthouseResult", {}).get("configSettings", {}).get("formFactor", "mobile"),
        }
    
    @staticmethod
    def _calculate_metric_score(value: float, metric: str) -> float:
        """
        Calcula score (0-100) baseado nos thresholds do Google.
        
        Good = 100-90
        Needs Improvement = 89-50
        Poor = 49-0
        """
        thresholds = PageSpeedAnalyzer.THRESHOLDS.get(metric, {})
        good = thresholds.get("good", 0)
        poor = thresholds.get("poor", 0)
        
        if value <= good:
            # Good: 90-100
            return 90 + ((good - value) / good) * 10
        elif value <= poor:
            # Needs Improvement: 50-89
            range_size = poor - good
            position = (value - good) / range_size
            return 90 - (position * 40)
        else:
            # Poor: 0-49
            excess = value - poor
            penalty = min(50, (excess / poor) * 50)
            return max(0, 50 - penalty)
    
    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Retorna métricas vazias em caso de erro."""
        return {
            "performance_score": None,
            "core_web_vitals_score": None,
            "lcp_value": None,
            "lcp_score": None,
            "fid_value": None,
            "fid_score": None,
            "inp_value": None,
            "inp_score": None,
            "cls_value": None,
            "cls_score": None,
            "strategy": None,
        }

    @classmethod
    def _get_cached(cls, key: Tuple[str, str], allow_stale: bool) -> Optional[Dict[str, Any]]:
        entry = cls._cache.get(key)
        if not entry:
            return None
        timestamp, value = entry
        age = time.time() - timestamp
        if age <= cls.CACHE_TTL_SECONDS:
            return value
        if allow_stale:
            return value
        return None
