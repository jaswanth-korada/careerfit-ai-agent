export interface AnalysisRequest {
  job_description: string;
  resume: string;
  original_latex_template?: string;
  resume_template?: string;
  company_name?: string;
  role_title?: string;
  target_style: string;
}

export interface Classification {
  business_domain?: string;
  engineering_domain?: string;
  speed_pattern?: string;
  company_maturity?: string;
  confidence?: number;
  evidence?: string[];
  alternative_domains?: string[];
  rationale?: string[];
}

export interface AlternativeClassification {
  business_domain?: string;
  engineering_domain?: string;
  speed_pattern?: string;
  disagreement_score?: number;
  reasons?: string[];
  confidence?: number;
}

export interface KeywordAnalysis {
  must_have?: string[];
  important?: string[];
  bonus?: string[];
  tools?: string[];
  domain_terms?: string[];
  missing_from_resume?: string[];
  tool_stack?: Record<string, string[]>;
  soft_skill_signals?: string[];
  exact_match?: string[];
  semantic_match?: string[];
  inferred_match?: string[];
  confidence_levels?: Record<string, string[]>;
  confidence?: number;
  evidence?: string[];
}

export interface ScoreCard {
  ats_score?: number;
  recruiter_readability?: number;
  hiring_manager_trust?: number;
  technical_alignment?: number;
  interview_risk?: number;
  overall_match?: number;
}

export interface ResumeMatch {
  scores?: ScoreCard;
  strong_matches?: string[];
  moderate_matches?: string[];
  weak_matches?: string[];
  missing?: string[];
  support_levels?: Record<string, string[]>;
  gaps?: string[];
  unsupported_claim_risks?: string[];
  confidence?: number;
  evidence?: string[];
}

export interface GuardrailReport {
  do_not_claim?: string[];
  unsupported_tools?: string[];
  unsupported_scale_claims?: string[];
  unsupported_domain_claims?: string[];
  unsupported_architecture_claims?: string[];
  safe_reframes?: string[];
  risky_insertions?: string[];
  confidence?: number;
  evidence?: string[];
}

export interface TailoredResume {
  revised_summary?: string;
  revised_skills?: string[];
  rewritten_bullets?: string[];
  final_resume_markdown?: string;
  final_resume_latex?: string;
  template_warning?: string;
  confidence?: number;
  evidence?: string[];
}

export interface InterviewPrep {
  sql_questions?: string[];
  data_modeling_questions?: string[];
  data_platform_questions?: string[];
  data_engineering_questions?: string[];
  cloud_questions?: string[];
  data_quality_questions?: string[];
  domain_business_questions?: string[];
  behavioral_questions?: string[];
  resume_defense_questions?: string[];
  confidence?: number;
  evidence?: string[];
}

export interface QualityScores {
  classification_quality?: number;
  semantic_match_quality?: number;
  guardrail_quality?: number;
  tailoring_quality?: number;
  synthesis_quality?: number;
  overall_quality?: number;
}

export interface FullAnalysisResponse {
  classification?: Classification;
  alternative_classification?: AlternativeClassification | null;
  keywords?: KeywordAnalysis;
  resume_match?: ResumeMatch;
  guardrails?: GuardrailReport;
  tailored_resume?: TailoredResume;
  interview_prep?: InterviewPrep;
  brutal_hiring_manager_verdict?: string;
  why_interested_answer?: string;
  quality_scores?: QualityScores;
  final_answer_confidence?: 'high' | 'medium' | 'low';
  refinement_rounds?: number;
  quality_checks_passed?: boolean;
  remaining_risks?: string[];
  acceptance_explanation?: string;
}

export interface SavedAnalysis {
  id: string;
  createdAt: string;
  companyName?: string;
  roleTitle?: string;
  targetStyle: string;
  jd: string;
  resume: string;
  originalLatexTemplate?: string;
  resumeTemplate?: string;
  analysis: FullAnalysisResponse;
}
