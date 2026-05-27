from schemas.analysis_schema import (
    Classification,
    ClassificationCrossReview,
    GuardrailReport,
    HiringNarrative,
    InterviewPrep,
    KeywordAnalysis,
    QualityScores,
    ResumeMatch,
    SelfCritiqueReport,
    TailoredResume,
)
from services.llm_client import llm_client
from services.semantic_matching import STOPWORDS

MAX_REFINEMENT_ROUNDS = 3
ACCEPT_THRESHOLD = 85
CAUTION_THRESHOLD = 70
CROSS_MODEL_DISAGREEMENT_THRESHOLD = 45


def _score_from_checks(base: int, penalties: list[int], floor: int = 35) -> int:
    return max(floor, min(100, base - sum(penalties)))


def _has_bad_evidence(evidence: list[str]) -> bool:
    for item in evidence:
        cleaned = item.strip().lower()
        if cleaned in STOPWORDS:
            return True
        if "supported by in" in cleaned or "supported by on" in cleaned:
            return True
    return False


def _has_phrase_reasons(evidence: list[str]) -> bool:
    return bool(evidence) and all((" - " in item or ":" in item) and len(item.split()) >= 4 for item in evidence[:5])


def _overlap(left: list[str], right: list[str]) -> set[str]:
    left_keys = {item.split(" -> ")[0].strip().lower() for item in left}
    right_keys = {item.split(" -> ")[0].strip().lower() for item in right}
    return left_keys & right_keys


def _quality_status(overall: int) -> str:
    if overall >= ACCEPT_THRESHOLD:
        return "accept"
    if overall >= CAUTION_THRESHOLD:
        return "accept_with_caution"
    return "revise"


def _confidence_label(overall: int, classification_confidence: float) -> str:
    if overall >= ACCEPT_THRESHOLD and classification_confidence >= 0.75:
        return "high"
    if overall >= CAUTION_THRESHOLD and classification_confidence >= 0.6:
        return "medium"
    return "low"


