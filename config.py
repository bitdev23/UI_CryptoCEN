"""Configuration for Mantraj AI LinkedIn automation."""
from typing import List, Dict

# Legacy profiles — kept for backward compatibility with main.py CLI only.
# The web app (app.py / dashboard_enterprise) does NOT use PROFILES.
# All generation uses per-user industry/role/tone settings.
PROFILES = {
    "valtrilabs": {
        "company_info": {
            "name": "ValtriLabs",
            "services": "Virtual assistant services: admin support, calendar management, lead qualification, research, and operations",
            "audience": "Founders, solopreneurs, small business owners, and busy executives",
            "value_prop": "Reliable, skilled virtual assistants that let leaders focus on growth while we handle the day-to-day",
        },
        "content_themes": [
            "VA benefits",
            "productivity tips",
            "case studies",
            "client wins",
            "tooling & automation",
            "pricing transparency",
        ],
        "hashtags": [
            "#VirtualAssistant",
            "#Productivity",
            "#SmallBusiness",
            "#Founders",
            "#RemoteWork",
        ],
    },
    "arab_global_crypto": {
        "company_info": {
            "name": "Arab Global Crypto Exchange",
            "services": "Centralized exchange: Crypto trading, custody, KYC, liquidity, and institutional-grade security (Fireblocks)",
            "audience": "Crypto traders, developers, institutional clients, product teams in fintech and blockchain",
            "value_prop": "Educational content on crypto trading, blockchain technology, and infrastructure for traders and builders",
        },
        "content_themes": [
            # Blockchain (35%)
            "EVM opcodes and gas optimization for smart contracts",
            "Cross-chain message passing and security considerations",
            "Merkle trees and proof structures in blockchain",
            "Consensus mechanisms: PoW, PoS, PoA trade-offs",
            "Account abstraction and wallet infrastructure evolution",
            "Sharding and data availability solutions",
            "Cryptographic primitives: signatures and zero-knowledge proofs",
            "Rollups vs sidechains: scaling architecture comparison",
            # Crypto Economics (35%)
            "MEV-resistant consensus and sequencer economics",
            "Advanced DeFi mechanics: flash loans and composability risks",
            "Tokenomics design: emission schedules and incentive alignment",
            "Institutional custody solutions and cold storage infrastructure",
            "Cryptographic key management across different hardware",
            "Compliance frameworks: FATF and AML/KYC implementation",
            "DAO governance models and voting mechanisms",
            "Yield farming strategies and protocol governance mechanisms",
            # Product-Market Fit & Strategy (10%)
            "Product strategy: distribution mechanisms for token launches",
            "User acquisition in DeFi: incentive design and retention",
            "PMF signals in blockchain protocols: metrics that matter",
            # Centralized Exchange Operations (10%)
            "Exchange infrastructure: orderbook vs AMM architectures",
            "Liquidity management and market maker economics",
            "Trading engine architecture and match algorithms",
            # Trading (10%)
            "Market microstructure and order flow dynamics",
            "Arbitrage opportunities across DEX/CEX fragmentation",
            "Options pricing models and volatility surfaces in crypto",
        ],
        "hashtags": [
            "#Crypto",
            "#Blockchain",
            "#NFT",
            "#DeFi",
            "#CeFi",
            "#Fireblocks",
        ],
    },
}

POST_FORMATS: List[str] = [
    "educational",
    "question",
    "story",
    "list",
    "myth-busting",
]

BRAND_VOICE: Dict[str, str] = {
    "tone": "Professional, approachable, and helpful",
    "dos": "Short paragraphs, actionable tips, clear CTAs, human examples",
    "donts": "Overly salesy language, long dense paragraphs, vague claims",
}

LINKEDIN_BEST_PRACTICES: Dict[str, int] = {
    "min_length": 150,
    "max_length": 300,
}

DEFAULT_SCHEDULE = {"hour": 11, "minute": 0}

# Default profile key to use. Can be overridden by env var CONTENT_PROFILE
DEFAULT_PROFILE = "valtrilabs"


DEFAULT_SCHEDULE = {"hour": 11, "minute": 0}
