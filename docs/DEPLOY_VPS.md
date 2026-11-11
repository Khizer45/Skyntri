# Put Skyntri live on a server (VPS + Docker + HTTPS)

At the end, anyone can open `https://<your site>`, sign up and run a skin analysis.

```
internet ──► Caddy (ports 80/443, free HTTPS certificates)
                ├── https://SITE_DOMAIN  ──► frontend (React, nginx)
                └── https://API_DOMAIN   ──► backend (FastAPI + TensorFlow) ──► PostgreSQL
```

Everything runs from `docker-compose.prod.yml`. Only Caddy is reachable from outside.

## 1. Get a server

* **Ubuntu 24.04**, at least **4 GB RAM** (8 GB is more comfortable: TensorFlow, PostgreSQL and the image build share it), 40 GB disk.
* Options: Contabo (most RAM for the price), Hetzner Cloud, Vultr, DigitalOcean, AWS Lightsail, Azure. Choose an **x86 (Intel/AMD)** plan, not ARM.
* Prices change often. Check the provider's own pricing page, including VAT and the IPv4 fee.
* **Students:** *Azure for Students* (https://azure.microsoft.com/free/students) gives credit without a credit card. The GitHub Student Developer Pack offers change over time: check https://education.github.com/pack.
* Free hosting such as Render or Railway does not have enough memory for the TensorFlow model.

Write down the server's **public IP address**.

## 2. Two web addresses that point to the server

You need two names: one for the app, one for the API.

* **With your own domain** (for example from Namecheap or Cloudflare), add two DNS **A records** pointing to the server IP:
  * `skyntri.yourdomain.com` (app)
  * `api.skyntri.yourdomain.com` (API)
* **Free, no domain needed:** sslip.io turns the IP into names automatically. For IP `203.0.113.5`:
  * `skyntri.203-0-113-5.sslip.io`
  * `api.203-0-113-5.sslip.io`

## 3. Prepare the server

From your computer, connect to the server:

```bash
ssh root@YOUR_SERVER_IP
```

On the server:

```bash
curl -fsSL https://get.docker.com | sh
```

```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

```bash
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

The swap file keeps the first image build from running out of memory.

## 4. Get the code

```bash
git clone https://github.com/Khizer45/Skyntri.git && cd Skyntri
```

If the repository is private, GitHub asks for a username and a **personal access token** (GitHub → Settings → Developer settings → Personal access tokens) instead of the password.

## 5. Copy the trained models to the server

The `.keras` files are not in git. From **your computer** (Windows PowerShell has `scp` built in):

```bash
scp E:\Skyntri\backend\models\facial_concerns_efficientnet.keras E:\Skyntri\backend\models\facial_concerns_metadata.json root@YOUR_SERVER_IP:/root/Skyntri/backend/models/
```

Add the disease and gate files the same way once they are trained.

## 6. Settings

On the server:

```bash
cp .env.production.example .env
```

```bash
openssl rand -hex 32
```

```bash
openssl rand -hex 24
```

```bash
nano .env
```

Fill in:

* `SITE_DOMAIN` and `API_DOMAIN`, the two names from step 2, without `https://`;
* `ADMIN_EMAILS`, your e-mail;
* `SECRET_KEY`, the first random value;
* `POSTGRES_PASSWORD`, the second random value.

Save with Ctrl+O, Enter, Ctrl+X.

Set `POSTGRES_PASSWORD` before the first start. Changing it later needs the database volume to be reset.

## 7. Start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The first build downloads TensorFlow and takes 10–20 minutes. Follow it with:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Ctrl+C stops following; the app keeps running.

Check:

* `https://API_DOMAIN/health/ready`: `facial_model.artifact_present` is `true`;
* `https://SITE_DOMAIN`: the app opens with a lock icon (HTTPS).

Sign up on the live site with the `ADMIN_EMAILS` address: you get the *Admin panel*. Other people sign up normally and can use Skin Analysis.

**Do this before you share the link.** Sign-up does not verify e-mail addresses, so whoever registers the `ADMIN_EMAILS` address first becomes the administrator. Two safe ways:

* Sign up yourself as the very first thing after the start, or
* leave `ADMIN_EMAILS` empty, sign up with any address, and make that account an administrator from the server:

```bash
docker compose -f docker-compose.prod.yml exec backend python -m app.cli make-admin you@example.com
```

Only someone who can log in to the server can run this command. With Google sign-in set up ([INTEGRATIONS.md](INTEGRATIONS.md)), signing in with Google is safe too, because Google has verified the address.

## Everyday commands (run inside `~/Skyntri`)

| Task | Command |
|---|---|
| Update to the latest code | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |
| New model files copied | `docker compose -f docker-compose.prod.yml restart backend` |
| Status | `docker compose -f docker-compose.prod.yml ps` |
| Backend logs | `docker compose -f docker-compose.prod.yml logs --tail 100 backend` |
| Make someone admin | `docker compose -f docker-compose.prod.yml exec backend python -m app.cli make-admin user@example.com` |
| Database backup | `docker compose -f docker-compose.prod.yml exec -T db pg_dump -U skyntri skyntri > backup-$(date +%F).sql` |
| Stop | `docker compose -f docker-compose.prod.yml down` (data stays) |

## Troubleshooting

* **No HTTPS / certificate error:**
  * Both names must point to the server IP. Check with `ping SITE_DOMAIN`.
  * Ports 80 and 443 must be open. Check the provider's firewall too, not only `ufw`.
  * Look at `docker compose -f docker-compose.prod.yml logs caddy`.
* **"Unsafe production configuration" in the backend log:** `SECRET_KEY` is missing or too weak. Use `openssl rand -hex 32`.
* **App opens but login fails:**
  * `SITE_DOMAIN` and `API_DOMAIN` in `.env` must be exactly the names in the browser.
  * After changing them, rebuild with `docker compose -f docker-compose.prod.yml up -d --build`. The API address is built into the frontend.
* **Skin Analysis says "Not available yet":** the model files are missing in `backend/models/` (step 5). Restart the backend after copying.
* **Server runs out of memory:** use a bigger plan (8 GB) and keep the swap file.

## Before inviting real users

* The app stores users' face photos. Keep the server updated (`apt update && apt upgrade`), make regular database backups and describe on the Privacy page what is stored and for how long.
* Password reset e-mails need SMTP settings in `.env`. Without them, password reset stays off.
* Skin disease screening stays off until an administrator turns it on under **Admin → Settings**. Do that only after a dermatologist has reviewed the model's results.
* Google sign-in, card and PayPal payments, the assistant's language model and n8n are optional: see `docs/INTEGRATIONS.md`.
* See `docs/DEPLOYMENT_RUNBOOK.md` for backups, restore and rollback.
