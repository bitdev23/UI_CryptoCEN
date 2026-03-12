# LinkedIn Automation — ValtriLabs / Arab Global Crypto

This repository generates RAG-backed LinkedIn posts using multiple AI providers and can post automatically to your personal LinkedIn profile.

Quick start

1. Copy `.env.example` to `.env` and fill secrets.

2. Install dependencies (locally):
```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

3. Start Redis + KB worker (required for KB training):
```bash
# macOS (Homebrew)
brew services start redis

# OR via Docker (ensure Docker Desktop is running)
docker run -d --name cryptocen-redis -p 6379:6379 redis:7-alpine

# in terminal 1
python app.py

# in terminal 2
python worker.py
```

4. Build knowledge base (optional):
```bash
python main.py
# choose option 1 to build from PDFs in data/pdfs
```

5. Run a preview post locally:
```bash
# ensure TEST_MODE=true in .env
python main.py
# choose option 2 (Run now - preview)
```

Switch content profile to crypto

- Set `CONTENT_PROFILE=arab_global_crypto` in `.env` or in GitHub Secrets to switch to crypto/Exchange-related content.
- Ensure `LINKEDIN_PERSON_ID` is your personal URN (e.g. `urn:li:person:vvQE2g2rkz`) if you want posts on your personal account.

Deploying on Render (recommended)

1. Push this repo to GitHub.
2. Go to [Render.com](https://render.com) and create a new Web Service.
3. Connect your GitHub repo and select this repository.
4. Configure the service:
   - **Runtime**: Docker
   - **Build Command**: (leave default)
   - **Start Command**: (leave default)
5. Add environment variables in Render dashboard:
   - `AI_PROVIDER`: `google`
   - `GOOGLE_API_KEY`: Your Google AI API key
   - `LINKEDIN_ACCESS_TOKEN`: Your LinkedIn access token
   - `LINKEDIN_PERSON_ID`: Your LinkedIn person URN
   - `LINKEDIN_CLIENT_ID`: Your LinkedIn app client ID
   - `LINKEDIN_CLIENT_SECRET`: Your LinkedIn app client secret
   - `TEST_MODE`: `false` (for live posting)
   - `CONTENT_PROFILE`: `arab_global_crypto`
   - `POST_TIME_HOUR`: `11`
   - `POST_TIME_MINUTE`: `0`
   - `TIMEZONE`: `Asia/Kolkata`
   - `MIN_POST_LENGTH`: `150`
   - `MAX_POST_LENGTH`: `1000`
   - `ENABLE_MARKET_GROUNDING`: `true`
   - `AUTH_PREFER_HTTP`: `true`
   - `AUTH_SDK_TIMEOUT`: `30`
   - `AUTH_HTTP_TIMEOUT`: `45`
   - `AUTH_HTTP_CONNECT_TIMEOUT`: `10`
   - `AUTH_HTTP_READ_TIMEOUT`: `45`
   - `AUTH_HTTP_RETRIES`: `4`
   - `AUTH_HTTP_RETRY_DELAY_SEC`: `1.0`
   - `RAZORPAY_KEY_ID`: Your Razorpay key ID
   - `RAZORPAY_KEY_SECRET`: Your Razorpay key secret
   - `RAZORPAY_WEBHOOK_SECRET`: Your Razorpay webhook signing secret
   - `PLAN_PRICE_1_MONTH_INR`: `999`
   - `PLAN_PRICE_3_MONTH_INR`: `2499`
   - `PLAN_PRICE_12_MONTH_INR`: `8999`
6. Deploy and access your dashboard at the provided URL.

The `render.yaml` file is configured for automatic deployment with these settings.

Notes & limitations

- LinkedIn UGC API only supports posting to personal profiles via this endpoint. Company page posting via API is restricted.
- LinkedIn access tokens may expire; you'll need to re-run the OAuth flow periodically to refresh the token.
- To post on the company page, either reshare the personal post manually or use LinkedIn's native page scheduler.

Adding domain-specific PDFs

- To improve factual grounding, add your crypto/Exchange PDFs to `data/pdfs/` and choose option 1 in the CLI to rebuild the knowledge base.

If you want, I can:
- Add an automated token refresh flow (requires refresh token)
- Configure deployment on Render or Railway (both have free tiers)