def _fallback_self_critique(
    *,
    classification: Classification,
    keywords: KeywordAnalysis,
    resume_match: ResumeMatch,
    guardrails: GuardrailReport,
    tailored_resume: TailoredResume,
    interview_prep: InterviewPrep,
    narrative: HiringNarrative,
    refinement_round: int,
) -> SelfCritiqueReport:
    classification_penalties = []
    if classification.business_domain.lower() in {"general / unknown", "unknown"}:
        classification_penalties.append(35)
    if classification.confidence < 0.75:
        classification_penalties.append(18)
    if not _has_phrase_reasons(classification.evidence):
        classification_penalties.append(14)
    if "saas" in classification.business_domain.lower() and any(
        term.lower() in " ".join(keywords.domain_terms).lower()
        for term in ["project lifecycle", "cost forecasting", "operational kpis", "bim", "payments", "patients", "campaigns"]
    ):
        classification_penalties.append(20)
    classification_quality = _score_from_checks(96, classification_penalties)

    semantic_penalties = []
    if _has_bad_evidence(keywords.evidence):
        semantic_penalties.append(25)
    if _overlap(resume_match.strong_matches, resume_match.weak_matches):
        semantic_penalties.append(30)
    if len(keywords.semantic_match) == 0 and len(keywords.missing_from_resume) > len(keywords.exact_match) + 4:
        semantic_penalties.append(15)
    if not resume_match.support_levels:
        semantic_penalties.append(12)
    semantic_match_quality = _score_from_checks(94, semantic_penalties)

    guardrail_penalties = []
    risky_tool_terms = ["procore", "buildops", "spectrum", "dayforce", "mulesoft", "ssis", "dbt", "atlan", "golang"]
    requested_text = " ".join(keywords.tools + keywords.bonus + keywords.domain_terms).lower()
    if any(term in requested_text for term in risky_tool_terms) and not guardrails.unsupported_tools:
        guardrail_penalties.append(28)
    if not guardrails.safe_reframes and (guardrails.unsupported_tools or guardrails.unsupported_domain_claims):
        guardrail_penalties.append(18)
    if guardrails.confidence < 0.7:
        guardrail_penalties.append(10)
    guardrail_quality = _score_from_checks(94, guardrail_penalties)

    tailoring_penalties = []
    tailored_text = " ".join([tailored_resume.revised_summary] + tailored_resume.rewritten_bullets).lower()
    generic_phrases = ["scalable solutions", "business needs", "cloud-based systems"]
    if any(phrase in tailored_text for phrase in generic_phrases):
        tailoring_penalties.append(20)
    if classification.confidence >= 0.75:
        domain = classification.business_domain.lower()
        domain_terms = {
            "construction": ["operational", "project", "cost", "erp", "kpi"],
            "fintech": ["trust", "financial", "privacy", "reliability"],
            "consulting": ["client", "governance", "architecture", "stakeholder"],
            "ad-tech": ["campaign", "measurement", "attribution", "analytics"],
            "saas": ["api", "integration", "warehouse", "reporting"],
        }
        for marker, terms in domain_terms.items():
            if marker in domain and not any(term in tailored_text for term in terms):
                tailoring_penalties.append(18)
    if tailored_resume.confidence < 0.65:
        tailoring_penalties.append(10)
    tailoring_quality = _score_from_checks(92, tailoring_penalties)

    synthesis_penalties = []
    narrative_text = f"{narrative.brutal_hiring_manager_verdict} {narrative.why_interested_answer}".lower()
    if "-> supported by" in narrative_text:
        synthesis_penalties.append(22)
    if "this company" in narrative.why_interested_answer.lower():
        synthesis_penalties.append(12)
    if classification.confidence < 0.75 and classification.business_domain.lower() in narrative_text:
        synthesis_penalties.append(10)
    if len(narrative.why_interested_answer.split()) < 30:
        synthesis_penalties.append(12)
    synthesis_quality = _score_from_checks(92, synthesis_penalties)

    scores = QualityScores(
        classification_quality=classification_quality,
        semantic_match_quality=semantic_match_quality,
        guardrail_quality=guardrail_quality,
        tailoring_quality=tailoring_quality,
        synthesis_quality=synthesis_quality,
        overall_quality=round(
            (
                classification_quality
                + semantic_match_quality
                + guardrail_quality
                + tailoring_quality
                + synthesis_quality
            )
            / 5
        ),
    )

    weak_sections = []
    if scores.classification_quality < ACCEPT_THRESHOLD:
        weak_sections.append("classification")
    if scores.semantic_match_quality < ACCEPT_THRESHOLD:
        weak_sections.append("semantic_match")
    if scores.guardrail_quality < ACCEPT_THRESHOLD:
        weak_sections.append("guardrails")
    if scores.tailoring_quality < ACCEPT_THRESHOLD:
        weak_sections.append("tailoring")
    if scores.synthesis_quality < ACCEPT_THRESHOLD:
        weak_sections.append("synthesis")

    remaining_risks = []
    if classification.confidence < 0.75:
        remaining_risks.append("Classification remains uncertain. Recommended human review.")
    if scores.semantic_match_quality < ACCEPT_THRESHOLD:
        remaining_risks.append("Some semantic matches or missing-skill calls may need human validation.")
    if scores.guardrail_quality < ACCEPT_THRESHOLD:
        remaining_risks.append("Unsupported tools, scale, domain, or ownership claims may need stricter review.")
    if scores.tailoring_quality < ACCEPT_THRESHOLD:
        remaining_risks.append("Tailored resume language may still be too generic or not domain-specific enough.")
    if scores.synthesis_quality < ACCEPT_THRESHOLD:
        remaining_risks.append("Recruiter verdict or why-interested answer may need more human polish.")

    decision = _quality_status(scores.overall_quality)
    if refinement_round >= MAX_REFINEMENT_ROUNDS and scores.overall_quality < CAUTION_THRESHOLD:
        decision = "accept_with_uncertainty"

    accepted_sections = [
        name.replace("_", " ")
        for name, value in {
            "business domain": scores.classification_quality,
            "semantic matches": scores.semantic_match_quality,
            "guardrails": scores.guardrail_quality,
            "tailoring": scores.tailoring_quality,
            "synthesis": scores.synthesis_quality,
        }.items()
        if value >= ACCEPT_THRESHOLD
    ]
    if decision == "revise":
        explanation = f"Revision required because {', '.join(weak_sections)} did not meet quality threshold."
    else:
        explanation = (
            f"Accepted after {refinement_round} refinement rounds because "
            f"{', '.join(accepted_sections) or 'the strongest available sections'} passed threshold."
        )
        if decision == "accept_with_caution":
            explanation += " Some sections remain below the preferred 85 threshold, so use with caution."
        if decision == "accept_with_uncertainty":
            explanation += " Classification remains uncertain. Recommended human review."

    return SelfCritiqueReport(
        quality_scores=scores,
        decision=decision,
        weak_sections=weak_sections,
        remaining_risks=remaining_risks,
        acceptance_explanation=explanation,
        confidence=0.82 if scores.overall_quality >= ACCEPT_THRESHOLD else 0.68 if scores.overall_quality >= CAUTION_THRESHOLD else 0.52,
        evidence=[
            f"classification={scores.classification_quality}",
            f"semantic_match={scores.semantic_match_quality}",
            f"guardrails={scores.guardrail_quality}",
            f"tailoring={scores.tailoring_quality}",
            f"synthesis={scores.synthesis_quality}",
            f"overall={scores.overall_quality}",
        ],
    )


