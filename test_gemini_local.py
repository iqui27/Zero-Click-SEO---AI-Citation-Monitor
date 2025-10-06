#!/usr/bin/env python3
"""Teste local do Gemini Semantic Service."""

import sys
import os

# Adicionar path do backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.gemini_semantic import GeminiSemanticService

# Dados de teste
question = "Conta universitária: quais bancos têm gratuita para estudantes?"

response_text = """
Para estudantes universitários, várias instituições financeiras oferecem contas gratuitas com benefícios especiais. O Banco do Brasil disponibiliza a Conta Universitária BB, sem tarifas de manutenção e com cartão de débito gratuito. O Santander oferece a Conta Universitária Santander, também sem custos mensais e com acesso a aplicativo mobile. A Caixa Econômica Federal possui a Conta Universitária Caixa, isenta de tarifas para estudantes regularmente matriculados. O Itaú tem o Itaú Universitário, com isenção de tarifas e benefícios exclusivos. O Bradesco oferece a Conta Universitária Bradesco, sem mensalidade e com cartão internacional. Bancos digitais como Nubank, Inter e C6 Bank também oferecem contas gratuitas para estudantes, com funcionalidades completas pelo aplicativo. Para abrir essas contas, geralmente é necessário apresentar comprovante de matrícula em instituição de ensino superior reconhecida pelo MEC.
"""

citations = [
    {"domain": "bb.com.br", "url": "https://www.bb.com.br/conta-universitaria"},
    {"domain": "santander.com.br", "url": "https://www.santander.com.br/estudantes"},
    {"domain": "caixa.gov.br", "url": "https://www.caixa.gov.br/universitarios"},
    {"domain": "itau.com.br", "url": "https://www.itau.com.br/estudantes"},
    {"domain": "bradesco.com.br", "url": "https://www.bradesco.com.br/universitarios"},
    {"domain": "nubank.com.br", "url": "https://nubank.com.br/estudantes"},
]

def test_gemini():
    print("=" * 80)
    print("🧪 TESTE LOCAL - GEMINI SEMANTIC SERVICE")
    print("=" * 80)
    print()
    
    try:
        # Inicializar serviço
        print("📡 Inicializando Gemini...")
        service = GeminiSemanticService()
        print("✅ Gemini inicializado com sucesso")
        print()
        
        # Executar análise
        print("🔍 Analisando resposta...")
        print(f"Pergunta: {question}")
        print(f"Texto: {response_text[:100]}...")
        print()
        
        result = service.analyze(
            question=question,
            response_text=response_text,
            citations=citations,
            project_name="Banco do Brasil",
        )
        
        print("=" * 80)
        print("✅ RESULTADO")
        print("=" * 80)
        print()
        
        # Mostrar resultado
        print(f"📊 Entidades encontradas: {len(result.get('entities', []))}")
        for entity in result.get('entities', [])[:5]:
            print(f"  - {entity.get('name')} ({entity.get('category')}) - confiança: {entity.get('confidence')}")
        
        print()
        print(f"🔑 Keywords encontradas: {len(result.get('keywords', []))}")
        for kw in result.get('keywords', [])[:5]:
            print(f"  - {kw.get('token')} - peso: {kw.get('weight')}")
        
        print()
        print(f"🔗 Relacionamentos: {len(result.get('relationships', []))}")
        
        print()
        print(f"📝 Summary: {result.get('summary', {}).get('headline', 'N/A')}")
        
        print()
        print(f"🏆 Competidores: {len(result.get('competitors', []))}")
        for comp in result.get('competitors', [])[:3]:
            print(f"  - {comp.get('name')} - menções: {comp.get('mentions')}")
        
        print()
        print("=" * 80)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERRO NO TESTE")
        print("=" * 80)
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gemini()
    sys.exit(0 if success else 1)
