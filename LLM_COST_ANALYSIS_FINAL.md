# LLM Cost Analysis (300-Prompt Benchmark)
**Date**: March 30, 2026  
**Provider Chain**: DeepSeek → OpenAI → Claude  
**Sample Size**: 300 prompts × 4 providers = 1,200 calls

## Benchmark Results
| Provider | Avg Quality | Avg Latency | Cost/Post | Error Rate |
|----------|-------------|------------|-----------|-----------|
| DeepSeek | 76.79/100 | 11.5s | $0.000192 | 2.0% |
| OpenAI | 69.98/100 | 3.9s | $0.000385 | 2.33% |
| Claude | 79.69/100 | 7.7s | $0.003439 | 2.33% |
| xAI | 69.65/100 | 14.8s | $0.001513 | 1.67% |

**Selected Production Chain**: DeepSeek (cost optimized with acceptable quality) → OpenAI (fast fallback) → Claude (quality backstop)

---

## Monthly LLM Cost Per User

### $19 Plan (60 posts/month)
- Base generation: $0.0139
- Regenerate (30% of users): $0.0042
- Repurpose (5% of users): $0.0028
- Style clone setup: $0.0002
- **Total LLM cost: $0.0211**
- **Price: $19.00**
- **Margin: 99.89%**

### $29.90 Plan (120 posts/month)
- Base generation: $0.0278
- Regenerate (30% of users): $0.0083
- Repurpose (10% of users): $0.0056
- Style clone setup: $0.0002
- **Total LLM cost: $0.0419**
- **Price: $29.90**
- **Margin: 99.86%**

### $49.90 Plan (250 posts/month)
- Base generation: $0.058
- Regenerate (40% of users): $0.0186
- Repurpose (15% of users): $0.0139
- Style clone setup: $0.0002
- **Total LLM cost: $0.0907**
- **Price: $49.90**
- **Margin: 99.82%**

---

## Extreme Usage Scenario (Stress Test)

**User**: $19 plan tier, trains KB daily × 5/month, regenerates 20 drafts, repurposes 10 sessions/month

| Activity | Count | Cost |
|----------|-------|------|
| Post generation | 60 | $0.0139 |
| KB training (local, no LLM cost) | 5 | $0.0000 |
| Regenerate | 20 | $0.0047 |
| Repurpose (4 calls × 10) | 40 | $0.0093 |
| Style clone | 1 | $0.0002 |
| **Total** | — | **$0.0281** |

Even extreme power users cost under $0.03/month in LLM fees.

---

## Infrastructure (Excluded from this analysis)

- KB storage: ~$0.10/user/month (Supabase)
- Embeddings compute: Local (SentenceTransformer) = ~$0 
- App hosting: ~$0.05/user/month (GCP/Cloud Run)
- Database: ~$0.05/user/month (Supabase)
- **Total infrastructure: ~$0.20/user/month**

---

## Profitability Summary

| Tier | LLM Cost | Infra Cost | Total Cost | Price | Net Margin |
|------|---------|-----------|-----------|-------|-----------|
| $19 | $0.021 | $0.20 | $0.221 | $19.00 | **98.84%** |
| $29.90 | $0.042 | $0.20 | $0.242 | $29.90 | **99.19%** |
| $49.90 | $0.091 | $0.20 | $0.291 | $49.90 | **99.42%** |

**Conclusion**: Pricing is highly defensible. Even at $19/month, you're capturing 98%+ gross margin.

---

## Confidence Level

- ✅ **High**: 300-prompt sample across 4 providers validated routing strategy
- ✅ **High**: Fallback chain error rate only 2%, keeps quality stable
- ✅ **High**: Local KB embedding removes major cost variable
- ⚠️ **Medium**: Assumes 30-40% feature adoption for regen/repurpose (may be higher)
- ⚠️ **Medium**: Batch requests (future optimization) could cut costs 20-30%

---

## Recommendations for Production

1. **Lock provider chain** in `.env`: deepseek → openai → claude
2. **Monitor actual token usage** for first 100 users to validate estimates
3. **Set cost ceiling alerts** at $0.10/user/month to catch runaway usage
4. **Implement usage quota** enforcement per plan tier to protect margins
5. **Plan token-batching optimization** in 6 months (could reduce LLM cost 20-30%)
