"""
Google Search Console Service - Busca dados reais de CTR, impressões e cliques.

Este serviço integra com a Google Search Console API para obter:
- CTR real por query
- Impressões
- Cliques  
- Posição média
"""

from __future__ import annotations
from typing import Dict, Optional
from datetime import datetime, timedelta
import json
import os


class SearchConsoleService:
    """Serviço para buscar dados do Google Search Console."""
    
    @staticmethod
    async def get_query_data(
        credentials_json: str,
        site_url: str,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Busca dados de uma query específica do Search Console.
        
        Args:
            credentials_json: Token OAuth2 criptografado
            site_url: URL do site no Search Console (ex: https://exemplo.com)
            query: Query para buscar dados
            start_date: Data inicial (padrão: 7 dias atrás)
            end_date: Data final (padrão: hoje)
            
        Returns:
            {
                "clicks": 150,
                "impressions": 5000,
                "ctr": 0.03,  # 3%
                "position": 5.2,
                "has_data": True
            }
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from app.core.encryption import decrypt_token
            
            # Datas padrão
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=7)
            
            # Descriptografar e carregar credenciais
            decrypted = decrypt_token(credentials_json)
            credentials = Credentials.from_authorized_user_info(json.loads(decrypted))
            
            # Construir serviço
            service = build('searchconsole', 'v1', credentials=credentials)
            
            # Preparar request
            request_body = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'dimensionFilterGroups': [{
                    'filters': [{
                        'dimension': 'query',
                        'expression': query,
                        'operator': 'equals'
                    }]
                }],
                'rowLimit': 1
            }
            
            # Executar query
            response = service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()
            
            # Processar resposta
            if 'rows' in response and len(response['rows']) > 0:
                row = response['rows'][0]
                return {
                    "clicks": row.get('clicks', 0),
                    "impressions": row.get('impressions', 0),
                    "ctr": row.get('ctr', 0.0),
                    "position": row.get('position', 0.0),
                    "has_data": True
                }
            
            # Sem dados
            return {
                "clicks": 0,
                "impressions": 0,
                "ctr": 0.0,
                "position": 0.0,
                "has_data": False
            }
            
        except ImportError:
            print("[SEARCH_CONSOLE] Google API libraries not installed")
            return SearchConsoleService._empty_data()
        except Exception as e:
            print(f"[SEARCH_CONSOLE] Error fetching data: {e}")
            import traceback
            traceback.print_exc()
            return SearchConsoleService._empty_data()
    
    @staticmethod
    def _empty_data() -> Dict:
        """Retorna dados vazios em caso de erro."""
        return {
            "clicks": 0,
            "impressions": 0,
            "ctr": 0.0,
            "position": 0.0,
            "has_data": False
        }
    
    @staticmethod
    def calculate_irzc_with_real_data(ctr_ratio: float, zero_click_features: int) -> float:
        """
        Calcula IRZC (Índice de Resistência Zero-Click) com dados reais.
        
        Args:
            ctr_ratio: CTR real / CTR esperado (0.0 - 2.0+)
            zero_click_features: Número de features de IA/zero-click na SERP
            
        Returns:
            Score 0-100 (quanto maior, menor o risco de zero-click)
        """
        # Base score pelo CTR ratio
        if ctr_ratio >= 1.0:
            base_score = 90  # CTR igual ou melhor que esperado
        elif ctr_ratio >= 0.8:
            base_score = 70  # CTR próximo do esperado
        elif ctr_ratio >= 0.5:
            base_score = 50  # CTR moderadamente abaixo
        elif ctr_ratio >= 0.3:
            base_score = 30  # CTR muito abaixo
        else:
            base_score = 10  # CTR crítico
        
        # Penalizar por features de zero-click
        if zero_click_features > 0:
            penalty = min(30, zero_click_features * 10)
            base_score = max(0, base_score - penalty)
        
        return round(base_score, 2)
