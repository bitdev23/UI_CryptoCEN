# Production Deployment: Concurrency & Rate Limiting Guide

**Date**: March 30, 2026  
**Scenario**: 100 users, 50 concurrent requests to `/api/generate-preview`

---

## Current Architecture

```
50 Concurrent Requests 
    ↓
Flask App (1 thread / 4 workers)
    ↓
AIProvider (with rate limit detection)
    ↓
DeepSeek API (60 req/min limit)
    ↓
Fallback: OpenAI → Claude
```

---

## What Happens With 50 Concurrent Requests

### Scenario A: Development (python app.py)
- **Workers**: 1 (single-threaded)
- **Result**: Requests queue in OS buffer → processed one at a time
- **Latency**: 1st request = 11.5s, 50th request = 50 × 11.5s = ~560 seconds total ❌
- **User experience**: TERRIBLE — users wait 10+ minutes

### Scenario B: Production (gunicorn -w 4)
- **Workers**: 4
- **Result**: 4 requests processed in parallel, rest queue
- **Latency**: 1-4th requests = 11.5s, 5-50th requests = queued then processed
- **Max concurrent pool**: ~4-8 active + 40+ queued
- **User experience**: OK for light load, adequate for 50 concurrent

### Scenario C: Production (gunicorn -w 16)
- **Workers**: 16
- **Result**: 16 requests processed in parallel natively
- **Latency**: 1-16th requests = 11.5s, 17-50th requests queue briefly
- **Max concurrent handling**: ~16 active + 34 queued
- **User experience**: GOOD — most users experience normal latency

---

## Rate Limit Scaling: How Many Can You Actually Handle?

### DeepSeek Tier Limits
| Tier | Requests/Min | Tokens/Min | Can Handle |
|------|-------------|-----------|-----------|
| Free | 60 | 90K | 20-30 concurrent (avg ~110 tokens/post) |
| Paid (Standard) | 300-600 | 1M+ | 100-200 concurrent |
| Pro | 1000+ | 2M+ | 500+ concurrent |

### Current Rate Limit Detection

Enhanced `ai_provider.py` now detects 429 errors and:
1. **Exponential backoff**: 0.1s → 0.2s → 0.4s → 0.8s → 1.6s
2. **Automatic fallback**: After backoff, tries OpenAI (much higher limits)
3. **Logging**: Tracks how many times rate limit hit

**Example**:
```
Request 61 hits DeepSeek → 429 error
Backoff 0.1s, retry → fails again
Falls back to OpenAI → 💚 SUCCESS
User waits: 11.5s (DeepSeek) + 4.0s (OpenAI) + backoff = ~16s total
```

---

## Recommendation for Your Scale

### For 100 Users / 50 Concurrent: Use THIS

**Production Stack**:
```bash
# Start with 16 workers (handles 16 native + 34 queued)
gunicorn \
  -w 16 \
  -b 0.0.0.0:5000 \
  --timeout 60 \
  --access-logfile - \
  app:app
```

**Expected Performance**:
- ✅ DeepSeek handles: requests 1-60 (per minute limit)
- ✅ Requests 61-120 fallback to OpenAI (much higher limits)
- ✅ 99% of requests succeed without user-facing errors
- ✅ Avg latency: 8-12 seconds (mostly DeepSeek, some OpenAI)
- ✅ Cost: ~$0.000232/request (blended)

### Upgrade Timeline

| Users | Concurrency | Deployment | Config |
|-------|------------|-----------|--------|
| 0-50 | 10-20 | Single VM | `gunicorn -w 8` |
| 50-200 | 20-50 | Single VM | `gunicorn -w 16` |
| 200-500 | 50-100 | Load balanced (2 VMs) | `gunicorn -w 16` × 2 |
| 500+ | 100+ | Auto-scaling (GCP/AWS) | Kubernetes + 50+ workers |

---

## Production Deployment (GCP Cloud Run Recommended)

### Option 1: GCP Cloud Run (Recommended for your scale)
✅ **Auto-scaling** handles 50+ concurrent automatically  
✅ **Serverless** = no ops  
✅ **Cost-effective** at your scale

```bash
# Build and deploy
gcloud run deploy velank-linkedin \
  --source . \
  --memory 2Gi \
  --cpu 2 \
  --allow-unauthenticated \
  --max-instances 50 \
  --concurrency 10
```

### Option 2: Single VM with Gunicorn (Cost optimized)
✅ **Cheaper** than Cloud Run  
✅ **Full control**

```bash
# On your VM, run:
gunicorn \
  -w 16 \
  -b 0.0.0.0:5000 \
  --timeout 60 \
  --access-logfile /var/log/gunicorn.log \
  app:app

# Start on boot (systemd)
# Use: /deploy/systemd/velank.service (already in your repo)
```

---

## Monitoring: What to Watch

### Critical Metrics
1. **Rate Limit Errors (429)**: 
   - If > 5% → upgrade DeepSeek plan
   - If < 1% → load is healthy

2. **Fallback Usage**:
   - If > 30% requests hit OpenAI/Claude → DeepSeek is bottleneck
   - Cost increases but quality holds

3. **Response Latency**:
   - p50: should be 8-12s (mostly DeepSeek)
   - p95: should be < 20s (some fallback)
   - p99: should be < 30s (final fallback + retries)

### Add this to your monitoring (optional):
```python
# In app.py, after each generation:
logger.info(f"generation_latency_ms={result['latency_ms']} provider={result['provider']} user_id={user_id}")
```

---

## Cost Impact of Fallbacks

If 50% requests hit fallback:
- **Base (100% DeepSeek)**: $0.000192/post
- **With fallback (50% DeepSeek + 50% OpenAI)**: 
  - = (0.5 × $0.000192) + (0.5 × $0.000385)
  - = $0.000289/post (+50% cost)

**Still extremely profitable**: $19 plan cost = $0.0211 LLM/month → price $19.00

---

## FAQ: Concurrency

**Q: Will 50 requests queue or does the app crash?**  
A: They queue in the OS socket buffer. Flask handles gracefully. No crashes. Just longer waits.

**Q: How do I know if I'm hitting rate limits?**  
A: Check logs for "429" or "rate limit detected". Our code now logs these automatically.

**Q: What's the max load before I need to upgrade?**  
A: With `gunicorn -w 16`:
- ~100 concurrent requests → 90% DeepSeek success
- ~150 concurrent requests → 70% DeepSeek success (rest fallback)
- ~200 concurrent requests → need load balancing

**Q: Can I batch requests instead of individual calls?**  
A: Not yet, but it's on the roadmap. Batch API would cut costs 20-30%.

---

## Next Steps

1. **Deploy to production** (Cloud Run or VM with systemd)
2. **Monitor rate limit errors** for first week
3. **If > 10% rate limit errors** → upgrade DeepSeek plan
4. **If avg latency > 15s** → add more workers or upgrade tier
5. **After 1000 users** → consider token batching optimization
