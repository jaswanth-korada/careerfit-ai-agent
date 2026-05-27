import logging
from pathlib import Path

from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.requests import Request

from agents.ats_keyword_agent import extract_keywords
from agents.interview_prep_agent import generate_interview_prep
from agents.jd_classifier import run_jd_classifier
from agents.resume_match_agent import score_resume
from agents.self_review_agent import (
    CROSS_MODEL_DISAGREEMENT_THRESHOLD,
    MAX_REFINEMENT_ROUNDS,
    cross_model_classification_review,
    final_confidence_from_critique,
    self_critique_analysis,
)
from agents.resume_tailor_agent import tailor_resume
from agents.synthesis_agent import generate_hiring_narrative
from agents.truthfulness_guardrail import run_guardrails
from schemas.analysis_schema import AlternativeClassification, AnalysisRequest, FullAnalysisResponse, ResumePdfExportRequest
from services.llm_client import llm_client
from services.pdf_export import LatexCompilerNotFoundError, compile_latex_or_fallback, safe_resume_filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("careerfit.api")

app = FastAPI(title="CareerFit AI Agent", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        f"[request] {request.method} {request.url.path} "
        f"origin={request.headers.get('origin', '-')}"
    )
    response = await call_next(request)
    logger.info(f"[response] {request.method} {request.url.path} status={response.status_code}")
    return response


@app.get("/")
def health_check():
    return {"status": "ok", "app": "CareerFit AI Agent"}


@app.post("/export-resume-pdf")
def export_resume_pdf(payload: ResumePdfExportRequest):
    filename = safe_resume_filename(payload.candidate_name, payload.company_name, payload.role_title)
    output_dir = Path(__file__).parent / "generated_resumes"
    try:
        pdf_path = compile_latex_or_fallback(
            payload.final_resume_latex,
            output_dir,
            filename,
            allow_plain_text_fallback=payload.allow_plain_text_fallback,
        )
    except LatexCompilerNotFoundError as exc:
        logger.error("[export-resume-pdf] pdflatex_missing filename=%s", filename)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[export-resume-pdf] failed filename=%s error=%s", filename, exc)
        raise HTTPException(
            status_code=500,
            detail="PDF generation failed. Download the LaTeX or Markdown version instead.",
        ) from exc

    logger.info(
        "[export-resume-pdf] generated filename=%s company=%s role=%s candidate=%s",
        filename,
        payload.company_name or "-",
        payload.role_title or "-",
        payload.candidate_name or "-",
    )
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
    )


def _log_analysis_snapshot(label: str, classification, keywords, resume_match, guardrails, tailored_resume, narrative):
    logger.info(
        "[self-review:%s] initial_output business=%s engineering=%s speed=%s keyword_counts=%s/%s/%s/%s "
        "scores=%s guardrails=%s tailored_confidence=%s narrative_confidence=%s",
        label,
        classification.business_domain,
        classification.engineering_domain,
        classification.speed_pattern,
        len(keywords.exact_match),
        len(keywords.semantic_match),
        len(keywords.inferred_match),
        len(keywords.missing_from_resume),
        resume_match.scores.model_dump(),
        {
            "unsupported_tools": len(guardrails.unsupported_tools),
            "scale": len(guardrails.unsupported_scale_claims),
            "domain": len(guardrails.unsupported_domain_claims),
            "architecture": len(guardrails.unsupported_architecture_claims),
        },
        tailored_resume.confidence,
        narrative.confidence,
    )


def _section_quality(critique, section: str) -> int:
    scores = critique.quality_scores
    return {
        "classification": scores.classification_quality,
        "semantic_match": scores.semantic_match_quality,
        "guardrails": scores.guardrail_quality,
        "tailoring": scores.tailoring_quality,
        "synthesis": scores.synthesis_quality,
    }.get(section, 0)


