# HTTPS / TLS with Nginx (Phase 8.2)

Terminate TLS at Nginx in front of the production Compose stack. Application containers stay on the internal network; only **80** (redirect / ACME) and **443** are published.

## Files

| Path | Role |
|------|------|
| `nginx/nginx.tls.conf` | HTTPS server + HTTP→HTTPS redirect + ACME webroot |
| `nginx/Dockerfile.tls` | Image that bakes `nginx.tls.conf` |
| `docker-compose.prod.tls.yml` | Overlay: TLS image, ports 80/443, `./certs` mount |

Plain HTTP (no TLS): use `docker-compose.prod.yml` alone ([COMPOSE_PROD.md](COMPOSE_PROD.md)).

## Certificate layout

Nginx expects:

```text
certs/
  fullchain.pem   # certificate + intermediates (or self-signed cert)
  privkey.pem     # private key
```

Override the host directory with `TLS_CERTS_DIR` if needed.

Do **not** commit real private keys. `certs/` should stay local / in your secret store (see `.gitignore`).

## Path A — Local self-signed (smoke test)

```bash
mkdir -p certs
./scripts/gen-dev-certs.sh
# Windows: .\scripts\gen-dev-certs.ps1

# .env.production must use https URLs, e.g.:
#   FRONTEND_URL=https://localhost
#   NEXT_PUBLIC_API_URL=https://localhost
#   ALLOWED_HOSTS=localhost

docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.tls.yml \
  --env-file .env.production \
  up -d --build

curl -kfsS https://localhost/api/v1/ops/ready
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost/   # expect 301
```

Browsers will warn on self-signed certs — that is expected for local smoke tests.

## Path B — Let's Encrypt (public hostname)

Assumes DNS for `yourdomain.com` (and API host if split) points at this machine, and ports **80/443** are reachable.

### 1. Bootstrap HTTP first (optional)

Bring up prod Compose without TLS, or use the TLS image with a temporary self-signed cert so Nginx can serve `/.well-known/acme-challenge/`.

### 2. Issue certificates (certbot on host)

```bash
# Example: webroot mode against the running nginx ACME location
sudo certbot certonly --webroot -w /var/lib/raginspector/certbot \
  -d yourdomain.com -d api.yourdomain.com
```

Or use standalone briefly (stop nginx port 80), then copy:

```bash
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/fullchain.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/privkey.pem
sudo chown "$USER" ./certs/*.pem
```

### 3. Env URLs

```bash
FRONTEND_URL=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://yourdomain.com          # or https://api.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
```

Rebuild frontend after changing `NEXT_PUBLIC_*` (baked at image build time).

### 4. Start TLS stack

```bash
docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.tls.yml \
  --env-file .env.production \
  up -d --build
```

### 5. Renew

Certbot renew + copy into `./certs` (or point `TLS_CERTS_DIR` at `/etc/letsencrypt/live/...` with a deploy hook that reloads nginx):

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.prod.tls.yml \
  --env-file .env.production exec nginx nginx -s reload
```

## Path C — External TLS (Cloudflare / LB)

If Cloudflare or a cloud load balancer terminates HTTPS:

1. Keep `docker-compose.prod.yml` on **HTTP :80** only (no TLS overlay).
2. Set `FRONTEND_URL` / `NEXT_PUBLIC_API_URL` to `https://…`.
3. Ensure the proxy sets `X-Forwarded-Proto: https` (Cloudflare does).
4. App HSTS / secure cookies still assume HTTPS at the browser.

## Security notes

- HSTS is enabled in `nginx.tls.conf` (`max-age=31536000`). Only enable after HTTPS works end-to-end.
- Prefer TLS 1.2+ (configured).
- Backend CORS matches `FRONTEND_URL` exactly — use `https://` with no trailing slash ([SECURITY.md](../SECURITY.md)).
- Private keys in `./certs` are host files; restrict permissions (`chmod 600 certs/privkey.pem`).

## Verify checklist

- [ ] `https://…/health` or `/api/v1/ops/ready` returns OK
- [ ] `http://…` redirects to `https://`
- [ ] Login / dashboard load over HTTPS
- [ ] Razorpay webhook URL uses `https://`
- [ ] `FRONTEND_URL` and `NEXT_PUBLIC_API_URL` are `https://`

## Related

- [COMPOSE_PROD.md](COMPOSE_PROD.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [SECURITY.md](../SECURITY.md)
