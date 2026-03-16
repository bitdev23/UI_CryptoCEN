#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for Supabase DB backup job.
# Expects the following env vars to be set (from Secret Manager or Cloud Run env):
# - SUPABASE_DB_URL (Postgres connection string in libpq format or URI)
# - GCS_BUCKET (gs://... target bucket)
# - BACKUP_PREFIX (optional prefix path inside bucket, default: supabase-backups)
# - GOOGLE_APPLICATION_CREDENTIALS (service account JSON path) - provided by Cloud Run service account or mounted secret

echo "Starting supabase backup job"

if [ -z "${SUPABASE_DB_URL:-}" ]; then
  echo "SUPABASE_DB_URL is not set. Aborting."
  exit 2
fi

if [ -z "${GCS_BUCKET:-}" ]; then
  echo "GCS_BUCKET is not set. Aborting."
  exit 2
fi

BACKUP_PREFIX=${BACKUP_PREFIX:-supabase-backups}
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT_DIR="/work/out"
mkdir -p "$OUT_DIR"

DB_DUMP_FILE="$OUT_DIR/supabase-db-$TS.dump"

echo "Dumping Postgres DB to $DB_DUMP_FILE"
# Use pg_dump in custom (-Fc) format for compactness
PGPASSWORD=${PGPASSWORD:-}
export PGPASSWORD
pg_dump "$SUPABASE_DB_URL" -Fc -f "$DB_DUMP_FILE"

echo "Uploading dump to $GCS_BUCKET/$BACKUP_PREFIX/"
gsutil cp "$DB_DUMP_FILE" "$GCS_BUCKET/$BACKUP_PREFIX/"

echo "Cleaning up local dump"
rm -f "$DB_DUMP_FILE"

echo "Backup completed: $TS"
