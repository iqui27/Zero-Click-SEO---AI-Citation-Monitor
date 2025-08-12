# Secret handling and environment setup

This project uses environment variables for all credentials and sensitive configuration. Do NOT commit secrets to the repository. Only example files with placeholders are tracked.

Files provided:
- .env.example — safe template with required keys and placeholders.

Never commit:
- .env
- Any files containing real keys, passwords, tokens, or connection strings.

Git ignore is already configured to ignore .env and .env.* while allowing *.example templates.

Required keys
- POSTGRES_PASSWORD — PostgreSQL password used by the managed instance/container.
- REDIS_URL — Connection URL for Redis (e.g., redis://redis:6379/0 or a managed instance URL).
- OPENAI_API_KEY — API key for OpenAI usage.
- GOOGLE_API_KEY — API key for Gemini/Google Generative AI.
- PERPLEXITY_API_KEY — API key for Perplexity API.
- SERPAPI_KEY — API key for SerpAPI fallback.
- VITE_API_BASE — Base path/URL the frontend uses to reach the API (e.g., /api or https://api.example.com).
- CORS_ORIGINS — Comma-separated list of allowed origins for the API (e.g., https://app.example.com,https://www.example.com). Leave empty for local dev or set explicitly in production.

Create the real .env only on the droplet (via MCP SSH)
Use your MCP action to execute remote commands on the droplet over SSH and create the .env file directly on the server. Example flow:
1) Connect via the MCP SSH action to your production droplet.
2) Create the file at the project root and set secure values via a non-interactive heredoc:

   cat > .env <<'ENV'
   POSTGRES_PASSWORD={{POSTGRES_PASSWORD}}
   REDIS_URL={{REDIS_URL}}
   OPENAI_API_KEY={{OPENAI_API_KEY}}
   GOOGLE_API_KEY={{GOOGLE_API_KEY}}
   PERPLEXITY_API_KEY={{PERPLEXITY_API_KEY}}
   SERPAPI_KEY={{SERPAPI_KEY}}
   VITE_API_BASE={{VITE_API_BASE}}
   CORS_ORIGINS={{CORS_ORIGINS}}
   ENV

3) Ensure correct permissions:

   chmod 600 .env

4) Restart services to load the new environment:

   docker compose --env-file .env up -d --build

Notes
- Replace {{...}} placeholders with values sourced from your secure secret store or MCP-managed secrets. Do not paste secrets into chat or commit them.
- For local development, you may copy .env.example to .env and fill it locally. Keep .env out of version control.
- The backend also accepts DATABASE_URL via container env; POSTGRES_PASSWORD is included here for DB container configuration where applicable.

