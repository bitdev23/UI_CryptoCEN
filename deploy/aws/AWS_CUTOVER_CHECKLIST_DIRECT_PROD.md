# Direct Production Cutover Checklist

Use this if skipping test-domain deployment.

## A) Go/No-Go before DNS switch

- [ ] EC2 up and reachable via SSH.
- [ ] API service healthy (`mantraj-api`).
- [ ] Worker service healthy (`mantraj-worker`).
- [ ] Nginx config valid (`nginx -t`).
- [ ] All required env vars set in /home/mantraj/mantraj/.env.
- [ ] APP_BASE_URL set to https://app.velank.io.
- [ ] Supabase callback URL updated.
- [ ] Google callback URL updated.
- [ ] LinkedIn callback URL updated.
- [ ] Razorpay/webhooks updated if applicable.
- [ ] GCP old deployment still running for rollback.

## B) Cutover execution

- [ ] Update DNS A record app.velank.io -> AWS Elastic IP.
- [ ] Wait DNS propagation.
- [ ] Run certbot for app.velank.io.
- [ ] Reload nginx.
- [ ] Restart API and worker services.

## C) Validation (must all pass)

- [ ] Homepage loads over HTTPS.
- [ ] Email login works.
- [ ] Google login works.
- [ ] Dashboard loads data.
- [ ] Post generation works.
- [ ] Worker executes jobs.
- [ ] No repeating errors in API logs.
- [ ] No repeating errors in worker logs.

## D) Rollback trigger

Rollback if any critical function fails >10 minutes:

- [ ] Login broken.
- [ ] Post generation unavailable.
- [ ] Worker queue not processing.
- [ ] Repeated 5xx errors.

## E) Rollback action

- [ ] Point DNS back to GCP.
- [ ] Confirm service recovery.
- [ ] Keep AWS running and diagnose.
