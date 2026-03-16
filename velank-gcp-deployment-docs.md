# Velank / Mantraj AI — GCP Deployment Documentation
> This document describes the EXACT deployment approach used for Mantraj AI on Google Cloud Platform.
> **We did NOT use Docker.** We deployed directly on Ubuntu using Python virtualenv + gunicorn + systemd + nginx.
> Share this with any LLM or developer before making changes to avoid breaking the setup.

---

## IMPORTANT: No Docker

We deliberately chose NOT to use Docker. The deployment is:
```
Python app → gunicorn WSGI server → systemd service → nginx reverse proxy
```
There is no Dockerfile, no docker-compose.yml, no containers running.
Although a Dockerfile exists in the repo (legacy), it is NOT used in production.

---

## 1. What We Built

**Product:** Mantraj AI — LinkedIn content generation SaaS
**Live URL:** https://app.velank.io
**Landing page:** https://velank.io (separate, on Hostinger — not this server)
**GitHub repo:** https://github.com/bitdev23/UI_CryptoCEN

---

## 2. Server Details

| Field | Value |
|---|---|
| Cloud provider | Google Cloud Platform (GCP) |
| VM name | mantraj-server |
| GCP account | bhavikk.vala@gmail.com |
| Machine type | e2-standard-2 (2 vCPU, 1 core, 8 GB RAM) |
| Region / Zone | us-east1-b (South Carolina, USA) |
| Operating system | Ubuntu 22.04.5 LTS |
| Disk | 40 GB Balanced persistent disk |
| External IP | 34.75.246.129 (static) |
| Internal IP | 10.142.0.2 |
| Firewall | HTTP port 80 + HTTPS port 443 open |
| GCP credits | ~$300 / Rs.27,287 — expires June 11 2026 |

---

## 3. Server Users

The VM has two Linux users:

| User | Purpose |
|---|---|
| bhavikk_vala | SSH login user (auto-created by GCP/Google) |
| mantraj | App user — owns all application files and runs the services |

**SSH into server:**
```bash
ssh -i ~/.ssh/id_ed25519 bhavikk_vala@34.75.246.129
sudo su - mantraj   # always switch to mantraj user after SSH
```

SSH key location on Mac: `~/.ssh/id_ed25519`

---

## 4. Application Files Location

All application files live at:
```
/home/mantraj/mantraj/
```

Full structure:
```
/home/mantraj/mantraj/
├── app.py                  ← Flask API server (runs via gunicorn on port 5050)
├── worker.py               ← RQ background worker (KB training jobs)
├── requirements.txt        ← Python dependencies
├── .env                    ← Production environment variables (never commit)
├── venv/                   ← Python virtual environment
│   └── bin/
│       ├── gunicorn        ← WSGI server binary
│       └── python          ← Python interpreter
├── templates/              ← Jinja2 HTML templates
├── database/               ← DB schema and migrations
├── data/                   ← Data files
├── auth.py
├── config.py
├── kb_jobs.py
├── pdf_processor.py
├── rag_system_pgvector.py
└── ...other modules
```

**App runs on port 5050** — not 8000, not 5000, not 3000. Always 5050.

---

## 5. How the App Runs — Two Systemd Services

The app runs as two permanent background services managed by systemd.
Both auto-start on server reboot and auto-restart on crash.

### Service 1: mantraj-api (the Flask web server)

File: `/etc/systemd/system/mantraj-api.service`

```ini
[Unit]
Description=Mantraj API Server
After=network.target

[Service]
User=mantraj
WorkingDirectory=/home/mantraj/mantraj
ExecStart=/home/mantraj/mantraj/venv/bin/gunicorn app:app -w 2 -b 0.0.0.0:5050
Restart=always
RestartSec=3
EnvironmentFile=/home/mantraj/mantraj/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- Runs gunicorn with 2 worker processes
- Binds to port 5050 on all interfaces
- Reads all environment variables from `.env`
- Restarts automatically if it crashes

### Service 2: mantraj-worker (the background job worker)

File: `/etc/systemd/system/mantraj-worker.service`

```ini
[Unit]
Description=Mantraj RQ Worker
After=network.target

[Service]
User=mantraj
WorkingDirectory=/home/mantraj/mantraj
ExecStart=/home/mantraj/mantraj/venv/bin/python worker.py
Restart=always
RestartSec=3
EnvironmentFile=/home/mantraj/mantraj/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

