Supabase backup job for GCP
===========================

Overview
--------
This folder contains a small Cloud Run job (container) that performs a Postgres dump of your Supabase database and uploads it to a GCS bucket. Backups are intended to be scheduled daily via Cloud Scheduler or Cloud Run Jobs and retained by a GCS lifecycle rule (7 days retention).

What it does
- Dumps the Postgres DB using `pg_dump -Fc` to a timestamped file
- Uploads the dump to the configured `GCS_BUCKET` under `BACKUP_PREFIX`

Important: This container only backs up the Postgres database. For Storage (user-uploaded files) you should either:
- Use the Supabase dashboard to copy/download buckets, or
- Use `supabase` CLI / `rclone` in a separate job to copy storage buckets into GCS.

Environment variables (set via Secret Manager or Cloud Run settings)
- `SUPABASE_DB_URL` — required. Postgres connection string (libpq/URI). Example: `postgresql://postgres:password@db.host:5432/postgres`
- `GCS_BUCKET` — required. Example: `gs://velank-supabase-backups`
- `BACKUP_PREFIX` — optional. Default: `supabase-backups`
- `GOOGLE_APPLICATION_CREDENTIALS` — optional on Cloud Run; use service account identity instead.

Build & deploy (Cloud Build + Cloud Run)
1. Build & push image with Cloud Build:
   ```bash
   gcloud builds submit --config cloudrun/backup/cloudbuild.yaml . --project=YOUR_PROJECT_ID
   ```
2. Deploy to Cloud Run (allow unauthenticated = false):
   ```bash
   gcloud run deploy supabase-backup --image gcr.io/YOUR_PROJECT_ID/supabase-backup:latest \
     --region=us-east1 --platform=managed --no-allow-unauthenticated \
     --set-env-vars=GCS_BUCKET=gs://your-bucket,SUPABASE_DB_URL='<REDACTED>'
   ```

Schedule (Cloud Scheduler) — trigger Cloud Run via authenticated HTTP
1. Create a service account with Cloud Run Invoker role and add its key to Secret Manager.
2. Create a Cloud Scheduler job that triggers the Cloud Run service daily and uses OIDC token with the service account.

Retention
---------
Use GCS lifecycle rules to delete objects older than 7 days. Example:
```json
{
  "rule": [
    {
      "action": { "type": "Delete" },
      "condition": { "age": 7 }
    }
  ]
}
```
Apply with:
```bash
gsutil lifecycle set lifecycle.json gs://your-bucket
```

Security notes
- Store `SUPABASE_DB_URL` and `SUPABASE_SERVICE_ROLE_KEY` in Secret Manager; do NOT put them directly in Cloud Run env if possible.
- Use a dedicated service account with minimal permissions (Cloud Run invoker + write to the GCS backup bucket).
