#!/usr/bin/env bash
# Helper: instructions to back up Supabase project schema + data.
# This script is a template. It requires the Supabase CLI or psql/pg_dump access.
# Usage (recommended): install supabase CLI and run from your machine with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set.

set -euo pipefail

if [ -z "${SUPABASE_URL:-}" ] || [ -z "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  echo "Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your environment before running this script."
  exit 1
fi

TS=$(date +%Y%m%dT%H%M%S)
OUT_DIR="backups/supabase-$TS"
mkdir -p "$OUT_DIR"

echo "Backup directory: $OUT_DIR"

echo "--- Step 1: export SQL schema using Supabase REST/SQL API (service role) ---"
# Note: The supabase CLI provides `supabase db dump` in recent versions.
# If you have the CLI installed you can simply run:
#   supabase db dump --file "$OUT_DIR/schema.sql" --project-ref "$(basename $SUPABASE_URL)"

# Fallback: use SQL export endpoint (requires service role key)
SQL_EXPORT_URL="$SUPABASE_URL/rest/v1/rpc/export_database"

cat > "$OUT_DIR/README.txt" <<EOF
This folder contains a recommended backup process.
Recommended steps:
1) Install supabase CLI: https://supabase.com/docs/guides/cli
2) Run: supabase db dump --file "$OUT_DIR/schema.sql" --project-ref "$(basename $SUPABASE_URL)"
3) Copy storage buckets via the Supabase dashboard or `supabase storage` tools.
4) Do NOT share the service-role key. Store backups securely.
EOF

# We intentionally do not attempt to connect to Postgres from this script because connection details differ per project.
# Use the supabase CLI or the Supabase UI (Project -> Settings -> Database -> Connection info) to run pg_dump/pg_restore.

echo "Created backup helper files in $OUT_DIR. Follow README.txt to create DB dumps and storage copies."

echo "Done."