- Runs worker.py directly using the venv Python
- Listens to Redis queue named `kb_training`
- Processes PDF embedding/chunking jobs in the background
- Restarts automatically if it crashes

### Service Management Commands

```bash
# Check status
sudo systemctl status mantraj-api
sudo systemctl status mantraj-worker

# Restart (use after every code deploy)
sudo systemctl restart mantraj-api mantraj-worker

# Stop
sudo systemctl stop mantraj-api mantraj-worker

# Start
sudo systemctl start mantraj-api mantraj-worker

# View live logs
sudo journalctl -u mantraj-api -f
sudo journalctl -u mantraj-worker -f

# View last 50 lines
sudo journalctl -u mantraj-api -n 50
sudo journalctl -u mantraj-worker -n 50

# Reload after editing service files
sudo systemctl daemon-reload
```

---

## 6. Nginx Configuration

Nginx acts as a reverse proxy — it receives all HTTP/HTTPS traffic on ports 80/443
and forwards it to the Flask app running on port 5050 internally.

File: `/etc/nginx/sites-available/mantraj`
Symlinked to: `/etc/nginx/sites-enabled/mantraj`

```nginx
server {
    listen 80;
    server_name app.velank.io;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name app.velank.io;

    ssl_certificate /etc/letsencrypt/live/app.velank.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.velank.io/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 55M;
        proxy_read_timeout 120;
        proxy_connect_timeout 120;
    }
}
```

HTTP (port 80) redirects to HTTPS (port 443) automatically.
SSL certificate issued by Let's Encrypt via certbot. Auto-renews.

```bash
# After editing nginx config:
sudo nginx -t              # test config
sudo systemctl reload nginx  # apply changes
```

---

## 7. SSL Certificate

- Provider: Let's Encrypt (free)
- Tool: Certbot
- Domain: app.velank.io
- Certificate location: `/etc/letsencrypt/live/app.velank.io/`
- Expiry: June 11 2026
- Auto-renewal: configured by certbot (runs in background)

To manually renew:
```bash
sudo certbot renew
```

---

## 8. External Services

### Database — Supabase (PostgreSQL)
| Field | Value |
|---|---|
| Provider | Supabase |
| URL | https://bwlkhowkhqkjjjhkrpmd.supabase.co |
| Purpose | Stores all user data, posts, KB files, chunks |
| Plan | Free tier |

### Job Queue — Upstash Redis
| Field | Value |
|---|---|
| Provider | Upstash |
| Endpoint | magical-robin-69761.upstash.io |
| Port | 6379 |
| TLS | Enabled (ssl=True in Redis client) |
| Purpose | Queue between app.py and worker.py for KB training jobs |
| Queue name | kb_training |
| Plan | Free tier |

**Critical:** worker.py connects to Redis with `ssl=True` and `password` parameter.
Without SSL the connection to Upstash will fail.

### DNS — Hostinger / Velank.io domain
- `velank.io` → landing page on Hostinger shared hosting
- `app.velank.io` → A record pointing to `34.75.246.129` (GCP VM)

---

## 9. How to Deploy Code Updates

Every time you make changes on your Mac:

**Step 1 — Push from Mac:**
```bash
cd /Users/macbookair/Documents/UI_CryptoCEN
git add .
git commit -m "describe your change"
git push
```

**Step 2 — Pull on server:**
```bash
ssh -i ~/.ssh/id_ed25519 bhavikk_vala@34.75.246.129
sudo su - mantraj
cd /home/mantraj/mantraj
git pull
source venv/bin/activate
pip install -r requirements.txt   # skip if requirements.txt unchanged
sudo systemctl restart mantraj-api mantraj-worker
```

---

## 10. Environment Variables

All environment variables are stored in `/home/mantraj/mantraj/.env`
This file is read by both systemd services via `EnvironmentFile=` directive.

Key variables:
```dotenv
# AI Providers
AI_PROVIDER=google
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...

# Supabase
SUPABASE_URL=https://bwlkhowkhqkjjjhkrpmd.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# Redis (Upstash — SSL required)
REDIS_HOST=magical-robin-69761.upstash.io
REDIS_PORT=6379
REDIS_PASSWORD=...
REDIS_DB=0
RQ_SIMPLE_WORKER=false

# Payments
RAZORPAY_KEY_ID=rzp_test_...       # switch to live before launch
RAZORPAY_KEY_SECRET=...
STRIPE_PUBLIC_KEY=pk_test_placeholder   # set up Stripe before launch
STRIPE_SECRET_KEY=sk_test_placeholder

# Pricing — INR (Indian users via Razorpay)
PLAN_PRICE_1_MONTH_INR=500
PLAN_PRICE_3_MONTH_INR=1199
PLAN_PRICE_12_MONTH_INR=3600

# Pricing — USD (International users via Stripe)
PLAN_PRICE_1_MONTH_USD=29
PLAN_PRICE_3_MONTH_USD=59
PLAN_PRICE_12_MONTH_USD=199

# Flask
FLASK_SECRET_KEY=463246c8dee629...
APP_BASE_URL=https://app.velank.io
FLASK_ENV=production
```

