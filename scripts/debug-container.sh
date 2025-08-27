#!/bin/bash
# Script para debug do container API que está reiniciando

echo "=== Debug Container API - $(date) ==="

cd /opt/seo-analyzer

echo "1. Status dos containers:"
sudo docker compose -f docker-compose.prod.yml ps

echo -e "\n2. Logs do container API (últimas 100 linhas):"
sudo docker compose -f docker-compose.prod.yml logs --tail=100 api

echo -e "\n3. Verificando variáveis de ambiente:"
sudo docker compose -f docker-compose.prod.yml exec -T api env | grep -E "(DATABASE_URL|REDIS_URL|SECRET_KEY)" || echo "Container não está rodando"

echo -e "\n4. Testando conexão com banco:"
sudo docker compose -f docker-compose.prod.yml exec -T api python -c "
try:
    from app.core.config import settings
    print(f'DATABASE_URL configurada: {settings.database_url[:50]}...')
    
    from app.db.session import engine
    with engine.connect() as conn:
        result = conn.execute('SELECT 1')
        print('✅ Conexão com banco OK')
except Exception as e:
    print(f'❌ Erro na conexão: {e}')
" 2>/dev/null || echo "❌ Container não consegue executar Python"

echo -e "\n5. Verificando se o processo está rodando:"
sudo docker compose -f docker-compose.prod.yml exec -T api ps aux || echo "Container não está rodando"

echo -e "\n6. Recursos do sistema:"
echo "Memória:"
free -h
echo "Disco:"
df -h /opt/seo-analyzer

echo -e "\n=== Fim do Debug ==="
