# Generation Quality Benchmark Suite

## Overview
This document describes the comprehensive multi-industry benchmark suite for validating post generation quality across all supported verticals.

**Current Coverage**: 31 test cases across 13 industries.

## Benchmark Suite Structure

### File Locations
- **Suite Definition**: `benchmarks/generation_quality_suite.sample.json` - Test cases with expectations
- **Sample Outputs**: `benchmarks/results/all_industries_sample_outputs.json` - Reference generated posts
- **Runner Script**: `benchmarks/run_generation_quality_bench.py` - Evaluation engine
- **CI Workflow**: `.github/workflows/generation_quality_ci.yml` - Automated testing

## Industries Covered

### 1. **Crypto** (3 cases)
- `crypto_types_strict`: Educational post on asset classification (strict grounding)
- `crypto_defi_strategy`: DeFi strategy insights (balanced grounding)
- `crypto_btc_market`: Bitcoin market cycles (strict grounding)

### 2. **SaaS** (3 cases)
- `saas_pricing_balanced`: Product-led growth pricing experiments
- `saas_customer_retention`: Churn reduction through onboarding
- `saas_team_scaling`: Scaling engineering teams without quality loss

### 3. **Healthcare** (3 cases)
- `healthcare_ops_creative`: Reducing patient no-shows (creative grounding)
- `healthcare_staff_retention`: Nurse retention strategies
- `healthcare_patient_experience`: Digital patient experience transformation

### 4. **Real Estate** (3 cases)
- `real_estate_roi_intro`: First-time buyer neighborhood ROI evaluation
- `real_estate_investment`: Multi-family investment in rising markets
- `real_estate_remote_work`: Remote work impact on commercial real estate

### 5. **E-Commerce** (3 cases)
- `ecommerce_conversion`: A/B testing checkout flow optimization
- `ecommerce_personalization`: Personalization engine for AOV lift
- `ecommerce_retention`: Loyalty program design for repeat purchase

### 6. **FinTech** (2 cases)
- `fintech_compliance`: Regulatory compliance in emerging markets (strict grounding)
- `fintech_api_integration`: Seamless payment API integration

### 7. **Manufacturing** (2 cases)
- `mfg_supply_chain`: Real-time supply chain visibility and optimization
- `mfg_lean_ops`: Lean manufacturing waste elimination (creative grounding)

### 8. **Media & Publishing** (2 cases)
- `media_content_strategy`: Content atomization for audience growth
- `media_monetization`: Revenue diversification strategies

### 9. **B2B Sales** (2 cases)
- `b2b_sales_process`: Sales enablement for cycle shortening
- `b2b_account_management`: Strategic account management for enterprise growth

### 10. **Non-Profit** (2 cases)
- `nonprofit_fundraising`: Modern donor engagement for millennials
- `nonprofit_operations`: Scaling impact without scaling overhead

### 11. **EdTech** (2 cases)
- `edtech_engagement`: Student engagement in hybrid learning models
- `edtech_outcomes`: Data-driven learning outcomes measurement

### 12. **Travel & Hospitality** (2 cases)
- `travel_personalization`: Hyper-personalization of guest experience (creative grounding)
- `travel_sustainability`: Sustainable tourism practices

### 13. **Enterprise Tech** (2 cases)
- `enterprise_security_strict`: Zero-Trust security frameworks (strict grounding)
- `enterprise_cloud_migration`: Cloud-first strategy with minimal disruption

## Grounding Mode Distribution
- **Strict**: 4 cases (crypto_types, crypto_btc, fintech_compliance, enterprise_security)
- **Balanced**: 19 cases (majority of business use cases)
- **Creative**: 8 cases (thought leadership, strategic content)

## Quality Expectations Per Case

Each case specifies:
- **must_include**: Required keywords/phrases that generated content must contain
- **must_not_include**: Forbidden keywords from other domains
- **min_word_count**: Minimum output length (18-22 words for realistic first-pass content)
- **expected_numbers**: Optional numeric content that should appear

### Example Case Structure
```json
{
  "id": "real_estate_roi_intro",
  "industry": "Real Estate",
  "topic": "How First-Time Buyers Can Evaluate Neighborhood ROI",
  "template_id": "educational-post",
  "kb_mode": "use_kb",
  "grounding_mode": "balanced",
  "expectations": {
    "must_include": ["cash flow", "roi", "neighborhood"],
    "must_not_include": ["bitcoin", "staking"],
    "min_word_count": 22
  }
}
```

## Running the Benchmark

### Local Testing
```bash
# Run with sample outputs
python benchmarks/run_generation_quality_bench.py \
  --suite benchmarks/generation_quality_suite.sample.json \
  --responses benchmarks/results/all_industries_sample_outputs.json \
  --output benchmarks/results/generation_quality_report.local.json \
  --min-pass-rate 80

# Run with real API outputs
python benchmarks/run_generation_quality_bench.py \
  --suite benchmarks/generation_quality_suite.sample.json \
  --responses benchmarks/results/latest_generation_outputs.json \
  --output benchmarks/results/generation_quality_report.latest.json \
  --min-pass-rate 80
```

### CI/CD Testing
The GitHub Actions workflow runs automatically on:
- Push to `main` (if benchmarks files changed)
- Pull requests to `main` (if benchmarks files changed)
- Manual trigger with optional responses file input

Default CI gate: **80% pass rate**

## Response Input Formats

The benchmark runner accepts multiple response file formats:

### Format 1: Simple Mapping
```json
{
  "case_id_1": "generated post text...",
  "case_id_2": "generated post text..."
}
```

### Format 2: Array of Records
```json
[
  {
    "case_id": "case_1",
    "content": "generated post text..."
  },
  {
    "case_id": "case_2",
    "text": "generated post text..."
  }
]
```

### Format 3: API Response Wrapper
```json
{
  "results": [
    {
      "id": "case_1",
      "response": {
        "content": "generated post text..."
      }
    }
  ]
}
```

## Benchmark Metrics

Each case produces:
- **passed**: Boolean - case met all expectations
- **score**: 0-100 - percentage of checks that passed
- **checks**: Detailed pass/fail for each expectation

### Summary Metrics
- **total_cases**: Number of test cases
- **passed_cases**: Cases that passed all checks
- **pass_rate**: (passed / total) * 100
- **avg_score**: Average score across all cases

## Next Steps

1. **Add Real Generation Logs**
   - Export actual post generation outputs from API calls
   - Format as `benchmarks/results/latest_generation_outputs.json`
   - Run benchmark to validate production quality

2. **Adjust Expectations**
   - Fine-tune must_include/must_not_include based on actual patterns
   - Calibrate min_word_count to your first-pass output reality
   - Add expected_numbers for quantitative content

3. **Monitor Pass Rate**
   - Track pass_rate metric over time
   - Correlate drops with model/prompt changes
   - Use feedback data to improve generation

4. **Expand Coverage**
   - Add new cases for emerging verticals
   - Create industry-specific sub-suites
   - Add customer-provided benchmark cases

## Integration with Generation Feedback

The feedback loop connects real user ratings with benchmark validation:
- Users rate generated posts as "Good" or "Needs Work"
- Optional reason and notes provided
- This feedback informs expectations calibration
- Low-pass cases guide model/prompt tuning

## Current Status

✅ **31 test cases across 13 industries**
✅ **100% pass rate on sample outputs**
✅ **CI workflow configured and working**
✅ **Multiple response format support**
✅ **Grounding mode distribution across all strategy types**
