# Supabase Setup Guide for ContentAI Pro

Complete guide to setting up Supabase for your multi-tenant SaaS platform.

---

## Step 1: Create Supabase Project

### 1.1 Sign Up for Supabase
1. Go to [https://supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with GitHub, Google, or email
4. Verify your email

### 1.2 Create New Project
1. Click "New Project"
2. Select your organization (or create one)
3. Fill in project details:
   - **Project name**: `contentai-prod` (or whatever you prefer)
   - **Database Password**: Generate a strong password (SAVE THIS!)
   - **Region**: Choose closest to your users (e.g., `us-east-1`, `eu-west-1`)
   - **Pricing Plan**: Start with **Free** tier
4. Click "Create new project"
5. Wait 2-3 minutes for provisioning

### 1.3 Get API Credentials
Once project is ready:

1. Go to **Settings** (gear icon) > **API**
2. Copy and save these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGc...` (for frontend)
   - **service_role key**: `eyJhbGc...` (for backend - KEEP SECRET!)
3. Add to your `.env` file:
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...service_role_key_here...
```

**⚠️ IMPORTANT**: Use `service_role` key for backend (bypasses RLS), use `anon` key for frontend.

---

## Step 2: Enable pgvector Extension

### 2.1 Enable Extension
1. Go to **Database** > **Extensions** in Supabase dashboard
2. Search for "vector"
3. Enable **pgvector** extension
4. Wait for activation (30 seconds)

### 2.2 Verify Installation
1. Go to **SQL Editor**
2. Run this query:
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```
3. Should return 1 row

---

## Step 3: Run Database Schema

### 3.1 Create Schema
1. Go to **SQL Editor** in Supabase dashboard
2. Click **New Query**
3. Copy entire contents of `database/supabase_schema.sql`
4. Paste into SQL Editor
5. Click **Run** (bottom right)
6. Wait for execution (30-60 seconds)
7. Verify: Should see "Success. No rows returned"

### 3.2 Verify Tables Created
1. Go to **Table Editor**
2. You should see these tables:
   - `user_profiles`
   - `user_api_keys`
   - `linkedin_connections`
   - `kb_files`
   - `kb_embeddings` ← **Most important**
   - `posts`
   - `scheduled_posts`
   - `subscriptions`
   - `usage_monthly`
   - `background_jobs`
   - `system_logs`
   - `plan_limits`

3. Verify `kb_embeddings` table:
   - Click on `kb_embeddings`
   - Check columns include `embedding` with type `vector(384)`

### 3.3 Run Functions
1. Go to **SQL Editor** > **New Query**
2. Copy entire contents of `database/supabase_functions.sql`
3. Paste and **Run**
4. Verify: Should see "Success"

### 3.4 Verify Functions Created
1. Go to **Database** > **Functions**
2. You should see:
   - `match_kb_chunks`
   - `match_kb_chunks_by_files`
   - `can_generate_post`
   - `can_upload_kb_file`
   - `get_dashboard_stats`
   - And others...

---

## Step 4: Set Up Storage for KB Files

### 4.1 Create Storage Bucket
1. Go to **Storage** in Supabase dashboard
2. Click **New bucket**
3. Name: `kb-files`
4. **Public bucket**: ❌ UNCHECKED (files should be private)
5. Click **Create bucket**

### 4.2 Set Up Storage Policies
1. Click on `kb-files` bucket
2. Go to **Policies** tab
3. Click **New policy**

**Policy 1: Allow users to upload their own files**
```sql
CREATE POLICY "Users can upload own KB files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'kb-files' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

**Policy 2: Allow users to view their own files**
```sql
CREATE POLICY "Users can view own KB files"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'kb-files' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

**Policy 3: Allow users to delete their own files**
```sql
CREATE POLICY "Users can delete own KB files"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'kb-files' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

4. Click **Review** > **Save policy** for each

### 4.3 Test Storage
Run this in SQL Editor to verify:
```sql
SELECT * FROM storage.buckets WHERE name = 'kb-files';
```
Should return 1 row.

---

## Step 5: Configure Authentication

### 5.1 Enable Email Auth
1. Go to **Authentication** > **Providers**
2. **Email** should be enabled by default
3. Verify settings:
   - ✅ Enable email provider
   - ✅ Confirm email
   - ✅ Secure email change
   - ✅ Secure password change

### 5.2 Configure Email Templates
1. Go to **Authentication** > **Email Templates**
2. Customize these templates:
   - **Confirm signup**: Email verification
   - **Magic Link**: Passwordless login (optional)
   - **Change Email Address**: Email change confirmation
   - **Reset Password**: Password reset

**Example customize "Confirm signup"**:
```html
<h2>Welcome to ContentAI Pro!</h2>
<p>Click the link below to confirm your email:</p>
<p><a href="{{ .ConfirmationURL }}">Confirm Email</a></p>
```

### 5.3 Set Redirect URLs
1. Go to **Authentication** > **URL Configuration**
2. **Site URL**: `http://localhost:5050` (for dev) or `https://yourdomain.com` (for prod)
3. **Redirect URLs**: Add these:
   - `http://localhost:5050/auth/callback`
   - `https://yourdomain.com/auth/callback`
4. Click **Save**

### 5.4 Configure Session Settings
1. Go to **Authentication** > **Settings**
2. Set these values:
   - **JWT expiry**: `3600` (1 hour)
   - **Refresh token expiry**: `604800` (7 days)
   - **Max password length**: `72`
   - **Min password length**: `8`

---

## Step 6: Test Database Connection

### 6.1 Test from Python
Create `test_supabase.py`:
```python
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

supabase = create_client(url, key)

# Test query
result = supabase.table('plan_limits').select('*').execute()
print(f"Found {len(result.data)} plans")
for plan in result.data:
    print(f"  - {plan['plan']}: {plan['posts_per_month']} posts/month")
```

Run:
```bash
python test_supabase.py
```

Should output:
```
Found 3 plans
  - free: 10 posts/month
  - pro: 100 posts/month
  - agency: -1 posts/month
```

### 6.2 Test pgvector Function
Run in SQL Editor:
```sql
-- Create test embedding (random 384-dim vector)
SELECT match_kb_chunks(
  ('random', 384)::vector,  -- Random query vector
  0.5,  -- threshold
  5,    -- limit
  NULL  -- user_id (will use auth.uid())
);
```

Should return empty result (no embeddings yet) without errors.

---

## Step 7: Set Up Row Level Security (RLS)

RLS is automatically enabled by the schema, but verify:

### 7.1 Check RLS is Enabled
1. Go to **Authentication** > **Policies**
2. Select table: `posts`
3. Should see: "Row Level Security enabled"
4. Should see policy: "Users can manage own posts"

### 7.2 Test RLS
Run in SQL Editor:
```sql
-- This should fail (no auth)
SELECT * FROM posts;

-- This should work (uses service_role key which bypasses RLS)
-- But in production, only authenticated requests should work
```

---

## Step 8: Configure Realtime (Optional)

If you want live updates for scheduled posts:

1. Go to **Database** > **Replication**
2. Enable replication for:
   - `scheduled_posts`
   - `posts`
3. Now you can use Supabase Realtime in frontend:
```javascript
const subscription = supabase
  .channel('scheduled_posts_changes')
  .on('postgres_changes', { 
    event: '*', 
    schema: 'public', 
    table: 'scheduled_posts' 
  }, payload => {
    console.log('Change received!', payload)
  })
  .subscribe()
```

---

## Step 9: Monitoring & Limits

### 9.1 Check Free Tier Limits
1. Go to **Settings** > **Usage**
2. Free tier includes:
   - **Database**: 500 MB
   - **Storage**: 1 GB
   - **Bandwidth**: 2 GB/month
   - **Monthly Active Users**: 50,000

### 9.2 Set Up Alerts
1. Go to **Settings** > **Billing**
2. Add payment method (optional, but prevents service interruption)
3. Set budget alerts:
   - Database size: 400 MB (80%)
   - Storage: 800 MB (80%)

### 9.3 Monitor Performance
1. Go to **Reports** > **API**
2. Check:
   - Response times
   - Error rates
   - Most called routes

---

## Step 10: Production Checklist

Before going live:

### Database
- ✅ All tables created
- ✅ All functions created
- ✅ pgvector extension enabled
- ✅ HNSW index on `kb_embeddings.embedding`
- ✅ RLS enabled on all user tables
- ✅ Storage bucket created with policies

### Authentication
- ✅ Email provider enabled
- ✅ Email templates customized
- ✅ Redirect URLs configured
- ✅ Session timeouts configured

### Security
- ✅ `service_role` key is SECRET (not in frontend)
- ✅ RLS policies tested
- ✅ Storage policies tested
- ✅ Rate limiting enabled (done in Flask app)

### Monitoring
- ✅ Usage alerts configured
- ✅ Backup payment method added
- ✅ Connection pooling configured (see below)

---

## Connection Pooling (for Production)

When you have >10 concurrent users:

1. Go to **Settings** > **Database**
2. Copy **Connection Pooling** URL (port 6543)
3. Update `.env`:
```env
SUPABASE_DB_URL=postgresql://postgres.xxxxx:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
DATABASE_POOL_SIZE=10
```

4. Use this for backend connections (higher concurrency)

---

## Cost Estimates

### Free Tier (Your Starting Point)
- **Cost**: $0/month
- **Limits**: 500 MB DB, 1 GB storage, 50k MAU
- **Good for**: 20-50 pilot users

### Pro Tier ($25/month)
- **Database**: 8 GB
- **Storage**: 100 GB
- **Bandwidth**: 50 GB
- **MAU**: Unlimited
- **Good for**: 100-1,000 users

### Pay-as-you-go (after Pro)
- **Database**: $0.125/GB/month
- **Storage**: $0.021/GB/month
- **Bandwidth**: $0.09/GB

**Example (1,000 users)**:
- 2 GB database = $25 (Pro included)
- 10 GB storage = $25 (Pro included)
- 100 KB per file × 10 files × 1000 users = 1 GB = included
- **Total**: ~$25-30/month

---

## Troubleshooting

### Issue: "Extension vector does not exist"
**Solution**: Go to Database > Extensions, enable pgvector

### Issue: "Permission denied for schema public"
**Solution**: Check RLS policies, ensure authenticated users have access

### Issue: "Function match_kb_chunks does not exist"
**Solution**: Run `database/supabase_functions.sql` again

### Issue: "Storage bucket kb-files not found"
**Solution**: Create bucket in Storage section

### Issue: Slow vector search (>1 second)
**Solution**: Verify HNSW index exists:
```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'kb_embeddings';
```
Should return `idx_kb_embeddings_vector`

---

## Next Steps

After Supabase is set up:

1. ✅ Update `.env` with Supabase credentials
2. ✅ Install new dependencies: `pip install -r requirements.txt`
3. ✅ Test connection: `python test_supabase.py`
4. ✅ Run app: `python app.py`
5. ✅ Deploy to AWS (see `AWS_DEPLOYMENT_GUIDE.md`)

---

## Support & Resources

- **Supabase Docs**: https://supabase.com/docs
- **pgvector Docs**: https://github.com/pgvector/pgvector
- **Supabase Discord**: https://discord.supabase.com
- **GitHub Issues**: Report bugs at your repo

---

**🎉 Congratulations! Your Supabase backend is ready. Time to deploy to AWS!**