@app.post("/full-analysis", response_model=FullAnalysisResponse)
def full_analysis(payload: AnalysisRequest):
    logger.info(
        "[full-analysis] POST body parsed "
        f"jd_chars={len(payload.job_description)} "
        f"resume_chars={len(payload.resume)} "
        f"latex_template_chars={len(payload.original_latex_template or '')} "
        f"resume_template={payload.resume_template} "
        f"company={payload.company_name or '-'} "
        f"role={payload.role_title or '-'} "
        f"style={payload.target_style}"
    )
    classification = run_jd_classifier(payload.job_description)
    original_classification = classification
    alternative_classification = None
    logger.info(
        "[classification] business=%s engineering=%s confidence=%s rationale=%s",
        classification.business_domain,
        classification.engineering_domain,
        classification.confidence,
        classification.rationale[:2],
    )
    classification_refinement_rounds = 0
    if llm_client.enable_cross_model_critique:
        classification_review = cross_model_classification_review(
            job_description=payload.job_description,
            classification=classification,
        )
        logger.info(
            "[cross-model-classification] agreed=%s disagreement=%s threshold=%s corrected_business=%s corrected_engineering=%s corrected_speed=%s reasons=%s",
            classification_review.agreed,
            classification_review.disagreement_score,
            CROSS_MODEL_DISAGREEMENT_THRESHOLD,
            classification_review.corrected_business_domain,
            classification_review.corrected_engineering_domain,
            classification_review.corrected_speed_pattern,
            classification_review.reasons,
        )
        while (
            classification_review.disagreement_score > CROSS_MODEL_DISAGREEMENT_THRESHOLD
            and classification_refinement_rounds < MAX_REFINEMENT_ROUNDS
        ):
            classification_refinement_rounds += 1
            logger.warning(
                "[cross-model-classification] disagreement_above_threshold refinement_round=%s rerunning_classifier original_business=%s original_engineering=%s",
                classification_refinement_rounds,
                classification.business_domain,
                classification.engineering_domain,
            )
            classification = run_jd_classifier(payload.job_description)
            classification_review = cross_model_classification_review(
                job_description=payload.job_description,
                classification=classification,
            )
            logger.info(
                "[cross-model-classification] post_refinement agreed=%s disagreement=%s threshold=%s reasons=%s",
                classification_review.agreed,
                classification_review.disagreement_score,
                CROSS_MODEL_DISAGREEMENT_THRESHOLD,
                classification_review.reasons,
            )
        if classification_review.disagreement_score > CROSS_MODEL_DISAGREEMENT_THRESHOLD:
            alternative_classification = AlternativeClassification(
                business_domain=classification_review.corrected_business_domain,
                engineering_domain=classification_review.corrected_engineering_domain,
                speed_pattern=classification_review.corrected_speed_pattern,
                disagreement_score=classification_review.disagreement_score,
                reasons=classification_review.reasons,
                confidence=classification_review.confidence,
            )
            classification = original_classification
            logger.warning(
                "[cross-model-classification] unresolved_after_max_rounds preserving_original=true alternative=%s",
                alternative_classification.model_dump(),
            )
    keywords = extract_keywords(payload.job_description, payload.resume)
    logger.info(
        "[semantic-matches] exact=%s semantic=%s inferred=%s missing=%s",
        len(keywords.exact_match),
        len(keywords.semantic_match),
        len(keywords.inferred_match),
        len(keywords.missing_from_resume),
    )
    resume_match = score_resume(payload.job_description, payload.resume, keywords)
    logger.info(
        "[scoring] ats=%s technical=%s trust=%s risk=%s overall=%s",
        resume_match.scores.ats_score,
        resume_match.scores.technical_alignment,
        resume_match.scores.hiring_manager_trust,
        resume_match.scores.interview_risk,
        resume_match.scores.overall_match,
    )
    guardrails = run_guardrails(payload.job_description, keywords, payload.resume)
    logger.info(
        "[guardrails] unsupported_tools=%s scale=%s domain=%s architecture=%s risky=%s",
        len(guardrails.unsupported_tools),
        len(guardrails.unsupported_scale_claims),
        len(guardrails.unsupported_domain_claims),
        len(guardrails.unsupported_architecture_claims),
        len(guardrails.risky_insertions),
    )
    tailored_resume = tailor_resume(
        payload.resume,
        payload.job_description,
        classification,
        keywords,
        resume_match,
        guardrails,
        payload.target_style,
        payload.original_latex_template,
        payload.resume_template,
    )
    interview_prep = generate_interview_prep(
        payload.job_description,
        payload.resume,
        classification,
        keywords,
        resume_match,
    )
    narrative = generate_hiring_narrative(
        company_name=payload.company_name,
        role_title=payload.role_title,
        job_description=payload.job_description,
        resume=payload.resume,
        classification=classification,
        keywords=keywords,
        resume_match=resume_match,
    )

    _log_analysis_snapshot("round-0", classification, keywords, resume_match, guardrails, tailored_resume, narrative)
    critique = self_critique_analysis(
        job_description=payload.job_description,
        resume=payload.resume,
        classification=classification,
        keywords=keywords,
        resume_match=resume_match,
        guardrails=guardrails,
        tailored_resume=tailored_resume,
        interview_prep=interview_prep,
        narrative=narrative,
        refinement_round=classification_refinement_rounds,
    )
    logger.info(
        "[self-review:round-0] critique decision=%s scores=%s weak_sections=%s risks=%s",
        critique.decision,
        critique.quality_scores.model_dump(),
        critique.weak_sections,
        critique.remaining_risks,
    )

    refinement_rounds = classification_refinement_rounds
    while critique.quality_scores.overall_quality < 70 and refinement_rounds < MAX_REFINEMENT_ROUNDS:
        refinement_rounds += 1
        requested_sections = critique.weak_sections or ["classification", "semantic_match", "guardrails", "tailoring", "synthesis"]
        weak_sections = [
            section
            for section in requested_sections
            if _section_quality(critique, section) < 85 and not (section == "classification" and alternative_classification is not None)
        ]
        if not weak_sections:
            logger.info(
                "[self-review:round-%s] no_revisions all_requested_sections_passed=%s",
                refinement_rounds,
                requested_sections,
            )
            break
        logger.info("[self-review:round-%s] revised_sections=%s", refinement_rounds, weak_sections)

        if "classification" in weak_sections:
            classification = run_jd_classifier(payload.job_description)

        if "semantic_match" in weak_sections:
            keywords = extract_keywords(payload.job_description, payload.resume)
            resume_match = score_resume(payload.job_description, payload.resume, keywords)

        if "guardrails" in weak_sections:
            guardrails = run_guardrails(payload.job_description, keywords, payload.resume)

        if "tailoring" in weak_sections:
            tailored_resume = tailor_resume(
                payload.resume,
                payload.job_description,
                classification,
                keywords,
                resume_match,
                guardrails,
                payload.target_style,
                payload.original_latex_template,
                payload.resume_template,
            )

        if "synthesis" in weak_sections:
            narrative = generate_hiring_narrative(
                company_name=payload.company_name,
                role_title=payload.role_title,
                job_description=payload.job_description,
                resume=payload.resume,
                classification=classification,
                keywords=keywords,
                resume_match=resume_match,
            )

        _log_analysis_snapshot(
            f"round-{refinement_rounds}",
            classification,
            keywords,
            resume_match,
            guardrails,
            tailored_resume,
            narrative,
        )
        critique = self_critique_analysis(
            job_description=payload.job_description,
            resume=payload.resume,
            classification=classification,
            keywords=keywords,
            resume_match=resume_match,
            guardrails=guardrails,
            tailored_resume=tailored_resume,
            interview_prep=interview_prep,
            narrative=narrative,
            refinement_round=refinement_rounds,
        )
        logger.info(
            "[self-review:round-%s] critique decision=%s scores=%s weak_sections=%s risks=%s",
            refinement_rounds,
            critique.decision,
            critique.quality_scores.model_dump(),
            critique.weak_sections,
            critique.remaining_risks,
        )

    remaining_risks = list(dict.fromkeys(critique.remaining_risks))
    if refinement_rounds >= MAX_REFINEMENT_ROUNDS and (
        critique.quality_scores.overall_quality < 70 or classification.confidence < 0.75
    ):
        remaining_risks.append("Classification remains uncertain. Recommended human review.")
    if alternative_classification is not None:
        remaining_risks.append("Cross-model classification disagreement remained high; original classification was preserved and Claude's alternative is shown for human review.")

    final_answer_confidence = final_confidence_from_critique(critique, classification)
    quality_checks_passed = critique.quality_scores.overall_quality >= 85
    logger.info(
        "[self-review:final] final_quality=%s final_confidence=%s rounds=%s passed=%s risks=%s",
        critique.quality_scores.model_dump(),
        final_answer_confidence,
        refinement_rounds,
        quality_checks_passed,
        remaining_risks,
    )

    return FullAnalysisResponse(
        classification=classification,
        alternative_classification=alternative_classification,
        keywords=keywords,
        resume_match=resume_match,
        guardrails=guardrails,
        tailored_resume=tailored_resume,
        interview_prep=interview_prep,
        brutal_hiring_manager_verdict=narrative.brutal_hiring_manager_verdict,
        why_interested_answer=narrative.why_interested_answer,
        quality_scores=critique.quality_scores,
        final_answer_confidence=final_answer_confidence,
        refinement_rounds=refinement_rounds,
        quality_checks_passed=quality_checks_passed,
        remaining_risks=remaining_risks,
        acceptance_explanation=critique.acceptance_explanation,
    )
