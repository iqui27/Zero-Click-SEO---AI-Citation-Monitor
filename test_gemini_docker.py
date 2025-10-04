#!/usr/bin/env python3
"""Teste do Gemini Semantic Service dentro do Docker."""

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

print("=" * 80)
print("🧪 TESTE - GEMINI SEMANTIC SERVICE")
print("=" * 80)
print()

try:
    # Inicializar serviço
    print("📡 Inicializando Gemini...")
    service = GeminiSemanticService()
    print("✅ Gemini inicializado")
    print()
    
    # Executar análise
    print("🔍 Analisando resposta...")
    print(f"Pergunta: {question}")
    print(f"Texto: {len(response_text)} caracteres")
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
    entities = result.get('entities', [])
    print(f"📊 Entidades: {len(entities)}")
    for entity in entities[:5]:
        name = entity.get('name', 'N/A')
        category = entity.get('category', 'N/A')
        confidence = entity.get('confidence', 0)
        print(f"  - {name} ({category}) - {confidence:.2f}")
    
    print()
    keywords = result.get('keywords', [])
    print(f"🔑 Keywords: {len(keywords)}")
    for kw in keywords[:5]:
        token = kw.get('token', 'N/A')
        weight = kw.get('weight', 0)
        print(f"  - {token} - {weight:.2f}")
    
    print()
    relationships = result.get('relationships', [])
    print(f"🔗 Relacionamentos: {len(relationships)}")
    
    print()
    summary = result.get('summary', {})
    headline = summary.get('headline', 'N/A')
    print(f"📝 Summary: {headline}")
    
    print()
    competitors = result.get('competitors', [])
    print(f"🏆 Competidores: {len(competitors)}")
    for comp in competitors[:3]:
        name = comp.get('name', 'N/A')
        mentions = comp.get('mentions', 0)
        print(f"  - {name} - {mentions} menções")
    
    print()
    print("=" * 80)
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("=" * 80)
    
except Exception as e:
    print()
    print("=" * 80)
    print("❌ ERRO NO TESTE")
    print("=" * 80)
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