To update .env on server:
```bash
nano /home/mantraj/mantraj/.env
# edit → Ctrl+X → Y → Enter
sudo systemctl restart mantraj-api mantraj-worker
```

---

## 11. OAuth Configuration

### Google OAuth
- Project: mantraj-ai (on bhavik.valtrilabs@gmail.com account)
- **DO NOT touch this account** — it handles all Google login

Authorized JavaScript Origins:
```
http://localhost:5050
http://127.0.0.1:5050
https://app.velank.io
```

Authorized Redirect URIs:
```
http://localhost:5050/auth/callback
http://127.0.0.1:5050/auth/callback
https://bwlkhowkhqkjjjhkrpmd.supabase.co/auth/v1/callback
https://app.velank.io/auth/callback
```

### Supabase Auth
- Site URL: `https://app.velank.io`
- Redirect URLs:
```
http://127.0.0.1:5050/auth/callback
http://localhost:5050/auth/callback
http://127.0.0.1:5050/**
http://localhost:5050/**
http://localhost:3000/**
https://cornflowerblue-mantis-137350.hostingersite.com/**
https://app.velank.io/auth/callback
```

---

## 12. Flask Session Configuration

Added to `app.py` after `app.secret_key` line to fix HTTPS session cookies:

```python
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
```

---

## 13. Installed Packages on Server

```bash
# System packages
python3, python3-pip, python3-venv
nginx
certbot, python3-certbot-nginx
git
ufw

# Firewall rules
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enabled
```

Python dependencies: see `requirements.txt` in repo.
Installed in virtualenv at `/home/mantraj/mantraj/venv/`

---

## 14. Traffic Flow

```
User browser
     ↓ HTTPS port 443
Nginx (reverse proxy)
     ↓ HTTP port 5050 (internal only)
Gunicorn (2 workers)
     ↓
Flask app (app.py)
     ↓              ↓
Supabase DB    Redis Queue
               ↓
           worker.py
               ↓
           Supabase DB
```

---

## 15. Pre-Launch Checklist

```
[ ] Switch Razorpay test keys → live keys
[ ] Set up Stripe account + create products/prices
[ ] Add real Stripe keys to .env
[ ] Configure LinkedIn OAuth credentials
[ ] Set up GCP billing alert at Rs.24,000
[ ] Rotate all API keys (were exposed during setup)
[ ] Plan Hetzner migration at day 80 (before June 11 2026)
```

---

## 16. Hetzner Migration Plan (Before June 11 2026)

GCP credits expire June 11 2026. Migrate to Hetzner CX22 at day 80-85.

```
Hetzner CX22 specs: 2 vCPU dedicated AMD, 4GB RAM, 80GB NVMe, 20TB bandwidth
Cost: €6.49/month (~Rs.600/month)
Region: US East (Ashburn)

Migration steps:
1. Spin up Hetzner CX22
2. git clone + pip install + copy .env
3. Set up same nginx + certbot + systemd
4. Test via new IP
5. Change DNS A record: app.velank.io → new Hetzner IP
6. Wait 30 mins, verify traffic
7. Stop GCP VM
```

---

## Summary — What We Used vs What We Didn't

| Approach | Used? | Notes |
|---|---|---|
| Docker | ❌ NO | Dockerfile in repo is legacy, not used |
| docker-compose | ❌ NO | Not used |
| gunicorn | ✅ YES | WSGI server for Flask |
| systemd | ✅ YES | Keeps both services running permanently |
| nginx | ✅ YES | Reverse proxy + SSL termination |
| certbot | ✅ YES | Free SSL from Let's Encrypt |
| virtualenv | ✅ YES | Python dependencies isolated in venv/ |
| Redis | ✅ YES | Upstash hosted Redis for RQ job queue |
| Supabase | ✅ YES | PostgreSQL database |
| Railway | ❌ NO | Considered but not used |
| Render | ❌ NO | Considered but not used |
