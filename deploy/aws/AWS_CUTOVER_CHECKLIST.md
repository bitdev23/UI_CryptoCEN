# AWS Cutover Checklist (Go/No-Go)

Use this exactly during migration window.
Mark each line as done before moving on.

## A) Pre-cutover (must all be YES)

- [ ] EC2 instance healthy and reachable over SSH.
- [ ] Elastic IP attached.
- [ ] API service running (`mantraj-api`).
- [ ] Worker service running (`mantraj-worker`).
- [ ] Nginx config test passes (`nginx -t`).
- [ ] HTTPS works on test domain.
- [ ] Login works on test domain.
- [ ] Post generation works on test domain.
- [ ] Scheduling + worker execution works on test domain.
- [ ] Supabase callback URLs include AWS test + prod URLs.
- [ ] Google OAuth callback URLs include AWS test + prod URLs.
- [ ] LinkedIn callback URLs include AWS test + prod URLs.
- [ ] Payment/webhook callback target prepared for prod switch.
- [ ] `.env` on AWS has all production values.
- [ ] GCP old stack remains online for rollback.

## B) Go-live actions (in order)

- [ ] Set `APP_BASE_URL=https://app.velank.io` on AWS `.env`.
- [ ] Update Nginx `server_name` to `app.velank.io`.
- [ ] Obtain/renew SSL cert for `app.velank.io`.
- [ ] Restart API and worker services.
- [ ] Confirm services healthy after restart.
- [ ] Change DNS A record `app.velank.io` -> AWS Elastic IP.
- [ ] Wait for DNS propagation (TTL dependent).

## C) Immediate validation after DNS switch

- [ ] App home page opens over HTTPS.
- [ ] Login with email/password works.
- [ ] Google login works.
- [ ] Dashboard loads data from Supabase.
- [ ] Post generate endpoint works.
- [ ] Scheduler actions work.
- [ ] Worker consumes and completes jobs.
- [ ] No spike in API 5xx errors.
- [ ] No spike in worker errors.

## D) Monitor for first 2 hours

- [ ] `journalctl -u mantraj-api -f` clean (no critical errors).
- [ ] `journalctl -u mantraj-worker -f` clean (no repeated failures).
- [ ] OAuth callback errors absent.
- [ ] Redis connectivity stable.
- [ ] User reports normal.

## E) Rollback trigger conditions

Rollback immediately if any of these persist > 10-15 min:

- [ ] Login consistently failing for users.
- [ ] Post generation unavailable.
- [ ] Worker queue stuck/unprocessed.
- [ ] Repeated 502/503/504 from Nginx/API.

## F) Rollback steps

- [ ] Repoint DNS `app.velank.io` to previous GCP target.
- [ ] Confirm old stack serves traffic again.
- [ ] Keep AWS running for debugging.
- [ ] Record root cause before next attempt.

## G) Post-stabilization (within 48h)

- [ ] Keep GCP stack as fallback for 48h.
- [ ] Add CloudWatch alarms (CPU, memory, errors).
- [ ] Snapshot EC2/EBS.
- [ ] Restrict SSH to fixed office IP if possible.
- [ ] Document final architecture and credentials owner list.
