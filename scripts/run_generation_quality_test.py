import json
import os
import re
import time
from pathlib import Path

import requests

BASE = (os.getenv('GEN_TEST_BASE') or 'http://127.0.0.1:5050').strip()
ENDPOINT = BASE + '/api/generate-preview'
REQUEST_DELAY_SEC = 12
TEST_EMAIL = (os.getenv('GEN_TEST_EMAIL') or '').strip()
TEST_PASSWORD = (os.getenv('GEN_TEST_PASSWORD') or '').strip()
FORCE_PROVIDER = (os.getenv('GEN_FORCE_PROVIDER') or '').strip().lower()

CASES = [
    {
        'name': 'Deep Tech / CTO',
        'industry': 'deep tech',
        'role': 'cto',
        'topic': 'AI agent orchestration patterns for enterprise reliability',
        'target_audience': 'engineering leaders and platform architects',
        'topics': ['AI agents', 'LLM reliability', 'system design'],
        'keywords': ['ai', 'llm', 'agent', 'model', 'architecture', 'reliability', 'inference', 'latency'],
    },
    {
        'name': 'E-Commerce / Marketing',
        'industry': 'ecommerce',
        'role': 'marketing',
        'topic': 'How lifecycle email and onsite personalization improve repeat purchase rate',
        'target_audience': 'ecommerce growth marketers and DTC founders',
        'topics': ['retention', 'conversion optimization', 'customer journey'],
        'keywords': ['conversion', 'retention', 'customer', 'cart', 'purchase', 'personalization', 'funnel', 'aov'],
    },
    {
        'name': 'Real Estate / Sales',
        'industry': 'real estate',
        'role': 'sales',
        'topic': 'How top real estate advisors build trust with local market data storytelling',
        'target_audience': 'real estate agents and brokerage sales leaders',
        'topics': ['lead nurturing', 'local market insights', 'listing strategy'],
        'keywords': ['property', 'listing', 'buyer', 'seller', 'market', 'mortgage', 'brokerage', 'neighborhood'],
    },
    {
        'name': 'Legal / Operations',
        'industry': 'legal',
        'role': 'ops',
        'topic': 'Operational playbook for reducing legal intake turnaround time',
        'target_audience': 'law firm operations managers and partners',
        'topics': ['workflow automation', 'service delivery', 'quality control'],
        'keywords': ['legal', 'contract', 'matter', 'compliance', 'firm', 'intake', 'case', 'counsel'],
    },
    {
        'name': 'Finance / CFO',
        'industry': 'finance',
        'role': 'finance',
        'topic': 'How finance teams can shorten close cycles without sacrificing control',
        'target_audience': 'finance leaders, controllers, and CFOs',
        'topics': ['forecasting', 'controls', 'close process'],
        'keywords': ['finance', 'cash', 'forecast', 'margin', 'close', 'budget', 'control', 'cfo'],
    },
]

FORBIDDEN_NON_CRYPTO = [
    'crypto', 'cryptocurrency', 'web3', 'blockchain', 'defi', 'token', 'tokens', 'nft', 'nfts',
    'bitcoin', 'ethereum', 'solana', 'wallet', 'exchange', 'dex', 'cex'
]
CTA_MARKERS = [
    'what do you think', 'what has worked', 'share your', 'drop a comment', 'comment below',
    'dm me', 'let me know', 'how are you', 'your take', 'agree or disagree'
]


def words_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text or ''))


