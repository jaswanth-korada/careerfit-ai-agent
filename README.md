CareerFit AI Agent
CareerFit AI Agent is a production-minded, multi-agent resume intelligence system that analyzes job descriptions, scores resume fit, identifies unsupported claims, and generates tailored resume outputs with recruiter-aware reasoning.

The project is designed for data engineering and analytics roles where a strong resume must do more than repeat keywords. CareerFit combines structured LLM calls, deterministic fallbacks, Pydantic validation, semantic matching, self-review, cross-model critique, and PDF/LaTeX export into one end-to-end workflow.

Project Overview
CareerFit AI Agent helps candidates understand how well their resume aligns with a target role and produces a truthfulness-preserving tailored resume. Users paste a job description, master resume, optional LaTeX resume template, company name, role title, and target style. The backend orchestrates specialized agents that classify the role, extract ATS and hiring-manager signals, score resume alignment, detect risky claims, tailor the resume, generate interview preparation, and review the final output before returning it to the React dashboard.

The system prioritizes:

Explainable resume-job fit analysis
Recruiter and hiring-manager realism
ATS keyword coverage with semantic support levels
Honest tailoring that avoids hallucinated tools, credentials, metrics, or domain experience
Structured JSON responses suitable for frontend rendering and future persistence
Final resume export as Markdown, LaTeX, and PDF
Key Features
Multi-agent backend orchestration through FastAPI
Job description classification by business domain, engineering domain, speed pattern, and company maturity
ATS keyword extraction with exact, semantic, inferred, and missing support levels
Resume match scoring across ATS alignment, technical alignment, recruiter readability, hiring-manager trust, interview risk, and overall fit
Truthfulness guardrails for unsupported tools, scale claims, domain claims, and architecture ownership
Resume tailoring that preserves strong original bullets and inserts only defensible improvements
Self-review loop with quality scores, weak-section detection, and bounded refinement rounds
Cross-model critique for classification disagreements
Interview preparation questions tailored to the role and resume risks
Hiring narrative generation, including recruiter-style verdict and "why interested" answer
LaTeX template preservation with built-in resume templates
PDF export through local pdflatex, with controlled fallback behavior
Deterministic local fallbacks when LLM providers are unavailable or invalid responses fail schema validation
Multi-Agent Architecture
CareerFit is organized as a graph of narrow, schema-driven agents. Each agent owns a specific part of the career analysis workflow and returns validated structured data.

Agent	Responsibility
JD Classifier Agent	Classifies business domain, engineering domain, delivery speed pattern, maturity, evidence, alternatives, and rationale.
ATS Keyword Agent	Extracts must-have, important, bonus, tool, domain, and soft-skill signals from the job description.
Resume Match Agent	Scores resume alignment and separates strong, moderate, weak, missing, and risky support.
Truthfulness Guardrail Agent	Detects unsupported claims and suggests safe reframes based on actual resume evidence.
Resume Tailor Agent	Produces revised summary, reordered skills, rewritten bullets, final Markdown, and final LaTeX.
Interview Prep Agent	Generates technical, domain, behavioral, and resume-defense interview questions.
Synthesis Agent	Produces a hiring-manager verdict and company/role interest narrative.
Self-Review Agent	Critiques the completed analysis, assigns quality scores, identifies weak sections, and drives refinement.
Cross-Model Critique	Challenges JD classification when enabled and preserves uncertainty for human review.
AI Workflow
The user submits a job description, master resume, company metadata, target style, and optional LaTeX template.
The JD Classifier identifies domain and engineering context using evidence from the posting.
If enabled, cross-model critique reviews the classification for domain mistakes or overconfident assumptions.
The ATS Keyword Agent extracts requirements and maps them to resume support levels.
The Resume Match Agent scores alignment and identifies gaps, risks, and strong evidence.
The Truthfulness Guardrail Agent blocks unsafe claims and recommends transferable reframes.
The Resume Tailor Agent generates a complete final resume while preserving truthful original sections.
Interview preparation and hiring narrative agents generate candidate-facing preparation outputs.
The Self-Review Agent grades the full analysis and requests targeted refinement when quality is low.
The API returns a validated FullAnalysisResponse to the React dashboard.
Self-Review Loop
The self-review loop is designed to make the system less brittle than a single-pass LLM workflow.

