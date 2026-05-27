import re
from difflib import SequenceMatcher
from typing import Iterable

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is",
    "it", "of", "on", "or", "the", "to", "with", "via", "will", "you", "your"
}

REAL_SHORT_TOOLS = {"bi", "go", "r"}

SEMANTIC_EQUIVALENTS = {
    "api-based data integration": ["api ingestion", "api integrations", "python api ingestion framework"],
    "bi / visualization": ["power bi", "tableau", "dashboards", "business intelligence"],
    "data pipelines": ["etl", "elt", "elt pipelines", "etl pipelines", "pipeline orchestration", "data integration workflows"],
    "data warehouse": ["azure synapse", "redshift", "amazon redshift", "snowflake", "warehouse engineering", "cloud warehouse"],
    "elt pipelines": ["data pipelines", "etl pipelines", "pipeline orchestration", "data ingestion"],
    "etl pipelines": ["data pipelines", "elt pipelines", "data integration"],
    "azure synapse": ["data warehouse", "warehouse engineering", "sql analytics warehouse"],
    "amazon redshift": ["data warehouse", "warehouse engineering", "cloud warehouse"],
    "redshift": ["data warehouse", "warehouse engineering", "cloud warehouse"],
    "snowflake": ["data warehouse", "warehouse engineering", "cloud warehouse"],
    "stakeholder collaboration": ["business analysts", "stakeholders", "business partners", "cross-functional partners", "stakeholder management"],
    "business analysts": ["stakeholder collaboration", "stakeholders", "business stakeholders", "cross-functional partners"],
    "stakeholders": ["stakeholder collaboration", "business analysts", "business partners", "cross-functional partners"],
    "spark structured streaming": ["streaming pipelines", "real-time data processing", "spark streaming"],
    "streaming pipelines": ["spark structured streaming", "kafka", "real-time data processing"],
    "dbt": ["sql transformations", "analytics engineering", "warehouse transformations"],
    "data governance": ["governance", "data quality", "standards", "access controls"],
    "slas": ["reliability targets", "operational reliability", "service levels"],
    "golden datasets": ["certified datasets", "trusted datasets", "canonical data models"],
    "analytics enablement": ["self-service analytics", "business reporting", "stakeholder enablement"],
}

