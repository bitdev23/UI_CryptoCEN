# 🚀 Quick Reference Card

## Access the Platform
```
URL: http://127.0.0.1:5000
Running: python app.py
```

## Main Tabs

| Tab | Purpose | Key Feature |
|-----|---------|------------|
| **Dashboard** | Overview screen | Post statistics & recent activity |
| **Content Generation** | Create posts | Preview before posting |
| **Automation** | Schedule & post | "Post Now" button here |
| **Knowledge Base** | Upload PDFs | Train AI on your company docs |
| **Personas & Style** | Customize voice | Choose how AI writes |
| **Analytics** | View metrics | Post performance data |
| **Settings** | Configuration | API keys, LinkedIn creds |

---

## Common Tasks

### Task: Fix Post Now Button - Done! ✅
```
Status: FIXED - Button now works without JSON errors
```

### Task: Upload Knowledge Base
```
1. Knowledge Base tab
2. Click "Select PDF Files"
3. Choose PDFs (company docs)
4. Click "Upload PDFs"
5. Click "Train RAG Model"
6. See status turn green
```

### Task: Choose AI Persona
```
1. Personas & Style tab
2. Drop down "Active Persona"
3. Pick one:
   - Professional Advisor (B2B)
   - Friendly Innovator (Startup)
   - Thought Leader (Vision-focused)
   - Storyteller (Personal brand)
4. See details update
```

### Task: Generate & Post
```
1. Automation tab
2. Check Test Mode toggle
3. Click "Post Now"
4. Wait 5-15 seconds
5. See success message
6. Check Dashboard for post
```

### Task: Schedule Automatic Posts
```
1. Automation tab
2. Set Post Time (Hour/Minute)
3. Set Timezone
4. Disable Test Mode
5. Posts publish automatically!
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F12` | Open browser developer console |
| `Ctrl+Shift+I` | DevTools on Windows |
| `Cmd+Option+I` | DevTools on Mac |
| `Ctrl+R` | Refresh page |
| `Ctrl+Shift+Delete` | Clear cache (hard refresh) |

---

## API Endpoints

```
POST   /api/config                    - Get/set configuration
POST   /api/post-now                  - Generate & post
POST   /api/upload-knowledge-base     - Upload PDFs
POST   /api/train-model               - Train RAG
GET    /api/knowledge-base-status     - Check KB status
GET    /api/personas                  - Get personas
POST   /api/personas                  - Update personas
GET    /api/posts                     - Get post history
GET    /api/generate-preview          - Preview content
POST   /api/test-api                  - Test AI connection
POST   /api/test-linkedin             - Test LinkedIn connection
```

---

## Configuration

### AI Provider Setup
**Location**: Settings → AI Configuration

```
Provider Options:
- Google Gemini (FREE - good for testing)
- OpenAI GPT-4 (PAID - best quality)
- Anthropic Claude (PAID - most reliable)
```

### LinkedIn Credentials
**Location**: Settings → LinkedIn Integration

```
Required:
1. Access Token (from LinkedIn Developer)
2. Your LinkedIn Person ID (find in URL when viewing your profile)
```

### Content Profile
**Location**: Settings → Content Settings

```
Options:
- Arab Global Crypto
- ValtriLabs
(Customizable in config.py)
```

---

## File Structure

```
/
├── app.py                    ← Main Flask app
├── templates/
│   └── dashboard.html        ← Web UI
├── data/
│   ├── posts.json            ← Your posts history
│   ├── personas.json         ← Persona configs
│   ├── pdfs/                 ← Your knowledge base PDFs
│   └── chroma_db/            ← RAG database
├── config.py                 ← Hardcoded profiles
├── ai_provider.py            ← AI interface
├── linkedin_poster.py        ← LinkedIn posting
├── content_generator.py      ← Post generation
└── rag_system.py             ← Knowledge base system
```

---

## Status Checks

### Is Flask Running?
```bash
curl http://127.0.0.1:5000
# Should return: 200 OK
```

### Is API Responding?
```bash
curl http://127.0.0.1:5000/api/config
# Should return: JSON config object
```

### Check Knowledge Base Status
**Location**: Knowledge Base tab → Knowledge Base Status card

Shows:
- PDFs Uploaded: count
- Model Status: Trained/Not Trained
- Ready to Use: Yes/No

---

## Troubleshooting Quick Fixes

### "Post Now" throws error
```
1. Refresh page (Ctrl+R)
2. Check Test Mode is ON
3. Check API key in Settings
4. Restart Flask app
```

### Knowledge Base upload fails
```
1. Ensure PDF files (not images)
2. Check file size < 50MB total
3. Try uploading 1 file first
4. Check browser console (F12) for details
```

