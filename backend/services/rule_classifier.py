import re
from collections import defaultdict
from typing import Dict, List, Tuple


DOMAIN_KEYWORDS = {
    "Construction / Industrial Services": [
        "procore", "bim", "virtual construction", "estimating", "bidding", "bid", "project lifecycle",
        "project performance", "cost forecasting", "cost structures", "resource planning", "field operations",
        "job cost", "construction", "contractor", "electrical contractor", "industrial services",
        "operational kpis", "project workflows", "erp integrations", "buildops", "spectrum", "dayforce",
    ],
    "Energy / Utilities": [
        "utility", "utilities", "energy", "grid", "power generation", "transmission", "distribution",
        "renewable", "solar", "wind", "meter", "outage", "asset maintenance",
    ],
    "Manufacturing": [
        "manufacturing", "factory", "plant", "production line", "shop floor", "quality control",
        "mes", "bill of materials", "supply planning", "industrial automation",
    ],
    "Logistics / Supply Chain": [
        "logistics", "supply chain", "shipment", "freight", "warehouse operations", "inventory",
        "fulfillment", "route", "transportation", "procurement", "vendor", "3pl",
    ],
    "Healthcare": [
        "patient", "patients", "claims", "ehr", "emr", "clinical", "hipaa", "provider", "providers",
        "payer", "health plan", "care delivery", "medical", "pharmacy", "healthcare data",
    ],
    "FinTech / Financial Infrastructure": [
        "payment", "payments", "banking", "banks", "financial institution", "financial institutions",
        "financial account", "financial accounts", "fraud", "transaction", "transactions", "risk",
        "credit", "fintech", "plaid", "venmo", "sofi", "stripe", "ledger", "money movement",
        "kyc", "aml", "financial infrastructure", "consumer financial data", "financial data",
        "account linking", "trusted financial datasets",
    ],
    "Ad-Tech / Media Analytics": [
        "advertising", "ads", "ad-tech", "campaign", "campaigns", "measurement", "attribution",
        "prime video", "media", "audience", "impressions", "conversion", "roas", "programmatic",
        "identity graph", "publisher", "advertiser", "marketing analytics", "experimentation",
    ],
    "SaaS / Business Operations": [
        "saas", "crm", "customer success", "subscription", "tenant", "multi-tenant", "customer platform",
        "product-led", "customer lifecycle", "revenue operations", "usage analytics", "business operations",
        "meal planning", "foodservice", "menu", "customer reporting",
    ],
    "Consulting / Enterprise Transformation": [
        "client", "clients", "stakeholder", "consulting", "pwc", "deloitte", "accenture", "bain",
        "mckinsey", "advisory", "transformation", "enterprise transformation", "multi-cloud strategy",
        "governance", "operating model", "architecture strategy", "roadmap", "change management",
        "client delivery", "architecture documentation", "standards",
    ],
    "Retail / E-commerce": [
        "orders", "cart", "checkout", "retail", "product catalog", "marketplace", "merchant", "sku",
        "pricing", "returns", "customer purchase", "e-commerce", "ecommerce",
    ],
}

ENGINEERING_KEYWORDS = {
    "Cloud Data Architecture / Data Engineering": [
        "architecture", "guidelines", "governance", "aws", "azure", "gcp", "cost optimization",
        "scalability", "data infrastructure", "data systems", "multi-cloud",
    ],
    "Data Integration + Analytics Engineering": [
        "api", "api integration", "api ingestion", "integration", "integrations", "ingest", "erp",
        "multiple systems", "reporting", "dashboard", "power bi", "tableau", "analytics-ready",
    ],
    "Data Integration / Analytics Engineering": [
        "data integration", "etl", "elt", "sql", "warehouse", "data model", "business entities",
        "reporting", "dashboards", "analytics engineering",
    ],
    "Big Data Platform Engineering": [
        "big data", "distributed", "spark", "emr", "databricks", "lake", "petabyte", "kafka",
        "kinesis", "flink", "streaming", "events", "real-time",
    ],
    "Data Platform Engineering": [
        "platform", "infrastructure", "data platform", "warehouse scalability", "trusted datasets",
        "data reliability", "privacy", "auditability",
    ],
}