NORMALIZED_SKILLS = {
    "api ingestion": "API-based Data Integration",
    "api integration": "API-based Data Integration",
    "api integrations": "API-based Data Integration",
    "azure synapse": "Data Warehouse",
    "redshift": "Data Warehouse",
    "snowflake": "Data Warehouse",
    "power bi": "BI / Visualization",
    "tableau": "BI / Visualization",
    "business analysts": "Stakeholder Collaboration",
    "stakeholder": "Stakeholder Collaboration",
    "elt": "Data Pipelines",
    "etl": "Data Pipelines",
    "performance": "Query Optimization",
    "scalability": "Warehouse Scalability",
    "quality": "Data Quality",
    "warehouse": "Data Warehousing",
    "modeling": "Data Modeling",
    "schema": "Schema Design",
    "reliability": "Data Reliability",
    "pipelines": "Data Pipelines",
    "stakeholders": "Stakeholder Management",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def normalize_skill(value: str) -> str:
    lowered = normalize_text(value)
    for token, normalized in sorted(NORMALIZED_SKILLS.items(), key=lambda item: len(item[0]), reverse=True):
        if token in lowered:
            return normalized
    return value.strip()


def is_meaningful_evidence(value: str | None) -> bool:
    if not value:
        return False
    cleaned = normalize_text(value)
    tokens = re.findall(r"[a-z0-9+#]+", cleaned)
    if not tokens:
        return False
    if len(tokens) == 1:
        token = tokens[0]
        return (len(token) >= 3 and token not in STOPWORDS) or token in REAL_SHORT_TOOLS
    return any((len(token) >= 3 or token in REAL_SHORT_TOOLS) and token not in STOPWORDS for token in tokens)


def dedupe_phrases(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in items:
        item = " ".join(str(raw).strip().split())
        if not item:
            continue
        lower = item.lower()
        if any(lower == existing.lower() or lower in existing.lower() or existing.lower() in lower for existing in result):
            continue
        result.append(item)
    return result


def phrase_similarity(left: str, right: str) -> float:
    l_norm = normalize_text(left)
    r_norm = normalize_text(right)
    if not l_norm or not r_norm:
        return 0.0
    if l_norm in r_norm or r_norm in l_norm:
        return 1.0
    l_tokens = set(re.findall(r"[a-z0-9]+", l_norm))
    r_tokens = set(re.findall(r"[a-z0-9]+", r_norm))
    token_score = len(l_tokens & r_tokens) / max(len(l_tokens | r_tokens), 1)
    sequence_score = SequenceMatcher(None, l_norm, r_norm).ratio()
    return max(token_score, sequence_score * 0.85)


def extract_resume_phrase(resume: str, needle: str, max_chars: int = 120) -> str:
    needle_lower = normalize_text(needle)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", resume)
    for sentence in sentences:
        clean = " ".join(sentence.strip(" -*\t").split())
        if needle_lower and needle_lower in normalize_text(clean) and is_meaningful_evidence(clean):
            return clean[:max_chars]
    return needle


def semantic_support_detail(term: str, resume: str) -> dict[str, object]:
    resume_lower = normalize_text(resume)
    term_lower = normalize_text(term)
    if term_lower and term_lower in resume_lower:
        return {
            "bucket": "exact_match",
            "evidence": extract_resume_phrase(resume, term),
            "confidence": 0.92,
            "support_level": "strongly_supported",
        }

    equivalents = SEMANTIC_EQUIVALENTS.get(term_lower, [])
    for equivalent in equivalents:
        if normalize_text(equivalent) in resume_lower:
            return {
                "bucket": "semantic_match",
                "evidence": extract_resume_phrase(resume, equivalent),
                "confidence": 0.82,
                "support_level": "partially_supported",
            }

    for source, equivalents in SEMANTIC_EQUIVALENTS.items():
        if term_lower in equivalents and source in resume_lower:
            return {
                "bucket": "semantic_match",
                "evidence": extract_resume_phrase(resume, source),
                "confidence": 0.8,
                "support_level": "partially_supported",
            }

    for resume_phrase in re.findall(r"\b(?:[A-Za-z0-9+#]+\s+){0,4}[A-Za-z0-9+#]+\b", resume):
        if is_meaningful_evidence(resume_phrase) and phrase_similarity(term, resume_phrase) >= 0.82:
            return {
                "bucket": "semantic_match",
                "evidence": resume_phrase,
                "confidence": 0.72,
                "support_level": "partially_supported",
            }

    inferred_patterns = {
        "stakeholder management": ["stakeholder", "business partner", "cross-functional", "requirements"],
        "cross-functional collaboration": ["cross-functional", "business", "product", "engineering"],
        "data quality mindset": ["validation", "quality checks", "reconciliation", "testing"],
        "ownership": ["owned", "led", "maintained", "production"],
        "ambiguity handling": ["ambiguous", "requirements", "discovery", "scoped"],
        "data warehouse": ["redshift", "synapse", "snowflake", "warehouse"],
        "data reliability": ["monitoring", "alerts", "sla", "reliability", "production"],
    }
    for concept, signals in inferred_patterns.items():
        if term_lower == concept or phrase_similarity(term_lower, concept) >= 0.72:
            hits = [signal for signal in signals if signal in resume_lower]
            if len(hits) >= 1:
                evidence = extract_resume_phrase(resume, hits[0])
                return {
                    "bucket": "inferred_match",
                    "evidence": evidence if is_meaningful_evidence(evidence) else ", ".join(hits[:3]),
                    "confidence": 0.58,
                    "support_level": "inferred_support",
                }

    return {"bucket": "missing", "evidence": None, "confidence": 0.0, "support_level": "truly_missing"}


def semantic_support(term: str, resume: str) -> tuple[str, str | None]:
    detail = semantic_support_detail(term, resume)
    return str(detail["bucket"]), detail["evidence"] if detail["evidence"] else None


def classify_support(terms: Iterable[str], resume: str) -> dict[str, list[str]]:
    buckets = {
        "exact_match": [],
        "semantic_match": [],
        "inferred_match": [],
        "missing": [],
    }
    for term in dedupe_phrases(terms):
        detail = semantic_support_detail(term, resume)
        bucket = str(detail["bucket"])
        evidence = detail["evidence"]
        if bucket == "exact_match":
            buckets[bucket].append(term)
        elif bucket in {"semantic_match", "inferred_match"}:
            if is_meaningful_evidence(str(evidence)):
                buckets[bucket].append(f"{term} -> supported by {evidence}")
            else:
                buckets["missing"].append(term)
        else:
            buckets[bucket].append(term)
    return buckets


def classify_support_records(terms: Iterable[str], resume: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for term in dedupe_phrases(normalize_skill(item) for item in terms):
        key = normalize_text(term)
        if key in seen:
            continue
        seen.add(key)
        detail = semantic_support_detail(term, resume)
        records.append(
            {
                "jd_concept": term,
                "support_type": detail["bucket"],
                "resume_evidence": detail["evidence"],
                "confidence": detail["confidence"],
                "support_level": detail["support_level"],
            }
        )
    return records