### Persona won't update
```
1. Select persona again
2. Refresh page
3. Check browser console for errors
4. Try different persona
```

### LinkedIn post doesn't appear
```
1. Check Test Mode is OFF
2. Verify LinkedIn token in Settings
3. Check LinkedIn person ID (view your profile)
4. Try Test Mode first to verify content generation
```

### Server not responding
```
1. Check Flask is running: python app.py
2. Verify URL: http://127.0.0.1:5000
3. Check for port conflicts
4. Restart: Kill terminal, run python app.py again
```

---

## Best Settings by Use Case

### 🎩 Enterprise/B2B
```
Persona: Professional Advisor
Tone: Professional
Style: Formal
Emoji Usage: Minimal
Hashtags: 3
Language: English
Topics: Industry, strategy, insights
```

### 🚀 Startup/SaaS
```
Persona: Friendly Innovator
Tone: Casual
Style: Conversational
Emoji Usage: Moderate
Hashtags: 5
Language: English
Topics: Innovation, growth, startup
```

### 👁️ Thought Leader
```
Persona: Thought Leader
Tone: Inspirational
Style: Narrative
Emoji Usage: Strategic
Hashtags: 4
Language: English
Topics: Future, trends, vision
```

### 📖 Personal Brand
```
Persona: Storyteller
Tone: Narrative
Style: Story-based
Emoji Usage: Adaptive
Hashtags: 3
Language: English
Topics: Experience, learning, growth
```

---

## Performance Tips

### Faster Post Generation
1. Don't upload too many PDFs (2-10 optimal)
2. Use Google Gemini (faster than GPT-4)
3. Keep Test Mode ON while testing
4. Restart Flask if it gets slow

### Faster Training
1. Start with smaller PDFs
2. Train one at a time
3. Check status with "Refresh" button
4. Wait 10-30 sec typically

### Better Post Quality
1. Upload high-quality PDFs
2. Use specific audience keywords
3. Clear content topics
4. Choose matching persona

---

## Data Storage

### Posts are saved to:
```
data/posts.json
```

Each post contains:
```json
{
  "content": "Post text",
  "hashtags": ["#tag1", "#tag2"],
  "theme": "Selected theme",
  "created_at": "2026-02-13T10:30:45",
  "posted": true,
  "test_mode": false
}
```

### Delete a post:
```
1. Open data/posts.json
2. Find post by date
3. Remove JSON object
4. Save file
5. Refresh Dashboard
```

---

## Environment Variables

Set in `.env` file:
```
AI_PROVIDER=google
GOOGLE_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
LINKEDIN_ACCESS_TOKEN=your_token_here
LINKEDIN_PERSON_ID=your_id_here
TEST_MODE=true
CONTENT_PROFILE=arab_global_crypto
POST_TIME_HOUR=11
POST_TIME_MINUTE=0
TIMEZONE=Asia/Kolkata
```

---

## Command Reference

```bash
# Start app
python app.py

# Run tests
python test_generate.py

# Check imports
python -c "from app import app; print('OK')"

# View posts
cat data/posts.json

# Clear posts history
rm data/posts.json
echo "[]" > data/posts.json

# Rebuild RAG
python scripts/rebuild_rag.py
```

---

## Contact & Support

**Issue**: Feature request?
→ Check [FEATURES_SUMMARY.md](FEATURES_SUMMARY.md)

**Issue**: How to X?
→ Check [UI_FEATURES_GUIDE.md](UI_FEATURES_GUIDE.md)

**Issue**: Something broken?
→ Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Issue**: Understanding Post Now?
→ Check [POST_NOW_FIX_GUIDE.md](POST_NOW_FIX_GUIDE.md)

---

## Version Info

```
Platform: LinkedIn Content Automation
Version: 2.0
Last Updated: February 13, 2026
Status: Production Ready ✅

New in v2.0:
✅ Post Now button fixed
✅ Knowledge Base upload
✅ Model training from UI
✅ AI persona selection
✅ Writing style customization
✅ Language support (8 languages)
✅ Complete documentation
```

---

## Next Actions

- [ ] Read [FEATURES_SUMMARY.md](FEATURES_SUMMARY.md) (10 min)
- [ ] Upload knowledge base PDFs (5 min)
- [ ] Train the RAG model (3 min)
- [ ] Test each persona (5 min)
- [ ] Generate first post (2 min)
- [ ] Click "Post Now" (1 min)
- [ ] Monitor analytics (ongoing)

---

**Happy posting! 🚀**

Remember: Start with Test Mode ON, then switch to Live when ready!
