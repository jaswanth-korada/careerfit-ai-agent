from schemas.analysis_schema import KeywordAnalysis
from services.llm_client import llm_client
from services.semantic_matching import classify_support, classify_support_records, dedupe_phrases, normalize_skill

KEYWORDS = [
    "SQL", "Python", "ETL", "ELT", "data pipelines", "data modeling", "data warehouse", "AWS", "Azure", "GCP",
    "AWS Glue", "AWS Lambda", "Azure Data Factory", "Azure Functions", "Dataproc", "Dataflow", "Spark", "Airflow",
    "governance", "security", "data flow diagrams", "architecture guidelines", "cost optimization", "performance", "scalability",
    "stakeholders", "client", "documentation", "data integration", "DBT", "Atlan", "Retool", "SLAs", "privacy",
    "golden datasets", "analytics enablement", "ELT pipelines", "Azure Synapse", "business analysts",
    "Spark Structured Streaming", "cross-functional collaboration", "ownership", "stakeholder management",
    "business partnership", "ambiguity handling", "communication", "data quality mindset", "Power BI", "Tableau",
    "API ingestion", "API integration", "API-based Data Integration", "business analysts", "PMs", "MuleSoft",
    "SSIS", "Procore", "BuildOps", "Spectrum", "Dayforce", "BIM", "ERP", "SLA", "cost forecasting",
    "operational KPIs", "privacy", "governance", "campaign analytics", "attribution", "financial institutions",
    "payments", "patients", "claims", "EMR", "clinical", "providers"
]

BONUS_KEYWORDS = [
    "dbt", "Atlan", "Retool", "Procore", "BuildOps", "Spectrum", "Dayforce", "SSIS", "MuleSoft", "BIM",
    "ERP", "SLA", "SLAs", "governance", "privacy", "cost forecasting", "operational KPIs"
]

DOMAIN_TERMS = [
    "project lifecycle", "cost forecasting", "operational KPIs", "financial accounts", "financial institutions",
    "payments", "Venmo", "SoFi", "campaigns", "attribution", "measurement", "ads", "impressions",
    "patients", "claims", "EMR", "clinical", "providers", "clients", "advisory", "transformation",
    "consulting", "governance", "ERP", "BIM"
]

TOOL_BUCKETS = {
    "cloud": ["AWS", "Azure", "GCP", "S3", "Glue", "Lambda", "Azure Data Factory", "Dataproc", "Dataflow"],
    "programming": ["Python", "SQL", "Scala", "Java"],
    "orchestration": ["Airflow", "Azure Data Factory", "Step Functions"],
    "warehousing": ["Redshift", "Synapse", "Snowflake", "data warehouse"],
    "governance": ["governance", "security", "compliance", "data quality", "documentation", "Atlan", "privacy"],
    "enablement": ["Retool", "SLAs", "golden datasets", "analytics enablement"],
}


