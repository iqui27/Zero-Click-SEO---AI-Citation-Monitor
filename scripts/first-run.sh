#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "# Criando .env mínimo para Sandbox" >&2
  cat > .env <<EOF
# Preencha chaves conforme necessário; em branco mantém Sandbox ativo
PERPLEXITY_API_KEY=
GOOGLE_API_KEY=
OPENAI_API_KEY=
SERPAPI_KEY=
EOF
  echo ".env criado. Você pode colar chaves depois em Settings." >&2
else
  echo ".env já existe; nada a fazer." >&2
fi

echo "Subindo containers..." >&2
docker compose up -d --build

echo "Abra http://localhost:5173 (o wizard redireciona se nenhum projeto estiver configurado)." >&2
