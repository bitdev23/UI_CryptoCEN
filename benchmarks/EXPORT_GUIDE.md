# How to Export Real Posts for Benchmarking

## Quick Start

### Option 1: Automatic Script (Recommended)

```bash
# Export from local posts.json
python benchmarks/export_real_generations.py --limit 31

# Or from Supabase
python benchmarks/export_real_generations.py --from-supabase --limit 31
```

The script will:
- Read recent posts from your data
- Automatically map them to benchmark cases
- Save to `benchmarks/results/latest_generation_outputs.json`

### Option 2: Manual Export (Simple)

If you only have a few posts to test:

```bash
# In Python REPL or script:
python3 << 'EOF'
import json

# Add posts you want to test
outputs = {
    "real_estate_roi_intro": "First-time buyers should evaluate neighborhoods by...",
    "crypto_types_strict": "Crypto assets fall into 6 categories...",
    "saas_pricing_balanced": "Product-led growth pricing requires...",
}

# Save the file
with open("benchmarks/results/latest_generation_outputs.json", "w") as f:
    json.dump(outputs, f, indent=2)

print("✅ Saved to benchmarks/results/latest_generation_outputs.json")
EOF
```

### Option 3: From Browser Dashboard

1. Go to your app: `http://localhost:5000`
2. Generate 5-10 posts for different industries
3. Copy the generated text
4. Paste into a JSON file manually

```json
{
  "real_estate_roi_intro": "[paste your real estate post here]",
  "crypto_types_strict": "[paste your crypto post here]",
  "saas_pricing_balanced": "[paste your saas post here]"
}
```

Save as: `benchmarks/results/latest_generation_outputs.json`

---

## Where Is Your Data?

### Local Posts File
```
data/posts.json  ← Your saved posts live here
```

### Supabase Database
```
If configured, posts table stores:
├─ id
├─ user_id
├─ content
├─ topic
├─ industry
├─ created_at
└─ metadata
```

### GCP Production
Your live app stores posts in:
- Local file: `data/posts.json`
- Database: Supabase (if configured)
- Session memory: Recent drafts

---

## Step-by-Step Guide

### Step 1: Generate Some Posts (5-10 is enough)

```bash
# Start app
python app.py

# Go to http://localhost:5000
# Generate posts for different industries:
# - Real Estate: "First-time buyer tips"
# - Crypto: "Types of tokens"
# - SaaS: "Pricing strategy"
# etc.
```

### Step 2: Export the Posts

**Choice A: Automatic**
```bash
python benchmarks/export_real_generations.py --limit 31
```

**Choice B: Manual**
```python
# Copy/paste generated posts into this:
{
  "real_estate_roi_intro": "Your generated post here",
  "crypto_types_strict": "Your generated post here",
  ...
}
```

### Step 3: Push to GitHub

```bash
git add benchmarks/results/latest_generation_outputs.json
git commit -m "Add real generation outputs for CI benchmark validation"
git push origin main
```

### Step 4: Check Results

Go to GitHub Actions:
```
https://github.com/YOUR_ORG/UI_CryptoCEN/actions
```

Click the workflow run → see report:
```
✅ Generation Quality Suite passed (92% pass rate)
OR
❌ Generation Quality Suite failed (75% pass rate)
```

---

## Example: Running Export Script

### Before
```
data/posts.json          ← Your recent posts (100 posts)
benchmarks/results/      ← Empty
```

### Run Export
```bash
$ python benchmarks/export_real_generations.py --limit 31
════════════════════════════════════════════════════════════
EXPORTING REAL GENERATION OUTPUTS FOR BENCHMARK
════════════════════════════════════════════════════════════

✅ Loaded 31 posts from data/posts.json
✅ Mapped 28 posts to benchmark cases

✅ Exported 28 posts to benchmarks/results/latest_generation_outputs.json

════════════════════════════════════════════════════════════
Next steps:
  git add benchmarks/results/latest_generation_outputs.json
  git commit -m 'Add real generation outputs for CI validation'
  git push origin main

GitHub CI will automatically validate these outputs against
the benchmark suite and show the quality report.
════════════════════════════════════════════════════════════
```

### After
```
data/posts.json          ← Still there (100 posts)
benchmarks/results/
  ├─ latest_generation_outputs.json  ← NEW (28 posts for testing)
  ├─ generation_quality_report.all_industries.json
  └─ sample_outputs.json
```

---

## What Gets Created

File: `benchmarks/results/latest_generation_outputs.json`

```json
{
  "real_estate_roi_intro": "First-time home buyers often struggle with neighborhood evaluation. Start by analyzing comparable sales in the last 6 months, understanding rental demand patterns, and evaluating long-term appreciation potential.",
  "real_estate_investment": "Multi-family properties in rising markets require careful evaluation of supply constraints and rent trends. Look for markets where new construction is limited but demand continues growing.",
  "crypto_types_strict": "Crypto assets fall into 6 major categories: utility tokens that power platforms, security tokens that represent ownership, stablecoins tied to fiat currencies, governance tokens for DAOs, wrapped assets for cross-chain use, and Layer 2 tokens for scaling solutions.",
  "saas_pricing_balanced": "Product-led growth (PLG) pricing tests require establishing baseline metrics. Start with activation and retention, run one experiment at a time, measure conversion impact, and maintain cohort quality throughout.",
  "healthcare_ops_creative": "Reducing patient no-shows starts with better scheduling practices. Implement SMS reminders 24 hours before, send follow-up confirmations 1 hour prior, offer flexible rescheduling, and track patterns to identify high-risk appointments early.",
  ...more...
}
```

---

## Common Questions

**Q: How many posts do I need?**  
A: At least 5-10. Ideally 31 (one per benchmark case) for complete coverage.

**Q: Do I need to match case IDs exactly?**  
A: The script does auto-matching. If you manually create the file, yes use the exact case IDs from the suite.

**Q: What if a post doesn't match any case?**  
A: The script skips it. Only mapped posts are included in the benchmark.

**Q: Can I use sample posts?**  
A: Yes, but the benchmark is more useful with real generated posts from your app.

**Q: Do I need to do this before pushing to main?**  
A: No. Push the code first. Do this later when you have real posts to test.

---

## Timeline

```
TODAY:
  ✅ You: push code to main
  ✅ CI: runs with sample outputs (100% pass)
  
DAY 2-3:
  📝 You: generate 5-10 posts in the app
  📋 You: run export script
  ✅ You: push outputs to main
  
DAY 3:
  ✅ CI: validates real outputs
  📊 You: see report (90% pass rate etc.)
  🎯 You: use data to make improvements
```