After the initial analysis, the Self-Review Agent evaluates:

Classification quality
Semantic match quality
Guardrail quality
Tailoring quality
Synthesis quality
Overall answer quality
If the overall quality score falls below the configured acceptance threshold, the backend reruns only the weak sections where possible. Refinement is bounded by MAX_REFINEMENT_ROUNDS to avoid unbounded agent loops. The final response includes quality scores, refinement count, remaining risks, whether quality checks passed, and a final confidence label of high, medium, or low.

Cross-Model Critique
When ENABLE_CROSS_MODEL_CRITIQUE=true, CareerFit performs an additional classification review. The default routing uses OpenAI for schema-heavy extraction and Claude for recruiter-style critique and review.

The cross-model critique checks whether the initial classification is likely wrong, especially for business domain, engineering domain, and batch/streaming/hybrid speed pattern. If disagreement remains above the threshold after refinement, the system preserves the original classification and returns an alternative_classification object with reasons and confidence. This keeps the workflow transparent instead of silently replacing uncertain results.

Truthfulness Guardrails
CareerFit explicitly avoids the biggest failure mode in resume generation: inventing experience.

The guardrail layer flags:

Unsupported tools such as direct ownership of systems not present in the resume
Unsupported scale claims such as inflated data volume, traffic, latency, or reliability metrics
Unsupported domain expertise such as claiming prior construction, fintech, healthcare, or ad-tech experience without evidence
Unsupported architecture ownership where the resume does not show design authority
Risky insertions that may be useful only if the candidate can defend them in an interview
Instead of simply deleting missing requirements, the system provides safe reframes. For example, it may recommend positioning Redshift experience as transferable cloud warehouse engineering rather than claiming direct Azure Synapse ownership.

ATS Semantic Analysis
The ATS layer goes beyond literal keyword matching. It separates job requirements into:

must_have
important
bonus
tools
domain_terms
soft_skill_signals
It also classifies resume support into:

exact_match
semantic_match
inferred_match
missing_from_resume
This allows the system to recognize adjacent experience, such as ELT pipelines supporting data pipeline requirements, Redshift/Synapse/Snowflake supporting warehouse engineering, or API ingestion supporting integration requirements. Missing skills are reserved for concepts that are truly unsupported rather than merely phrased differently.

Resume Tailoring Pipeline
The tailoring pipeline is built around conservative editing.

It preserves:

Candidate header and contact information
Existing roles and experience context
Strong quantified bullets
Education and certifications
Production architecture, CI/CD, uptime, throughput, latency, and data-volume evidence
Original LaTeX layout when a template is provided
It changes:

Summary positioning
Skill ordering and emphasis
A small number of JD-aware bullets when truthful and useful
Domain-specific framing when classifier confidence is high enough
The output includes both a focused tailored draft and a complete final resume in Markdown and LaTeX.

PDF/LaTeX Export
CareerFit supports resume export through:

final_resume_markdown
final_resume_latex
POST /export-resume-pdf
Users can paste or upload an original LaTeX resume template. When PRESERVE_ORIGINAL_LATEX_TEMPLATE=true, the backend preserves the existing document structure where possible and replaces only supported sections such as Summary, Technical Skills, and selected Professional Experience bullets.

Built-in templates live in backend/templates/:

classic.tex
ats_clean.tex
modern.tex
compact.tex
enterprise.tex
PDF generation first attempts local pdflatex. If LaTeX compilation is unavailable or fails, the API reports a clear export error so the user can still download Markdown or LaTeX. A controlled plain-text fallback exists for non-template export paths.

Tech Stack
Layer	Technology
Backend API	Python, FastAPI, Starlette, Uvicorn
Data Validation	Pydantic v2
LLM Providers	OpenAI, Anthropic Claude
LLM Reliability	Structured JSON prompts, schema validation, retry loop, deterministic fallbacks
Frontend	React, TypeScript, Vite
Styling	CSS
Export	Markdown, LaTeX, local pdflatex, simple PDF fallback utility
Runtime Config	python-dotenv, environment variables
Tests	Pytest-style backend tests for LaTeX/PDF behavior
Screenshots
Add screenshots here after capturing the application in use.

