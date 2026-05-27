from schemas.analysis_schema import ResumeMatch, ScoreCard, KeywordAnalysis
from services.llm_client import llm_client
from services.semantic_matching import classify_support_records


def _fallback_score_resume(resume: str, keywords: KeywordAnalysis) -> ResumeMatch:
    all_keywords = keywords.must_have + keywords.important + keywords.bonus
    records = classify_support_records(all_keywords, resume)
    exact = [r for r in records if r["support_type"] == "exact_match" and float(r["confidence"]) >= 0.9]
    semantic = [r for r in records if r["support_type"] == "semantic_match" and float(r["confidence"]) >= 0.7]
    inferred = [r for r in records if r["support_type"] == "inferred_match" and float(r["confidence"]) >= 0.5]
    missing_records = [r for r in records if r["support_type"] == "missing" or float(r["confidence"]) < 0.5]
    matched = exact + semantic + inferred
    missing = [str(r["jd_concept"]) for r in missing_records]
    exact_weight = len(exact)
    semantic_weight = len(semantic) * 0.8
    inferred_weight = len(inferred) * 0.5
    ratio = (exact_weight + semantic_weight + inferred_weight) / max(len(all_keywords), 1)

    semantic_bonus = min(len(semantic) * 2, 8)
    tool_depth = len([r for r in matched if str(r["jd_concept"]).lower() in {"sql", "python", "azure", "aws", "data warehouse", "data pipelines", "api-based data integration", "bi / visualization"}])
    ats = int(52 + ratio * 38 + semantic_bonus)
    technical = int(50 + min(ratio, 0.9) * 34 + min(tool_depth * 3, 12))
    trust = 82 if any(metric in resume for metric in ["%", "GB", "TB", "daily", "month"]) else 70
    trust += 4 if exact or semantic else 0
    readability = 78 if len(resume.split()) < 900 else 70
    risk = max(18, 78 - int(ratio * 40) + min(len(missing) * 3, 18))
    overall = int((ats + technical + trust + readability + (100 - risk)) / 5)

    strong = [
        f"{r['jd_concept']} -> {r['support_type']} ({r['confidence']}): {r['resume_evidence']}"
        for r in exact + semantic
    ][:10]
    moderate = [
        f"{r['jd_concept']} -> inferred_match ({r['confidence']}): {r['resume_evidence']}"
        for r in inferred
    ][:8]
    weak = [
        f"{r['jd_concept']} -> weak or unsupported below 0.50 confidence"
        for r in missing_records[:8]
    ]
    gaps = [f"Truly missing or weakly supported JD concept: {m}" for m in missing[:8]]
    unsupported = []
    if "GCP" in missing:
        unsupported.append("Do not claim GCP production experience unless it is true; position AWS/Azure as multi-cloud exposure instead.")
    if "data flow diagrams" in missing:
        unsupported.append("Add architecture documentation only if you actually created diagrams or design docs.")

    return ResumeMatch(
        scores=ScoreCard(
            ats_score=min(ats, 93),
            recruiter_readability=readability,
            hiring_manager_trust=min(trust, 90),
            technical_alignment=min(technical, 92),
            interview_risk=min(risk, 95),
            overall_match=min(overall, 91),
        ),
        strong_matches=strong,
        moderate_matches=moderate,
        weak_matches=weak,
        missing=missing,
        support_levels={
            "strongly_supported": [str(r["jd_concept"]) for r in exact],
            "partially_supported": [str(r["jd_concept"]) for r in semantic],
            "inferred_support": [str(r["jd_concept"]) for r in inferred],
            "truly_missing": missing,
        },
        gaps=gaps,
        unsupported_claim_risks=unsupported,
        confidence=0.7,
        evidence=[
            f"Semantic support scoring: exact={len(exact)}, semantic={len(semantic)}, inferred={len(inferred)}, missing={len(missing)}"
        ] + [
            f"{r['jd_concept']}: {r['support_type']} confidence={r['confidence']} evidence={r['resume_evidence']}"
            for r in matched[:8]
        ],
    )


def score_resume(job_description: str, resume: str, keywords: KeywordAnalysis) -> ResumeMatch:
    fallback = _fallback_score_resume(resume, keywords)
    return llm_client.generate(
        schema=ResumeMatch,
        fallback=fallback,
        route="resume_match_agent",
        system_prompt=(
            "PROMPT_VERSION=v2. You are the Resume Match and Scoring Agent. Score resume-to-JD fit with semantic "
            "support, not raw token overlap. Consider exact support, semantic equivalence, inferred support, architecture "
            "relevance, business-domain alignment, and realism/trustworthiness. Do not mark semantically supported "
            "concepts as weak keyword mismatches, and never reward unsupported claims. A concept must appear in only one "
            "category: strong_matches, moderate_matches, weak_matches, or missing. Use thresholds: exact_match >= 0.90, "
            "semantic_match >= 0.70, inferred_match >= 0.50, below 0.50 is weak or missing."
        ),
        user_prompt=(
            "Compare the resume against the JD and keyword analysis. Return calibrated 0-100 scores, "
            "strong matches, moderate matches, weak matches, missing concepts, support_levels, gaps, unsupported claim risks, "
            "confidence, and evidence from the resume/JD. ATS score = keyword plus semantic coverage. Technical alignment = "
            "depth of matched tools and architecture. Hiring manager trust = specificity, metrics, and defensibility. "
            "Recruiter readability = clarity and role alignment. Interview risk = missing tools, unsupported scale, and domain gaps.\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"KEYWORD ANALYSIS:\n{keywords.model_dump_json()}\n\n"
            f"RESUME:\n{resume}"
        ),
    )