def split_body_and_tags(content: str):
    lines = [ln.rstrip() for ln in (content or '').splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()

    hashtag_line = ''
    if lines and re.search(r'(?:^|\s)#[A-Za-z][A-Za-z0-9_]{1,49}', lines[-1]):
        hashtag_line = lines[-1].strip()
        body = '\n'.join(lines[:-1]).strip()
    else:
        body = '\n'.join(lines).strip()

    tags = re.findall(r'#[A-Za-z][A-Za-z0-9_]{1,49}', hashtag_line)
    return body, tags, hashtag_line


def score_case(case: dict, content: str) -> dict:
    body, tags, tagline = split_body_and_tags(content)
    lower = (body + ' ' + tagline).lower()
    score = 0
    reasons = []

    hits = sum(1 for kw in case['keywords'] if re.search(rf"\b{re.escape(kw.lower())}\b", lower))
    rel = min(30, hits * 6)
    score += rel
    if rel < 18:
        reasons.append(f'Low domain keyword coverage ({hits} hits)')

    role_hint = case['role'].lower()
    role_ok = role_hint in lower or case['target_audience'].split()[0].lower() in lower
    if role_ok:
        score += 10
    else:
        reasons.append('Role perspective is weak')

    leaks = [t for t in FORBIDDEN_NON_CRYPTO if re.search(rf"\b{re.escape(t)}\b", lower)]
    if case['industry'] != 'crypto' and not leaks:
        score += 20
    elif case['industry'] != 'crypto':
        reasons.append('Cross-domain leakage: ' + ', '.join(sorted(set(leaks))[:5]))

    paragraphs = [p for p in re.split(r'\n\s*\n', body) if p.strip()]
    if len(paragraphs) >= 3:
        score += 10
    else:
        reasons.append(f'Needs clearer paragraphing ({len(paragraphs)} para)')

    words = words_count(body)
    if 110 <= words <= 260:
        score += 7
    else:
        reasons.append(f'Word count out of range ({words})')

    if '**' not in content and not re.search(r'^\s*[-•]', body, flags=re.MULTILINE):
        score += 4
    else:
        reasons.append('Contains markdown/bullets artifacts')

    if 3 <= len(tags) <= 6:
        score += 4
    else:
        reasons.append(f'Hashtag count not ideal ({len(tags)})')

    first_line = body.splitlines()[0].strip() if body.splitlines() else ''
    hook_ok = ('?' in first_line) or bool(re.search(r'\d', first_line)) or len(first_line) <= 90
    if hook_ok:
        score += 5
    else:
        reasons.append('Weak opening hook')

    cta_ok = any(m in lower for m in CTA_MARKERS) or body.strip().endswith('?')
    if cta_ok:
        score += 5
    else:
        reasons.append('No clear engagement CTA')

    readability_ok = all(len(ln) <= 230 for ln in body.splitlines() if ln.strip())
    if readability_ok:
        score += 5
    else:
        reasons.append('Some lines too long for feed readability')

    return {
        'score': score,
        'words': words,
        'paragraphs': len(paragraphs),
        'hashtags': tags,
        'reasons': reasons[:4],
        'body_preview': body[:360].replace('\n', ' / '),
    }


def main():
    rows = []
    auth_headers = {}

    if TEST_EMAIL and TEST_PASSWORD:
        try:
            login_response = requests.post(
                BASE + '/api/auth/login',
                json={'email': TEST_EMAIL, 'password': TEST_PASSWORD},
                timeout=60,
            )
            login_data = login_response.json() if login_response.headers.get('content-type', '').startswith('application/json') else {}
            token = str(login_data.get('access_token') or '').strip()
            if token:
                auth_headers = {'Authorization': f'Bearer {token}'}

                if FORCE_PROVIDER in {'anthropic', 'google', 'openai'}:
                    requests.post(
                        BASE + '/api/config',
                        json={'AI_PROVIDER': FORCE_PROVIDER},
                        headers=auth_headers,
                        timeout=60,
                    )
                    time.sleep(1)
            else:
                print('WARN: Login succeeded without access token; running unauthenticated tests')
        except Exception as exc:
            print(f'WARN: Auth setup failed ({exc}); running unauthenticated tests')

    for idx, case in enumerate(CASES):
        if idx > 0:
            time.sleep(REQUEST_DELAY_SEC)

        payload = {
            'topic': case['topic'],
            'industry': case['industry'],
            'role': case['role'],
            'target_audience': case['target_audience'],
            'post_goal': 'Engagement and qualified inbound conversations',
            'tone': 'professional',
            'hashtags': 4,
            'emojis': 'minimal',
            'topics': case['topics'],
            'word_count_mode': 'custom_range',
            'min_words': 130,
            'max_words': 220,
            'kb_mode': 'no_kb',
        }
        try:
            response = requests.post(ENDPOINT, json=payload, headers=auth_headers or None, timeout=90)
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

            message = str(data.get('message') or '')
            if response.status_code in {429, 500} and 'quota' in message.lower() and 'retry in' in message.lower():
                retry_match = re.search(r'retry in\s+([0-9]+(?:\.[0-9]+)?)s', message.lower())
                wait_sec = float(retry_match.group(1)) if retry_match else 35.0
                time.sleep(max(5.0, wait_sec + 2.0))
                response = requests.post(ENDPOINT, json=payload, headers=auth_headers or None, timeout=90)
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

            content = (data.get('content') or data.get('text') or data.get('post') or '').strip()

            if response.status_code == 200 and data.get('success') and content:
                evaluated = score_case(case, content)
                status = 'PASS' if evaluated['score'] >= 75 else 'WARN' if evaluated['score'] >= 60 else 'FAIL'
                rows.append({'case': case['name'], 'status': status, 'http': response.status_code, **evaluated})
            else:
                rows.append({
                    'case': case['name'], 'status': 'FAIL', 'http': response.status_code, 'score': 0,
                    'words': 0, 'paragraphs': 0, 'hashtags': [],
                    'reasons': [data.get('message', 'Generation failed')], 'body_preview': ''
                })
        except Exception as exc:
            rows.append({
                'case': case['name'], 'status': 'FAIL', 'http': 0, 'score': 0,
                'words': 0, 'paragraphs': 0, 'hashtags': [],
                'reasons': [str(exc)], 'body_preview': ''
            })

    avg = sum(r['score'] for r in rows) / len(rows)
    passed = sum(1 for r in rows if r['status'] == 'PASS')
    warn = sum(1 for r in rows if r['status'] == 'WARN')
    failed = sum(1 for r in rows if r['status'] == 'FAIL')

    lines = []
    lines.append('# Generation Quality Test Report (5 Industry-Role Cases)')
    lines.append('')
    lines.append(f'- Server: `{BASE}`')
    lines.append('- Endpoint: `/api/generate-preview`')
    lines.append('- Mode: `kb_mode=no_kb` (isolates prompt/domain behavior)')
    lines.append(f'- Overall average score: **{avg:.1f}/100**')
    lines.append(f'- Results: **{passed} PASS**, **{warn} WARN**, **{failed} FAIL**')
    lines.append('')
    lines.append('## Scoring rubric (proxy for suitability + engagement)')
    lines.append('- Relevance to industry/role: 40')
    lines.append('- No cross-domain leakage (e.g., crypto in non-crypto): 20')
    lines.append('- LinkedIn structure/format quality: 25')
    lines.append('- Engagement signals (hook + CTA + readability): 15')
    lines.append('')
    lines.append('## Detailed results')

    for row in rows:
        lines.append(f"### {row['case']} — {row['status']} ({row['score']}/100)")
        lines.append(
            f"- HTTP: {row['http']} | Words: {row['words']} | Paragraphs: {row['paragraphs']} | Hashtags: {len(row['hashtags'])}"
        )
        if row['reasons']:
            lines.append(f"- Notes: {'; '.join(row['reasons'])}")
        if row['body_preview']:
            lines.append(f"- Preview: {row['body_preview']}")
        lines.append('')

    report_path = Path('TEST_GENERATION_5X5_REPORT.md')
    report_path.write_text('\n'.join(lines), encoding='utf-8')

    print('written', report_path)
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
