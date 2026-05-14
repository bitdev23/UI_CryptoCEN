# AWS Migration Runbook (Beginner Friendly)

This runbook migrates your app from GCP to AWS with the least risk.

It is designed for your current stack:
- Gunicorn API service (`mantraj-api`)
- Python worker service (`mantraj-worker`)
- Nginx reverse proxy
- External services unchanged (Supabase, Redis, LLM APIs)

## 0) What success looks like

- Your app loads on AWS over HTTPS.
- Login works (email + Google).
- Post generation works.
- Scheduler/worker jobs run.
- Domain `app.velank.io` points to AWS instance.
- No major errors in API or worker logs.

## 1) Prerequisites (do this before touching AWS)

1. AWS account with EC2 access.
2. Domain DNS access for `app.velank.io`.
3. Access to Supabase, Google OAuth, LinkedIn developer app, Razorpay webhooks.
4. Existing production env values available from your current setup.
5. A maintenance window of at least 60-90 minutes.

## 2) Create AWS server

1. Open AWS Console -> EC2 -> Launch Instance.
2. Select Ubuntu 22.04 LTS.
3. Instance type: start with `t3.medium`.
4. Key pair: create/download `.pem`.
5. Storage: 60 GB gp3.
6. Security Group inbound:
   - 22 (SSH) from your IP only
   - 80 (HTTP) from Anywhere
   - 443 (HTTPS) from Anywhere
7. Launch instance.
8. Allocate and attach Elastic IP.

## 3) Create test DNS

1. In your DNS provider, create A record:
   - Name: `aws-test.app.velank.io`
   - Value: your EC2 Elastic IP
2. Wait for DNS propagation.

## 4) Connect to server

From your Mac terminal:

```bash
chmod 400 /path/to/your-key.pem
ssh -i /path/to/your-key.pem ubuntu@YOUR_ELASTIC_IP
```

## 5) Run migration commands on EC2

Use the command file in this repo:
- `deploy/aws/aws_migration_commands.sh`

Steps:
1. Upload/pull latest repo on EC2.
2. Open script and confirm the prefilled values are correct for your cutover:
  - Repo URL: `https://github.com/bitdev23/UI_CryptoCEN.git`
  - Test domain: `aws-test.app.velank.io`
  - Prod domain: `app.velank.io`
3. Run section-by-section (recommended), not blindly all at once.

## 6) Fill environment file correctly

On EC2, edit:

```bash
sudo -u mantraj nano /home/mantraj/mantraj/.env
```

Minimum critical keys to verify:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `APP_BASE_URL` (test first: `https://aws-test.app.velank.io`)
- Redis values (`REDIS_URL` or host/port/password)
- LLM API keys in use
- LinkedIn keys
- Razorpay keys/webhook secret
- Flask secret keys

## 7) Validate services

Run:

```bash
sudo systemctl status mantraj-api --no-pager
sudo systemctl status mantraj-worker --no-pager
sudo journalctl -u mantraj-api -n 100 --no-pager
sudo journalctl -u mantraj-worker -n 100 --no-pager
```

If either service fails, fix before proceeding.

## 8) Validate app on test domain

Open:
- `https://aws-test.app.velank.io`

Check all:
1. Login page loads.
2. Email/password login works.
3. Google login works.
4. Dashboard loads.
5. Generate post works.
6. Schedule post works.
7. Worker executes jobs.

## 9) Update callback URLs (high-risk step)

Before production cutover, add AWS URLs to providers.

1. Supabase auth redirect URLs:
- `https://aws-test.app.velank.io/auth/callback`
- `https://app.velank.io/auth/callback`

2. Google OAuth redirect URLs:
- `https://aws-test.app.velank.io/auth/callback`
- `https://app.velank.io/auth/callback`

3. LinkedIn OAuth redirect URLs:
- `https://aws-test.app.velank.io/auth/callback`
- `https://app.velank.io/auth/callback`

4. Razorpay/webhooks:
- Ensure webhook target can be switched to AWS domain.

## 10) Production cutover

1. In `.env`, set:
- `APP_BASE_URL=https://app.velank.io`

2. Update Nginx to production domain.
3. Issue production cert for `app.velank.io`.
4. Restart API + worker.
5. Change DNS A record for `app.velank.io` to EC2 Elastic IP.

## 11) Post-cutover validation (first 2 hours)

1. Verify home/login/dashboard.
2. Verify OAuth logins.
3. Verify generation endpoint latency/errors.
4. Verify scheduler and worker queue completion.
5. Verify billing webhook events.
6. Keep log tails open:

```bash
sudo journalctl -u mantraj-api -f
sudo journalctl -u mantraj-worker -f
```

## 12) Rollback plan (if major issue)

1. Repoint DNS `app.velank.io` back to old GCP target.
2. Wait TTL propagation.
3. Confirm service restored on old stack.
4. Investigate AWS issue and retry in next window.

Keep GCP live for at least 48 hours after cutover.

## 13) Common failures and fixes

1. OAuth error `redirect_uri_mismatch`
- Fix provider callback URL list.

2. Login fails after cutover
- Verify `APP_BASE_URL` and Supabase redirect config.

3. Worker not processing jobs
- Check `mantraj-worker` status/logs and Redis connection variables.

4. 502/504 from Nginx
- Check gunicorn service running on `127.0.0.1:5050`.

5. SSL certificate issue
- Re-run certbot and confirm domain points to this EC2 IP.

## 14) Approx AWS cost (hosting only)

- Single EC2 (`t3.medium`) + EBS + normal transfer:
  - About USD 45-60/month
- Bigger single EC2 (`t3.large`):
  - About USD 75-95/month
- Split API + worker EC2:
  - About USD 65-110/month

These do not include Supabase, Redis provider, LLM APIs, email, payment gateway charges.