def self_critique_analysis(
    *,
    job_description: str,
    resume: str,
    classification: Classification,
    keywords: KeywordAnalysis,
    resume_match: ResumeMatch,
    guardrails: GuardrailReport,
    tailored_resume: TailoredResume,
    interview_prep: InterviewPrep,
    narrative: HiringNarrative,
    refinement_round: int,
) -> SelfCritiqueReport:
    fallback = _fallback_self_critique(
        classification=classification,
        keywords=keywords,
        resume_match=resume_match,
        guardrails=guardrails,
        tailored_resume=tailored_resume,
        interview_prep=interview_prep,
        narrative=narrative,
        refinement_round=refinement_round,
    )
    return llm_client.generate(
        schema=SelfCritiqueReport,
        fallback=fallback,
        route="self_critique_agent",
        system_prompt=(
            "PROMPT_VERSION=v3. You are the Agentic Self-Review Agent for a recruiter-grade resume analysis system. "
            "Critique the completed analysis before it is returned. Prefer honest uncertainty over inflated confidence. "
            "Evaluate business domain accuracy, engineering domain accuracy, evidence quality, semantic match quality, "
            "false missing skills, truthfulness risks, tailored resume specificity, recruiter realism, and why-interested quality. "
            "Do not chase fake 100% confidence."
        ),
        user_prompt=(
            "Review the full analysis and return quality scores from 0-100 for classification_quality, "
            "semantic_match_quality, guardrail_quality, tailoring_quality, synthesis_quality, and overall_quality. "
            "Decision rules: overall_quality >= 85 means accept; 70-84 means accept_with_caution; below 70 means revise. "
            "List weak_sections using these exact labels when relevant: classification, semantic_match, guardrails, "
            "tailoring, synthesis. Include remaining_risks and a concise acceptance_explanation.\n\n"
            f"REFINEMENT ROUND: {refinement_round}\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"RESUME:\n{resume}\n\n"
            f"CLASSIFICATION:\n{classification.model_dump_json()}\n\n"
            f"KEYWORDS:\n{keywords.model_dump_json()}\n\n"
            f"RESUME MATCH:\n{resume_match.model_dump_json()}\n\n"
            f"GUARDRAILS:\n{guardrails.model_dump_json()}\n\n"
            f"TAILORED RESUME:\n{tailored_resume.model_dump_json()}\n\n"
            f"INTERVIEW PREP:\n{interview_prep.model_dump_json()}\n\n"
            f"SYNTHESIS:\n{narrative.model_dump_json()}"
        ),
    )


def final_confidence_from_critique(critique: SelfCritiqueReport, classification: Classification) -> str:
    return _confidence_label(critique.quality_scores.overall_quality, classification.confidence)


def _fallback_classification_cross_review(classification: Classification) -> ClassificationCrossReview:
    penalties = []
    reasons = []
    if classification.confidence < 0.75:
        penalties.append(30)
        reasons.append("Classifier confidence is below the preferred domain-certainty threshold.")
    if classification.business_domain.lower() in {"general / unknown", "unknown"}:
        penalties.append(35)
        reasons.append("Business domain is unresolved.")
    if not _has_phrase_reasons(classification.evidence):
        penalties.append(15)
        reasons.append("Classification evidence is thin or lacks phrase-level reasoning.")
    disagreement = min(100, sum(penalties))
    return ClassificationCrossReview(
        agreed=disagreement < CROSS_MODEL_DISAGREEMENT_THRESHOLD,
        disagreement_score=disagreement,
        corrected_business_domain=None,
        corrected_engineering_domain=None,
        corrected_speed_pattern=None,
        reasons=reasons or ["No material disagreement detected by deterministic cross-review fallback."],
        confidence=0.65 if disagreement else 0.8,
    )


def cross_model_classification_review(
    *,
    job_description: str,
    classification: Classification,
) -> ClassificationCrossReview:
    fallback = _fallback_classification_cross_review(classification)
    return llm_client.generate(
        schema=ClassificationCrossReview,
        fallback=fallback,
        route="self_critique_agent",
        system_prompt=(
            "PROMPT_VERSION=v3. You are Claude reviewing an OpenAI-generated JD classification. "
            "Use recruiter/domain reasoning to challenge incorrect industry labels, weak engineering-domain calls, "
            "and bad speed-pattern assumptions. Prefer uncertainty over forced disagreement."
        ),
        user_prompt=(
            "Review this classification against the JD. Return whether you agree, a disagreement_score from 0-100, "
            "optional corrected business_domain/engineering_domain/speed_pattern, reasons, and confidence. "
            "If disagreement_score is above the threshold, provide corrected_business_domain, corrected_engineering_domain, "
            "and corrected_speed_pattern when the JD supports a better label. "
            f"Flag disagreement above {CROSS_MODEL_DISAGREEMENT_THRESHOLD} only when the current classification is likely wrong.\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"OPENAI CLASSIFICATION:\n{classification.model_dump_json()}"
        ),
    )