SPEED_KEYWORDS = {
    "Streaming-heavy": ["kafka", "kinesis", "flink", "streaming", "real-time", "event-driven", "events"],
    "Batch-heavy": [
        "batch", "scheduled", "daily", "etl", "elt", "airflow", "erp", "reporting", "dashboard",
        "dashboards", "warehouse", "power bi", "tableau", "ssis",
    ],
    "Hybrid": ["batch and streaming", "streaming and batch", "real-time and batch", "etl/elt and streaming"],
}

MATURITY_KEYWORDS = {
    "Enterprise Consulting": ["client", "clients", "consulting", "pwc", "firm", "advisory", "travel", "governance"],
    "Growth-stage FinTech Platform": ["plaid", "venmo", "sofi", "stripe", "fintech", "financial infrastructure", "growth"],
    "Mid-size Industrial Enterprise": ["construction", "industrial services", "contractor", "project lifecycle", "erp"],
    "SaaS Product Company": ["saas", "subscription", "multi-tenant", "customer platform", "product-led"],
    "Big Tech / Platform Organization": ["amazon", "prime video", "meta", "google", "distributed", "petabyte"],
    "Enterprise Internal Analytics Team": ["internal", "business operations", "enterprise systems", "reporting", "dashboards"],
}

GENERIC_TECH_TERMS = {
    "api", "apis", "integration", "integrations", "platform", "software", "cloud", "sql", "python",
    "warehouse", "etl", "elt", "dashboard", "reporting", "salesforce",
}

DOMAIN_PHRASES = {
    "Construction / Industrial Services": [
        "project lifecycle", "cost forecasting", "cost structures", "operational kpis",
        "estimating and bidding", "erp integrations", "project performance dashboards",
    ],
    "FinTech / Financial Infrastructure": [
        "financial accounts", "financial institutions", "consumer financial data", "financial infrastructure",
        "trusted financial datasets", "payments", "venmo", "sofi",
    ],
    "Ad-Tech / Media Analytics": [
        "campaign measurement", "attribution", "advertising", "impressions", "campaign analytics",
    ],
    "Healthcare": ["patients", "claims", "emr", "clinical", "providers"],
    "Consulting / Enterprise Transformation": [
        "client delivery", "enterprise transformation", "governance", "architecture documentation",
        "multi-cloud strategy",
    ],
}


def _contains(text: str, phrase: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text))


def score_category(text: str, categories: Dict[str, List[str]], domain_mode: bool = False) -> Tuple[str, float, List[str], List[str]]:
    lowered = text.lower()
    scores = defaultdict(float)
    evidence = defaultdict(list)
    for category, words in categories.items():
        for word in words:
            if _contains(lowered, word):
                normalized = word.lower()
                if domain_mode:
                    weight = 0.35 if normalized in GENERIC_TECH_TERMS else 2.0
                    if " " in normalized:
                        weight += 1.0
                    if normalized in {"procore", "bim", "plaid", "venmo", "sofi", "prime video", "pwc", "hipaa"}:
                        weight += 2.0
                else:
                    weight = 2.0 if " " in normalized else 1.0
                scores[category] += weight
                evidence[category].append(word)
    if not scores:
        return "General / Unknown", 0.35, [], []
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    winner, top_score = ranked[0]
    total = sum(scores.values())
    margin = top_score - (ranked[1][1] if len(ranked) > 1 else 0)
    confidence = min(0.95, max(0.48, 0.42 + (top_score / max(total, 1)) * 0.42 + min(margin, 6) * 0.03))
    alternatives = [c for c, _ in ranked[1:3]]
    return winner, round(confidence, 2), evidence[winner][:8], alternatives