Analysis Dashboard
Placeholder: job description and resume input view.

Resume Match Report
Placeholder: ATS scoring, semantic matches, gaps, and guardrail warnings.

Tailored Resume Output
Placeholder: final Markdown/LaTeX resume preview and export controls.

Self-Review Results
Placeholder: quality scores, final confidence, refinement rounds, and remaining risks.

Architecture Diagram


No
Yes or Max Rounds
React + TypeScriptDashboard
FastAPI Backend
Analysis Request Schema
JD Classifier Agent
Cross-Model ClassificationCritique
ATS Keyword Agent
Resume Match Agent
Truthfulness GuardrailAgent
Resume Tailor Agent
Interview Prep Agent
Synthesis Agent
Self-Review Agent
Quality >= Threshold?
Refine Weak Sections
FullAnalysisResponse
Markdown + LaTeX Resume
PDF Export Endpoint
Local Setup
Prerequisites
Python 3.11 or newer recommended
Node.js 18 or newer recommended
npm
Optional: MiKTeX, TeX Live, or another pdflatex installation for PDF export
Optional: OpenAI and Anthropic API keys for full multi-model behavior
Backend
cd backend
python -m venv venv
Activate the virtual environment:

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
Install dependencies:

pip install -r requirements.txt
Create backend/.env and add the environment variables shown below.

Run the API:

uvicorn main:app --reload
Backend URLs:

http://localhost:8000
http://localhost:8000/docs
Frontend
cd frontend
npm install
npm run dev
Frontend URL:

http://localhost:5173
Build Frontend
cd frontend
npm run build
Environment Variables
Create backend/.env:

OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

ENABLE_MULTI_MODEL=true
ENABLE_CROSS_MODEL_CRITIQUE=true
PRESERVE_ORIGINAL_LATEX_TEMPLATE=true

# Optional. Use fallback to force deterministic local logic.
LLM_PROVIDER=

OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LLM_MAX_RETRIES=2
LLM_TEMPERATURE=0.1
Notes:

If no provider keys are available, the backend uses deterministic fallbacks.
If ENABLE_MULTI_MODEL=true, agents are routed by task strength.
If one provider fails validation, the client can attempt the secondary provider.
If LLM_PROVIDER=fallback, no external LLM calls are made.
API Example
Full Analysis
POST /full-analysis
Content-Type: application/json
{
  "job_description": "Paste the target job description here.",
  "resume": "Paste the candidate's master resume here.",
  "original_latex_template": "Optional LaTeX resume template.",
  "resume_template": "classic",
  "company_name": "Example Company",
  "role_title": "Data Engineer",
  "target_style": "Consulting"
}
PDF Export
POST /export-resume-pdf
Content-Type: application/json
{
  "final_resume_latex": "Complete LaTeX resume output.",
  "company_name": "Example Company",
  "role_title": "Data Engineer",
  "candidate_name": "Candidate Name",
  "allow_plain_text_fallback": false
}
Example Workflow
Paste a target job description into the dashboard.
Paste the master resume into the resume input.
Optionally paste the original LaTeX resume template to preserve formatting.
Enter company name, role title, and target style.
Run full analysis.
Review the classification, ATS keywords, match scores, and missing requirements.
Check guardrail warnings before accepting any resume edits.
Review the tailored summary, skills, and rewritten bullets.
Inspect self-review scores and remaining risks.
Download Markdown, LaTeX, or generate a PDF.
Use interview prep questions to validate that every tailored claim is defensible.
Future Roadmap
Resume parsing from uploaded PDF and DOCX files
Side-by-side before/after resume diff
Persistent saved analyses with PostgreSQL or Supabase
Authentication and private user workspaces
Browser extension for LinkedIn, Indeed, and company career pages
Batch analysis across multiple job descriptions
Configurable role families beyond data engineering
More robust LaTeX template mapping and visual preview
Automated screenshot capture for portfolio documentation
Deployment configuration for cloud hosting
Portfolio Note
CareerFit AI Agent demonstrates applied AI engineering beyond a simple chatbot wrapper. It combines agent decomposition, model routing, schema validation, deterministic fallback behavior, critique loops, safety constraints, domain-aware semantic matching, and practical document export into a cohesive product workflow.
