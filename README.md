# CareerFit AI Agent

An advanced AI job-description analyzer and resume tailoring agent for data engineering roles.

This is not a basic resume rewriter. It is an explainable, multi-agent workflow that:

- Classifies job descriptions by business domain, engineering domain, speed pattern, and company maturity
- Extracts ATS keywords and hidden hiring-manager expectations
- Compares a resume against the JD
- Produces match scores and gap analysis
- Generates truthfulness warnings so the user does not claim unsupported skills
- Tailors resume summary, skills, and bullets based on role type
- Generates interview preparation questions
- Exports Markdown-ready outputs

## Architecture

```text
Frontend React Dashboard
        ↓
FastAPI Backend
        ↓
Agent Orchestrator
        ↓
JD Classifier → ATS Keyword Agent → Resume Match Agent → Guardrail Agent → Resume Tailor → Interview Prep Agent
        ↓
Structured JSON Response
```

## Tech Stack

- Backend: FastAPI, Python, Pydantic
- Frontend: React, TypeScript, Vite
- AI Layer: Structured OpenAI/Claude calls with validated rule-based fallback
- Storage: In-memory / browser localStorage for MVP
- Export: Markdown and LaTeX output fields

Each agent returns structured JSON, confidence scoring, and evidence. LLM responses are retried and validated with Pydantic. If an LLM provider is unavailable or returns invalid JSON, the backend falls back to conservative deterministic logic rather than fabricating unsupported claims.

## Why This Project Is Advanced

Most resume tools blindly rewrite resumes. CareerFit AI Agent uses:

- Multi-agent architecture
- Explainable classification
- Confidence scoring
- Evidence snippets from the JD
- Rule-based + LLM-ready reasoning
- Truthfulness guardrails
- Interview-risk detection
- Company-style tailoring: Big Tech, SaaS, Consulting, Startup, General

## Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## Main API Endpoint

```http
POST /full-analysis
```

Request:

```json
{
  "job_description": "Paste JD here",
  "resume": "Paste resume here",
  "company_name": "PwC",
  "role_title": "Data Engineer Senior Associate",
  "target_style": "Consulting"
}
```

## Environment Variables

Create `.env` inside backend:

```bash
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
ENABLE_MULTI_MODEL=true
ENABLE_CROSS_MODEL_CRITIQUE=true
PRESERVE_ORIGINAL_LATEX_TEMPLATE=true
LLM_PROVIDER=         # optional: fallback forces deterministic mode; openai/claude are for single-provider mode when multi-model is disabled
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LLM_MAX_RETRIES=2
LLM_TEMPERATURE=0.1
```

When `ENABLE_MULTI_MODEL=true`, agents are routed by strength: OpenAI handles schema-heavy extraction, ATS keywords, resume matching, and initial JD classification; Claude handles recruiter realism, truthfulness guardrails, tailored resume generation, interview prep, synthesis, and self-critique. If a preferred provider fails validation or exhausts retries, the client falls back to the secondary provider while preserving Pydantic schema validation. Set `LLM_PROVIDER=fallback` to force deterministic local fallbacks.

Classification is confidence-based reasoning, not a guarantee. When cross-model critique remains unresolved, the API preserves the original classification and returns Claude's alternative classification with reasons so a human can review the disagreement.

## Final Resume PDF Export

The Tailored Resume tab generates a complete final resume in Markdown and LaTeX, preserving the master resume's contact info, experience context, education, certifications, and truthful unchanged sections while replacing only the summary, skills ordering, and relevant bullets.

The app has two resume inputs: Master Resume Content for analysis/tailoring, and Original LaTeX Template for final formatting. Paste or upload your `.tex` resume template to preserve documentclass, packages, margins, header layout, custom commands, spacing, section formatting, education, and certifications. The backend modifies only Summary, Technical Skills, and selected Professional Experience bullets.

When `PRESERVE_ORIGINAL_LATEX_TEMPLATE=true`, final LaTeX is rendered from the user-provided LaTeX template when one is pasted or uploaded. If no custom template is provided, the frontend's Resume Template dropdown selects one of the built-in templates: Classic, ATS Clean, Modern, Compact, or Enterprise. Classic is the default and uses the cleaned original LaTeX resume design. If a selected built-in template is missing, the backend falls back to Classic and returns a warning.

Built-in templates live in `backend/templates/` as `classic.tex`, `ats_clean.tex`, `modern.tex`, `compact.tex`, and `enterprise.tex`. All support the shared placeholders `{{SUMMARY}}`, `{{TECHNICAL_SKILLS}}`, `{{AZURE_BULLETS}}`, and `{{AWS_BULLETS}}`; custom user templates can use those placeholders too. If placeholders are absent from a custom template, the backend attempts section-aware replacement for Summary, Technical Skills, and Professional Experience bullet blocks.

Use `POST /export-resume-pdf` with `final_resume_latex`, `company_name`, `role_title`, and `candidate_name` to generate a downloadable PDF. Filenames are generated as lowercase underscore slugs, for example `jaswanth_korada_baker_electric_data_engineer_ii.pdf`, with special characters removed and length capped.

PDF export first attempts to compile LaTeX with local `pdflatex` when available. If LaTeX is unavailable or compilation fails, the backend falls back to a simple ATS-friendly one-column text PDF generator. If PDF export still fails, the frontend keeps LaTeX and Markdown downloads available.

## GitHub Resume Bullet

**CareerFit AI Agent — AI-Powered JD Analyzer and Resume Tailoring System**  
Built a multi-agent AI application that classifies job descriptions, extracts ATS keywords, scores resume-job fit, identifies unsupported claims, and generates tailored resumes and interview preparation using FastAPI, React, Pydantic schemas, and explainable LLM-ready workflows.

## Roadmap

- Add PDF resume parsing
- Add authentication
- Add PostgreSQL/Supabase persistence
- Add side-by-side before/after resume diff
- Add browser extension for LinkedIn/Indeed JDs
