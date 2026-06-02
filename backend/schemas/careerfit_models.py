from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class ResumeEvidence(BaseModel):
    skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    experience_bullets: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    architectures: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class JDDecomposition(BaseModel):
    role_identity: str
    platform_dominance: str
    orchestration_style: str
    tier1_signals: List[str] = Field(default_factory=list)
    tier2_signals: List[str] = Field(default_factory=list)
    tier3_minimize: List[str] = Field(default_factory=list)
    hidden_expectations: List[str] = Field(default_factory=list)


class IdentityBoundary(BaseModel):
    green_identities: List[str] = Field(default_factory=list)
    yellow_identities: List[str] = Field(default_factory=list)
    red_identities: List[str] = Field(default_factory=list)
    recommended_mode: str = "Balanced"
    risk_notes: List[str] = Field(default_factory=list)


class PromiseProofResult(BaseModel):
    proven_skills: List[str] = Field(default_factory=list)
    weak_skills: List[str] = Field(default_factory=list)
    unsupported_skills: List[str] = Field(default_factory=list)
    removed_skills: List[str] = Field(default_factory=list)
    proof_map: Dict[str, List[str]] = Field(default_factory=dict)


class RetrievedEvidence(BaseModel):
    retrieved_bullets: List[str] = Field(default_factory=list)
    retrieved_projects: List[str] = Field(default_factory=list)
    retrieved_metrics: List[str] = Field(default_factory=list)
    retrieved_skills: List[str] = Field(default_factory=list)


class TrustScore(BaseModel):
    ats_alignment: str
    recruiter_trust: str
    operational_credibility: str
    interview_defensibility: str
    identity_coherence: str
    notes: List[str] = Field(default_factory=list)


class PreAssessmentResult(BaseModel):
    fit_level: str
    technical_match: str
    experience_match: str
    structural_gates: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendation: str


class CareerFitPipelineResult(BaseModel):
    pre_assessment: Optional[PreAssessmentResult] = None
    resume_evidence: Optional[ResumeEvidence] = None
    jd_decomposition: Optional[JDDecomposition] = None
    identity_boundary: Optional[IdentityBoundary] = None
    promise_proof: Optional[PromiseProofResult] = None
    retrieved_evidence: Optional[RetrievedEvidence] = None
    trust_score: Optional[TrustScore] = None
    final_latex_resume: Optional[str] = None
    interview_risk_report: List[str] = Field(default_factory=list)