def _fallback_extract_keywords(job_description: str, resume: str) -> KeywordAnalysis:
    jd_lower = job_description.lower()
    present_raw = [kw for kw in KEYWORDS if kw.lower() in jd_lower]
    present = dedupe_phrases(normalize_skill(kw) for kw in present_raw)
    if "api ingestion" in jd_lower or "api integration" in jd_lower or "api integrations" in jd_lower:
        present.append("API-based Data Integration")
    if any(term in jd_lower for term in ["power bi", "tableau", "dashboard", "dashboards"]):
        present.append("BI / Visualization")
    present = dedupe_phrases(present)
    support = classify_support(present, resume)
    records = classify_support_records(present, resume)
    missing = support["missing"]

    must_have = [
        kw for kw in present
        if kw in [
            "SQL", "Python", "Data Pipelines", "Data Modeling", "Data Warehouse", "AWS", "Azure",
            "Azure Data Factory", "API-based Data Integration", "BI / Visualization"
        ]
    ]
    important = [kw for kw in present if kw not in must_have][:12]
    bonus = [
        normalize_skill(kw)
        for kw in BONUS_KEYWORDS + [
            "GCP", "Dataproc", "Dataflow", "architecture guidelines", "data flow diagrams",
            "cost optimization", "golden datasets", "analytics enablement"
        ]
        if kw.lower() in jd_lower
    ]
    bonus = dedupe_phrases(bonus)
    tools = dedupe_phrases(
        item
        for bucket_items in TOOL_BUCKETS.values()
        for item in bucket_items
        if item.lower() in jd_lower
    )
    domain_terms = dedupe_phrases(term for term in DOMAIN_TERMS if term.lower() in jd_lower)

    tool_stack = {}
    for bucket, items in TOOL_BUCKETS.items():
        tool_stack[bucket] = [item for item in items if item.lower() in jd_lower]

    soft = [
        kw for kw in [
            "cross-functional collaboration", "ownership", "stakeholder management", "business partnership",
            "ambiguity handling", "communication", "data quality mindset", "client relationship management"
        ]
        if kw in jd_lower or kw.split()[0] in jd_lower
    ]
    evidence = dedupe_phrases(
        [
            (
                f"{record['jd_concept']}: {record['support_type']} at {record['confidence']} "
                f"supported by {record['resume_evidence']}"
            )
            for record in records
            if record["support_type"] != "missing" and record["resume_evidence"]
        ]
    )[:12]

    return KeywordAnalysis(
        must_have=must_have or present[:6],
        important=important,
        bonus=bonus,
        tools=tools,
        domain_terms=domain_terms,
        missing_from_resume=missing,
        tool_stack=tool_stack,
        soft_skill_signals=soft,
        exact_match=support["exact_match"],
        semantic_match=support["semantic_match"],
        inferred_match=support["inferred_match"],
        confidence_levels={
            "strongly_supported": support["exact_match"],
            "partially_supported": support["semantic_match"],
            "inferred_support": support["inferred_match"],
            "truly_missing": support["missing"],
        },
        confidence=0.72 if present else 0.45,
        evidence=evidence,
    )


def extract_keywords(job_description: str, resume: str) -> KeywordAnalysis:
    fallback = _fallback_extract_keywords(job_description, resume)
    return llm_client.generate(
        schema=KeywordAnalysis,
        fallback=fallback,
        route="ats_keyword_agent",
        system_prompt=(
            "PROMPT_VERSION=v2. You are the ATS Keyword + Semantic Matching Agent. Extract requirements from the JD "
            "and compare them to the resume using exact, semantic, and inferred support. Treat ELT pipelines as data "
            "pipelines, Azure Synapse/Redshift/Snowflake as warehouse engineering, business analysts as stakeholders, "
            "Power BI/Tableau as BI / Visualization, and API ingestion/API integration as API-based Data Integration. "
            "Never use single stopwords or tokens shorter than 3 characters as evidence unless they are real tools like BI. "
            "Never classify semantically supported concepts as weak or truly missing. Put only truly missing JD terms "
            "in missing_from_resume. Prioritize JD-specific tools such as dbt, Atlan, Retool, Procore, BuildOps, Spectrum, "
            "Dayforce, SSIS, MuleSoft, BIM, ERP, SLA, governance, privacy, cost forecasting, and operational KPIs. "
            "Use meaningful resume phrases and support reasons in evidence."
        ),
        user_prompt=(
            "Extract ATS and hiring-manager keywords from the job description. Split them into must_have, "
            "important, bonus, tools, and domain_terms. Group tools in tool_stack by category. Identify soft_skill_signals and "
            "keywords missing from the resume. Return exact_match, semantic_match, inferred_match, and confidence_levels "
            "with these categories: strongly_supported, partially_supported, inferred_support, truly_missing. Include "
            "soft skills such as cross-functional collaboration, ownership, stakeholder management, business partnership, "
            "ambiguity handling, communication, and data quality mindset when supported by the JD.\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"RESUME:\n{resume}"
        ),
    )
