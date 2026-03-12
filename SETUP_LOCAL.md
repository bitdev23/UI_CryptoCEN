# Local Setup & Testing Guide

This guide walks you through testing the LinkedIn automation locally before deploying to GitHub.

## Prerequisites

- Python 3.10+ (ideally 3.11+)
- Google API key with Gemini access
- LinkedIn access token & person ID
- Your knowledge base (PDF or DOCX) in `data/pdfs/`

## Step 1: Install Dependencies

```bash
pip install --upgrade -r requirements.txt
```

This installs:
- `google-generativeai` (Gemini Flash)
- `supabase` & `sentence-transformers` (RAG/embeddings)
- `python-docx` (DOCX support)
- Other essentials

## Step 2: Configure `.env`

Edit `.env` locally with these required keys:

```dotenv
AI_PROVIDER=google
GOOGLE_API_KEY=your-api-key-here
TEST_MODE=true
ENABLE_MARKET_GROUNDING=true
GROUND_TOKENS=bitcoin,ethereum
CONTENT_PROFILE=arab_global_crypto

# LinkedIn credentials (keep secret!)
LINKEDIN_ACCESS_TOKEN=your-token
LINKEDIN_PERSON_ID=your-person-id
```

⚠️ **Never commit `.env` with secrets!**

## Step 3: Check Google API Access

```bash
python scripts/check_models.py
```

Expected output:
```
✓ Google GenAI configured successfully
✓ Available models:
  - models/gemini-2.5-flash
    Methods: ['generateContent', ...]
✓ Testing generation with gemini-2.5-flash...
  Response: Hello
✓ Generation successful!
```

If this fails, check:
- Google API key is valid & has GenAI API enabled
- Key has sufficient quota/permissions
- Internet connection is working

## Step 4: Rebuild RAG Embeddings

This reads your PDFs/DOCX and creates vector embeddings for similar-document retrieval:

```bash
python scripts/rebuild_rag.py
```

Expected output:
```
INFO:__main__:Loading PDFs/DOCX from data/pdfs...
INFO:__main__:Loaded X documents
INFO:__main__:Building RAG embeddings...
INFO:__main__:✓ RAG rebuilt successfully
```

This rebuilds user-scoped embeddings in Supabase pgvector.

## Step 5: Generate & Preview a Post

```bash
python scripts/test_local.py
```

This runs a complete end-to-end test:
1. Loads RAG embeddings
2. Queries Google Gemini (gemini-2.5-flash) with Head-of-Product persona prompt
3. Generates a ~150-word LinkedIn post
4. Validates quality (length, hashtags, no AI-clichés)
5. Saves to `data/posts.json`
6. Shows preview in terminal

Expected output:
```
============================================================
POST PREVIEW
============================================================
Ethereum's Merge in September 2022 dramatically reduced...
[post content here]
#CryptoExchange
#BlockchainTech
...

============================================================
QUALITY CHECKS
============================================================
Content length: 800 chars
✓ No stray formatting
✓ Hashtags present
✓ TEST COMPLETE — Post is ready for LinkedIn
```

### Quality Checks to Look For:
- ✅ No asterisks, markdown, or `**bold**` formatting
- ✅ No AI-clichés (no "delve", "unleash", "landscape")
- ✅ Hooks with concrete data or contrarian points
- ✅ 4-6 hashtags
- ✅ Length 150-1000 chars (LinkedIn sweet spot)
- ✅ References recent data with sources/years

## Step 6: Post Live (Optional Local Test)

Once you're happy with the preview, you can post to LinkedIn locally:

1. Set credentials in `.env`:
   ```dotenv
   TEST_MODE=false
   ```

2. Run interactive mode:
   ```bash
   python main.py
   # Choose option 3: Enable live posting and run now
   ```

Alternatively:
```bash
python post_saved_draft.py
```

This posts the last generated post directly.

## Step 7: Deploy to GitHub

When ready to automate:

1. **Add GitHub Secrets** (https://github.com/bhavik-vala/CryptoCEN/settings/secrets/actions):
   - `GOOGLE_API_KEY` → your API key
   - `LINKEDIN_ACCESS_TOKEN` → your token
   - `LINKEDIN_PERSON_ID` → your ID
   - `CONTENT_PROFILE` → `arab_global_crypto` (or your profile)
   - `AI_PROVIDER` → `google`

2. **Push code to GitHub**:
   ```bash
   git add -A
   git commit -m "Ready for scheduled LinkedIn posting"
   git push origin main
   ```

3. **Test workflow manually** (optional):
   - Go to GitHub Actions tab
   - Click "Scheduled LinkedIn Post"
   - Click "Run workflow" → "Run workflow"
   - Check logs for success

4. **Schedule runs automatically**:
   - Workflow runs daily at **11:00 AM IST** (cron: `55 11 * * *`)
   - Posts are generated and uploaded without your laptop running
   - Set `TEST_MODE=false` in workflow env when confident

## Troubleshooting

### "ModuleNotFoundError: No module named 'pdf_processor'"
- Make sure you're running scripts from project root:
  ```bash
  cd c:\Users\bhavi\Documents\Linkedin Post
  python scripts/test_local.py
  ```

### "GOOGLE_API_KEY not set"
- Ensure `.env` has `GOOGLE_API_KEY=your-key`
- Run: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GOOGLE_API_KEY')[:20])"`

### "models/gemini-2.5-flash is not found"
- Your Google project may not have GenAI API enabled
- Visit: Google Cloud Console → APIs & Services → Enable "Generative Language API"
- Ensure API key has permission to call GenAI

### "No PDFs/DOCX found in data/pdfs"
- Place your knowledge base files in `data/pdfs/` (PDF or DOCX)
- Run `python scripts/rebuild_rag.py` again

### Post quality is poor (old data, AI-clichés, etc.)
- Update your knowledge base PDFs with recent content
- Check prompt in `content_generator.py` — adjust persona/themes as needed
- Lower temperature (currently 0.2) for more deterministic output
- Run `python scripts/test_local.py` again to test

## Next Steps

- ✅ Verify local generation works
- ✅ Review post quality in `data/posts.json`
- ✅ Set up GitHub Secrets
- ✅ Push to GitHub
- ✅ GitHub Actions posts automatically daily at 11 AM IST

Good luck! 🚀
