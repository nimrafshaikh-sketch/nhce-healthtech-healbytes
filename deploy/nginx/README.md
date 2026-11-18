# Nginx Reverse Proxy & TLS Setup

`deploy/nginx/healbytes.conf` terminates TLS on port `443`, redirects HTTP (`:80`) to HTTPS, serves the production React SPA bundle built by `Dockerfile.frontend`, proxies `/api/` to Django (`backend:8000`), and exposes only the JWT-authenticated Copilot routes (`/ai/api/v1/agents/`) from `ai_engine:8001` while keeping internal scoring endpoints private on the Docker network.

## TLS Certificates
Place your certificate and private key (ignored by `.gitignore`) under `deploy/nginx/certs/`:
- `deploy/nginx/certs/fullchain.pem`
- `deploy/nginx/certs/privkey.pem`

For local HTTPS testing, generate a self-signed certificate:
```bash
mkdir -p deploy/nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deploy/nginx/certs/privkey.pem \
  -out deploy/nginx/certs/fullchain.pem \
  -subj "/CN=localhost"
```

## Launching the Production Profile
```bash
# Build frontend + start backend, celery_worker, celery_beat, ai_engine, and nginx
docker compose --profile prod up -d --build
```

When deploying behind Nginx on a real domain (e.g. `https://app.example.com`), build the frontend with:
- `VITE_API_BASE_URL=/api`
- `VITE_AI_ENGINE_URL=/ai`
- `VITE_USE_MOCK_DATA=false`

