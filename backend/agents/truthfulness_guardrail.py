from schemas.analysis_schema import GuardrailReport, KeywordAnalysis
from services.llm_client import llm_client


def _dedupe_case_insensitive(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _fallback_guardrails(keywords: KeywordAnalysis, resume: str) -> GuardrailReport:
    missing = set(keywords.missing_from_resume)
    do_not = []
    reframes = []
    risky = []
    unsupported_tools = []
    unsupported_scale = []
    unsupported_domain = []
    unsupported_architecture = []
    resume_lower = resume.lower()
    requested = set(keywords.tools + keywords.bonus + keywords.domain_terms + keywords.must_have + keywords.important)
    high_risk_tools = {"Procore", "BuildOps", "Spectrum", "Dayforce", "MuleSoft", "SSIS", "dbt", "Atlan", "Golang"}
    governance_terms = {"governance", "security", "privacy", "auditability", "access controls"}
    domain_markers = {"BIM", "project lifecycle", "cost forecasting", "operational KPIs", "financial institutions", "payments", "patients", "claims", "campaigns", "attribution"}

    for item in sorted(requested):
        normalized = item.lower()
        if normalized in resume_lower:
            continue
        if item in high_risk_tools or normalized in {tool.lower() for tool in high_risk_tools}:
            unsupported_tools.append(f"high severity: {item} appears in the JD but is not directly supported by the resume.")
            do_not.append(f"Do not claim direct {item} ownership or hands-on experience unless the candidate can defend it.")
        elif normalized in governance_terms:
            unsupported_domain.append(f"moderate severity: {item} needs evidence of controls, access, auditability, policy, or compliance work.")
        elif item in domain_markers or normalized in {term.lower() for term in domain_markers}:
            unsupported_domain.append(f"moderate severity: {item} is a domain-specific claim and should be framed as JD context, not prior experience.")

    for item in missing:
        normalized = item.lower()
        if item in {"GCP", "Dataproc", "Dataflow", "DBT", "Atlan", "Retool"}:
            unsupported_tools.append(f"medium severity: {item} is requested by the JD but not directly supported by the resume.")
            do_not.append(f"Do not claim direct {item} ownership or production experience unless it is true.")
            reframes.append(f"Position adjacent warehouse, pipeline, or governance experience as transferable instead of claiming direct {item} ownership.")
        elif item in {"data flow diagrams", "architecture guidelines", "golden datasets", "analytics enablement"}:
            unsupported_architecture.append(f"medium severity: {item} could imply architecture ownership beyond resume evidence.")
            risky.append(f"{item}: safe only if the candidate can defend specific design artifacts or owned datasets.")
            reframes.append("Use: 'contributed to data architecture discussions and documented pipeline designs' only if accurate.")
        elif item in {"governance", "security", "privacy"}:
            unsupported_domain.append(f"medium severity: {item} domain claim needs resume-backed controls, access, validation, or compliance evidence.")
            reframes.append("Use existing data quality, validation, access-control, or monitoring experience to show governance awareness.")
        elif "scale" in normalized or "petabyte" in normalized or "millions" in normalized:
            unsupported_scale.append(f"high severity: {item} scale language is not safe without matching resume metrics.")

    if not do_not:
        do_not.append("Do not add JD tools, scale, domains, or ownership claims unless the resume or interview evidence can defend them.")
    if "azure synapse" in " ".join(missing).lower() and "redshift" in resume_lower:
        reframes.append("Position Redshift experience as transferable cloud warehouse engineering instead of claiming Azure Synapse experience.")
    if any(tool.lower() in " ".join(requested).lower() for tool in ["mulesoft", "ssis", "procore", "buildops", "spectrum", "dayforce"]):
        reframes.append("Position Azure Data Factory and Python API ingestion as transferable integration experience instead of claiming ownership of unsupported enterprise or construction platforms.")
    if any(tool.lower() in " ".join(requested).lower() for tool in ["dbt", "atlan", "golang"]):
        reframes.append("Use SQL-based ELT and cloud warehouse optimization experience instead of claiming direct dbt, Atlan, or Golang ownership.")
    if "bim" in " ".join(requested).lower() or "cost forecasting" in " ".join(requested).lower():
        reframes.append("Frame construction terms as target-domain priorities: operational reporting pipelines, project performance analytics, and ERP-style integrations.")
    if "petabyte" in " ".join(job for job in missing).lower():
        reframes.append("Keep scale claims to resume-backed metrics such as 800GB+ daily processing or 4TB/month, without inflating to petabyte-scale ownership.")

    return GuardrailReport(
        do_not_claim=_dedupe_case_insensitive(do_not),
        unsupported_tools=_dedupe_case_insensitive(unsupported_tools),
        unsupported_scale_claims=_dedupe_case_insensitive(unsupported_scale),
        unsupported_domain_claims=_dedupe_case_insensitive(unsupported_domain),
        unsupported_architecture_claims=_dedupe_case_insensitive(unsupported_architecture),
        safe_reframes=_dedupe_case_insensitive(reframes),
        risky_insertions=_dedupe_case_insensitive(risky),
        confidence=0.75,
        evidence=[
            f"{item}: missing or only indirectly supported by resume evidence"
            for item in keywords.missing_from_resume[:8]
        ],
    )


def run_guardrails(job_description: str, keywords: KeywordAnalysis, resume: str) -> GuardrailReport:
    fallback = _fallback_guardrails(keywords, resume)
    return llm_client.generate(
        schema=GuardrailReport,
        fallback=fallback,
        route="truthfulness_guardrail",
        system_prompt=(
            "PROMPT_VERSION=v2. You are the Resume Credibility Auditor. Prevent resume hallucinations while preserving "
            "strong truthful positioning. Detect unsupported tools, scale inflation, unsupported domain expertise, and "
            "unsupported architecture ownership. Assign severity in each warning string: low, medium, or high. Include "
            "evidence for every warning and generate intelligent safe reframes that translate adjacent experience without "
            "claiming direct ownership."
        ),
        user_prompt=(
            "Review the JD, keyword analysis, and resume. Return do_not_claim warnings plus structured categories: "
            "unsupported_tools, unsupported_scale_claims, unsupported_domain_claims, unsupported_architecture_claims, "
            "risky_insertions, safe_reframes, confidence, and evidence. Be strict but nuanced: semantic support can be "
            "truthful, direct unsupported tool or scale claims are not. Example: 'Position Azure Synapse and Redshift "
            "experience as transferable warehouse engineering instead of claiming direct DBT ownership.'\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"KEYWORD ANALYSIS:\n{keywords.model_dump_json()}\n\n"
            f"RESUME:\n{resume}"
        ),
    )