def extract_meaningful_phrases(text: str, category: str, seeds: List[str]) -> List[str]:
    lowered = text.lower()
    candidates: list[str] = []
    for phrase in DOMAIN_PHRASES.get(category, []):
        if phrase in lowered:
            candidates.append(phrase)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    for sentence in sentences:
        clean = " ".join(sentence.strip(" -*\t").split())
        if len(clean) < 24 or len(clean) > 180:
            continue
        clean_lower = clean.lower()
        if any(seed.lower() in clean_lower for seed in seeds):
            candidates.append(clean)
    deduped: list[str] = []
    for candidate in candidates:
        if candidate.lower() in GENERIC_TECH_TERMS:
            continue
        if not any(candidate.lower() in item.lower() or item.lower() in candidate.lower() for item in deduped):
            deduped.append(candidate)
    return deduped[:8]


def _evidence_item(phrase: str, reason: str) -> str:
    return f"{phrase} - {reason}"


def classify_jd(job_description: str):
    business, b_conf, b_ev, alternatives = score_category(job_description, DOMAIN_KEYWORDS, domain_mode=True)
    engineering, e_conf, e_ev, _ = score_category(job_description, ENGINEERING_KEYWORDS)
    speed, s_conf, s_ev, _ = score_category(job_description, SPEED_KEYWORDS)
    maturity, m_conf, m_ev, _ = score_category(job_description, MATURITY_KEYWORDS)

    lowered = job_description.lower()
    has_streaming = any(_contains(lowered, k) for k in SPEED_KEYWORDS["Streaming-heavy"])
    has_batch = any(_contains(lowered, k) for k in SPEED_KEYWORDS["Batch-heavy"])
    if has_streaming and has_batch:
        speed = "Hybrid"
        s_ev = ["batch/reporting workflows", "streaming or event-driven systems"]
        s_conf = max(s_conf, 0.82)
    elif has_batch:
        speed = "Batch-heavy"
        s_conf = max(s_conf, 0.76)
    elif has_streaming:
        speed = "Streaming-heavy"
        s_conf = max(s_conf, 0.76)

    if business == "Construction / Industrial Services" and "analytics" in lowered:
        engineering = "Data Integration + Analytics Engineering"
        e_conf = max(e_conf, 0.78)
    elif business == "Consulting / Enterprise Transformation":
        engineering = "Cloud Data Architecture / Data Engineering"
        e_conf = max(e_conf, 0.78)
    elif business == "Ad-Tech / Media Analytics" and has_streaming:
        engineering = "Big Data Platform Engineering"
        e_conf = max(e_conf, 0.8)
    elif business == "SaaS / Business Operations" and "integration" in lowered:
        engineering = "Data Integration / Analytics Engineering"
        e_conf = max(e_conf, 0.76)
    elif business == "FinTech / Financial Infrastructure" and any(term in lowered for term in ["platform", "platforms", "financial infrastructure", "trusted financial datasets"]):
        engineering = "Data Platform Engineering"
        e_conf = max(e_conf, 0.76)

    overall_conf = round((b_conf + e_conf + s_conf + m_conf) / 4, 2)
    phrases = extract_meaningful_phrases(job_description, business, b_ev)
    evidence = [
        _evidence_item(phrase, f"Indicates {business} domain")
        for phrase in phrases
    ]
    evidence += [
        _evidence_item(", ".join(e_ev[:3]), f"Supports {engineering}") if e_ev else "",
        _evidence_item(", ".join(s_ev[:3]), f"Supports {speed} delivery pattern") if s_ev else "",
        _evidence_item(", ".join(m_ev[:3]), f"Supports {maturity} maturity classification") if m_ev else "",
    ]
    evidence = [item for item in dict.fromkeys(evidence) if item][:10]
    rationale = [
        f"Business domain favored {business} because industry/customer signals outweighed generic technology terms.",
        f"Engineering domain favored {engineering} from integration, platform, architecture, warehouse, or analytics language.",
        f"Speed pattern is {speed} based on ERP/reporting/batch versus streaming/event-system signals.",
    ]
    return {
        "business_domain": business,
        "engineering_domain": engineering,
        "speed_pattern": speed,
        "company_maturity": maturity,
        "confidence": overall_conf,
        "evidence": evidence,
        "alternative_domains": alternatives,
        "rationale": rationale,
    }
