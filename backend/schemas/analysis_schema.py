from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


def bounded_confidence(value: float) -> float:
    return round(max(0.0, min(float(value), 1.0)), 2)


def bounded_score(value: int) -> int:
    return max(0, min(int(value), 100))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisRequest(StrictModel):
    job_description: str = Field(..., min_length=50)
    resume: str = Field(..., min_length=50)
    original_latex_template: Optional[str] = None
    resume_template: str = "classic"
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    target_style: str = "General"


class ResumePdfExportRequest(StrictModel):
    final_resume_latex: str = Field(..., min_length=50)
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    candidate_name: Optional[str] = None
    allow_plain_text_fallback: bool = False


class Classification(StrictModel):
    business_domain: str
    engineering_domain: str
    speed_pattern: str
    company_maturity: str
    confidence: float
    evidence: List[str] = Field(default_factory=list)
    alternative_domains: List[str] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class KeywordAnalysis(StrictModel):
    must_have: List[str] = Field(default_factory=list)
    important: List[str] = Field(default_factory=list)
    bonus: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    domain_terms: List[str] = Field(default_factory=list)
    missing_from_resume: List[str] = Field(default_factory=list)
    tool_stack: Dict[str, List[str]] = Field(default_factory=dict)
    soft_skill_signals: List[str] = Field(default_factory=list)
    exact_match: List[str] = Field(default_factory=list)
    semantic_match: List[str] = Field(default_factory=list)
    inferred_match: List[str] = Field(default_factory=list)
    confidence_levels: Dict[str, List[str]] = Field(default_factory=dict)
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class ScoreCard(StrictModel):
    ats_score: int
    recruiter_readability: int
    hiring_manager_trust: int
    technical_alignment: int
    interview_risk: int
    overall_match: int

    @field_validator(
        "ats_score",
        "recruiter_readability",
        "hiring_manager_trust",
        "technical_alignment",
        "interview_risk",
        "overall_match",
    )
    @classmethod
    def validate_score(cls, value: int) -> int:
        return bounded_score(value)


class ResumeMatch(StrictModel):
    scores: ScoreCard
    strong_matches: List[str] = Field(default_factory=list)
    moderate_matches: List[str] = Field(default_factory=list)
    weak_matches: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    support_levels: Dict[str, List[str]] = Field(default_factory=dict)
    gaps: List[str] = Field(default_factory=list)
    unsupported_claim_risks: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class TailoredResume(StrictModel):
    revised_summary: str
    revised_skills: List[str] = Field(default_factory=list)
    rewritten_bullets: List[str] = Field(default_factory=list)
    final_resume_markdown: str
    final_resume_latex: str = ""
    template_warning: str = ""
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class GuardrailReport(StrictModel):
    do_not_claim: List[str] = Field(default_factory=list)
    unsupported_tools: List[str] = Field(default_factory=list)
    unsupported_scale_claims: List[str] = Field(default_factory=list)
    unsupported_domain_claims: List[str] = Field(default_factory=list)
    unsupported_architecture_claims: List[str] = Field(default_factory=list)
    safe_reframes: List[str] = Field(default_factory=list)
    risky_insertions: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class InterviewPrep(StrictModel):
    sql_questions: List[str] = Field(default_factory=list)
    data_modeling_questions: List[str] = Field(default_factory=list)
    data_platform_questions: List[str] = Field(default_factory=list)
    data_engineering_questions: List[str] = Field(default_factory=list)
    cloud_questions: List[str] = Field(default_factory=list)
    data_quality_questions: List[str] = Field(default_factory=list)
    domain_business_questions: List[str] = Field(default_factory=list)
    behavioral_questions: List[str] = Field(default_factory=list)
    resume_defense_questions: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class HiringNarrative(StrictModel):
    brutal_hiring_manager_verdict: str
    why_interested_answer: str
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class QualityScores(StrictModel):
    classification_quality: int
    semantic_match_quality: int
    guardrail_quality: int
    tailoring_quality: int
    synthesis_quality: int
    overall_quality: int

    @field_validator(
        "classification_quality",
        "semantic_match_quality",
        "guardrail_quality",
        "tailoring_quality",
        "synthesis_quality",
        "overall_quality",
    )
    @classmethod
    def validate_quality(cls, value: int) -> int:
        return bounded_score(value)


class SelfCritiqueReport(StrictModel):
    quality_scores: QualityScores
    decision: str
    weak_sections: List[str] = Field(default_factory=list)
    remaining_risks: List[str] = Field(default_factory=list)
    acceptance_explanation: str
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class ClassificationCrossReview(StrictModel):
    agreed: bool
    disagreement_score: int
    corrected_business_domain: Optional[str] = None
    corrected_engineering_domain: Optional[str] = None
    corrected_speed_pattern: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    confidence: float = 0.0

    @field_validator("disagreement_score")
    @classmethod
    def validate_disagreement_score(cls, value: int) -> int:
        return bounded_score(value)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class AlternativeClassification(StrictModel):
    business_domain: Optional[str] = None
    engineering_domain: Optional[str] = None
    speed_pattern: Optional[str] = None
    disagreement_score: int
    reasons: List[str] = Field(default_factory=list)
    confidence: float = 0.0

    @field_validator("disagreement_score")
    @classmethod
    def validate_disagreement_score(cls, value: int) -> int:
        return bounded_score(value)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return bounded_confidence(value)


class FullAnalysisResponse(StrictModel):
    classification: Classification
    alternative_classification: Optional[AlternativeClassification] = None
    keywords: KeywordAnalysis
    resume_match: ResumeMatch
    guardrails: GuardrailReport
    tailored_resume: TailoredResume
    interview_prep: InterviewPrep
    brutal_hiring_manager_verdict: str
    why_interested_answer: str
    quality_scores: QualityScores
    final_answer_confidence: str
    refinement_rounds: int
    quality_checks_passed: bool
    remaining_risks: List[str] = Field(default_factory=list)
    acceptance_explanation: str
