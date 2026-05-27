from schemas.analysis_schema import (
    Classification,
    HiringNarrative,
    KeywordAnalysis,
    ResumeMatch,
)
from services.llm_client import llm_client


def _fallback_narrative(
    company_name: str | None,
    classification: Classification,
    keywords: KeywordAnalysis,
    resume_match: ResumeMatch,
) -> HiringNarrative:
    company = company_name or "this company"
    strong = ", ".join(resume_match.strong_matches[:4]) or "the strongest resume-backed requirements"
    weak = ", ".join(resume_match.weak_matches[:3]) or "the least-supported JD requirements"
    overall = resume_match.scores.overall_match
    probability = "high" if overall >= 78 else "moderate" if overall >= 62 else "low-to-moderate"
    confidence = "high" if resume_match.confidence >= 0.75 and classification.confidence >= 0.7 else "moderate"
    domain_label = classification.business_domain if classification.confidence >= 0.75 else "operational analytics"
    domain_lower = domain_label.lower()
    if "construction" in domain_lower or "industrial" in domain_lower:
        why_context = "operational analytics that support project performance, cost visibility, and business decision-making"
        candidate_context = "ETL/ELT pipelines, API-based integrations, and analytics-ready datasets"
    elif "fintech" in domain_lower:
        why_context = "trusted financial datasets, privacy-aware data reliability, and analytics enablement"
        candidate_context = "SQL-based ELT, cloud warehouse optimization, and reliable data pipelines"
    elif "consult" in domain_lower:
        why_context = "client delivery, cloud modernization, governance, and architecture documentation"
        candidate_context = "cloud data pipelines, stakeholder requirements, and architecture-aware data delivery"
    elif "ad-tech" in domain_lower or "media" in domain_lower:
        why_context = "campaign analytics, measurement, attribution, and event-informed reporting"
        candidate_context = "analytics pipelines, warehouse models, and data reliability practices"
    elif "saas" in domain_lower:
        why_context = "SaaS integrations, API ingestion, warehouse operations, and customer or business reporting"
        candidate_context = "API-based ingestion, ETL/ELT pipelines, SQL modeling, and analytics-ready datasets"
    else:
        why_context = "data engineering work tied to reliable reporting, integration, and decision support"
        candidate_context = "pipeline development, data modeling, and stakeholder-facing analytics datasets"
    verdict = (
        f"Recommendation: proceed if interviewers validate depth in the JD's highest-priority systems. "
        f"Interview probability estimate: {probability}. Recruiter confidence: {confidence}. "
        f"Strongest alignment: {strong}. This looks most defensible for a {classification.engineering_domain} role in "
        f"{domain_label}. Realistic concerns: {weak}. Candidate shows evidence of production data delivery, but interviewers "
        "should validate direct tool ownership, end-to-end operational responsibility, stakeholder judgment, and whether any "
        "domain-specific language is framed as target-role context rather than invented prior experience."
    )
    why = (
        f"I am interested in {company} because the role combines data engineering with {why_context}. "
        f"My experience with {candidate_context} aligns well with the opportunity to help cross-functional teams turn "
        "complex data into trusted reporting and practical insights."
    )
    return HiringNarrative(
        brutal_hiring_manager_verdict=verdict,
        why_interested_answer=why,
        confidence=0.7,
        evidence=(classification.evidence + resume_match.evidence)[:8],
    )


def generate_hiring_narrative(
    *,
    company_name: str | None,
    role_title: str | None,
    job_description: str,
    resume: str,
    classification: Classification,
    keywords: KeywordAnalysis,
    resume_match: ResumeMatch,
) -> HiringNarrative:
    fallback = _fallback_narrative(company_name, classification, keywords, resume_match)
    return llm_client.generate(
        schema=HiringNarrative,
        fallback=fallback,
        route="synthesis_agent",
        system_prompt=(
            "PROMPT_VERSION=v2. You are the final recruiter and hiring-manager synthesis agent for a truthful resume "
            "tailoring workflow. Produce realistic recruiter-style reasoning, not mechanically stitched summaries. "
            "Generate strongest alignment areas, realistic hiring risks, likely interview focus areas, seniority fit, "
            "domain fit, recruiter concerns, differentiators, overall hiring recommendation, interview probability "
            "estimate, and recruiter confidence level inside the verdict. Do not propagate weak keyword mismatches "
            "when semantic support exists. Do not invent candidate experience. Avoid machine-readable phrasing such as "
            "'ownership -> supported by led'; write like real recruiter notes. If classifier confidence is below 0.75, "
            "use neutral wording such as operational analytics role instead of forcing a domain label."
        ),
        user_prompt=(
            "Write a concise but recruiter-realistic hiring-manager verdict and a truthful why-interested answer. "
            "The verdict must include: strongest alignment areas, realistic hiring risks, likely interview focus areas, "
            "seniority fit, domain fit, recruiter concerns, differentiators, overall hiring recommendation, interview "
            "probability estimate, and recruiter confidence level. The why-interested answer should sound natural and "
            "professional, use proper company capitalization, reflect company/domain/business context, and avoid template phrasing.\n\n"
            f"COMPANY: {company_name or 'Unknown'}\n"
            f"ROLE TITLE: {role_title or 'Unknown'}\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"CLASSIFICATION:\n{classification.model_dump_json()}\n\n"
            f"KEYWORDS:\n{keywords.model_dump_json()}\n\n"
            f"MATCH REPORT:\n{resume_match.model_dump_json()}\n\n"
            f"RESUME:\n{resume}"
        ),
    )
