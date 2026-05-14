# AWS Migration Runbook - Direct Production Cutover

This runbook skips the test-domain phase and cuts directly to production.

Risk level: High
Use this only if you need speed and can tolerate rollback risk.

## Your prefilled values

- Repo: https://github.com/bitdev23/UI_CryptoCEN.git
- Production domain: app.velank.io
- Services: mantraj-api, mantraj-worker

## 1) Pre-cutover checklist (must complete first)

1. Keep old GCP deployment running.
2. Lower DNS TTL for app.velank.io to 60 seconds at least 24h before cutover.
3. Ensure you can edit callbacks in Supabase, Google, LinkedIn, Razorpay.
4. Prepare EC2 instance and Elastic IP.
5. Keep rollback owner and decision rule ready.

## 2) Build AWS server and deploy app

1. Launch EC2 Ubuntu 22.04.
2. Open ports 22, 80, 443.
3. SSH in.
4. Run deploy/aws/aws_migration_commands_direct_prod.sh section by section.
5. Edit /home/mantraj/mantraj/.env and set APP_BASE_URL=https://app.velank.io.
6. Verify services are healthy with systemctl and journal logs.

## 3) Update provider callbacks BEFORE DNS cutover

1. Supabase auth redirect URLs:
- https://app.velank.io/auth/callback

2. Google OAuth redirect URL:
- https://app.velank.io/auth/callback

3. LinkedIn OAuth redirect URL:
- https://app.velank.io/auth/callback

4. Payment webhook callback URL:
- Update to production AWS domain endpoint.

## 4) DNS cutover

1. Change app.velank.io A record to AWS Elastic IP.
2. Wait for propagation (usually minutes with low TTL).
3. Run certbot on EC2:

```bash
sudo certbot --nginx -d app.velank.io --non-interactive --agree-tos -m admin@app.velank.io --redirect
```

4. Reload nginx and restart services:

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart mantraj-api mantraj-worker
```

## 5) Immediate smoke tests (first 15 minutes)

1. Open https://app.velank.io
2. Login with email/password.
3. Login with Google.
4. Open dashboard and generate a post.
5. Run schedule action and confirm worker processes the job.
6. Verify admin page key actions.

Logs:

```bash
sudo journalctl -u mantraj-api -f
sudo journalctl -u mantraj-worker -f
```

## 6) Rollback (if critical issue lasts >10 minutes)

1. Repoint app.velank.io DNS back to previous GCP endpoint.
2. Verify app recovers on old infrastructure.
3. Keep AWS up for debugging.
4. Retry only after root cause is fixed.

## 7) What usually breaks in direct cutover

1. OAuth callback URL mismatch.
2. APP_BASE_URL incorrect.
3. Missing env variable in AWS .env.
4. Redis connectivity issues for worker.
5. TLS issuance attempted before DNS propagation.

## 8) Cost expectation (same as standard AWS migration)

Hosting-only approximate monthly:
- t3.medium single box: USD 45-60
- t3.large single box: USD 75-95
- split API+worker: USD 65-110

External service costs are separate (Supabase, Redis provider, LLM APIs, email, billing).
