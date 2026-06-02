# CareerFit AI — MVP Build Plan

## MVP Goal

Build the FIRST fully working end-to-end version of CareerFit AI.

The MVP should:

* analyze a JD
* assess realistic fit
* determine safe engineering identity positioning
* retrieve relevant experience
* generate a tailored resume
* evaluate trust and interview defensibility
* export a final LaTeX resume

The MVP is NOT intended to be enterprise-grade.

The goal is:

## working orchestration before scaling complexity.

---

# MVP Principles

## 1. Build Core Intelligence First

Prioritize:

* orchestration quality
* credibility validation
* retrieval quality
* narrative generation

Do NOT prioritize:

* animations
* dashboards
* enterprise infra
* cloud scaling
* authentication systems

---

## 2. Retrieval Before Complexity

Avoid:

```text
full resume → giant prompt → LLM
```

Prefer:

```text
JD signals
→ retrieve relevant evidence
→ compressed context
→ orchestration
```

This reduces:

* token usage
* hallucination
* noisy outputs
* model dependency

---

## 3. Modular Architecture

Each engine should become an isolated module.

Avoid:

* giant orchestration prompts
* tightly coupled logic
* hardcoded workflows

The system should evolve into:

## orchestration services

---

# FINAL MVP FEATURES

## INPUTS

### Resume Upload

Supports:

* LaTeX resume
* plain text resume
* PDF parsing later

---

### Job Description Input

Supports:

* pasted JD text
* future: URL parsing

---

### User Risk Mode

Options:

* Safe
* Balanced
* Aggressive Stretch

---

# OUTPUTS

## 1. Pre-Assessment Result

Displays:

* fit level
* major gaps
* hard gates
* proceed recommendation

---

## 2. Identity Boundary Analysis

Displays:

* Green identities
* Yellow identities
* Red identities
* recommended positioning strategy

---

## 3. Tailored Resume

Outputs:

* final LaTeX resume
* one-page validated
* ATS aligned
* recruiter-readable

---

## 4. Trust Score Summary

Displays:

* ATS alignment
* recruiter trust
* operational credibility
* interview defensibility
* identity coherence

---

## 5. Interview Risk Report

Displays:

* weak proof areas
* likely technical follow-up questions
* unsupported tooling risks
* identity stretch warnings

---

## 6. Visual Change Audit

Displays:

* added content
* removed content
* modified content
* reason for every change

---

# MVP Backend Flow

```text
Resume Upload
        ↓
Resume Parser
        ↓
Candidate Knowledge Graph
        ↓
JD Input
        ↓
JD Decomposition
        ↓
Identity Boundary Analysis
        ↓
Promise = Proof Validation
        ↓
Retrieval Engine
        ↓
Narrative Generation
        ↓
Critique Loop
        ↓
Trust Scoring
        ↓
LaTeX Rendering
        ↓
One-Page Validation
        ↓
Final Output
```

---

# PHASE 1 — FOUNDATION

## Goal

Create stable orchestration infrastructure.

### Tasks

* freeze framework docs
* define architecture
* define backend structure
* define orchestration order
* create sample JSON outputs

### Deliverables

* framework_v1.md
* architecture_v1.md
* mvp_build_plan.md

---

# PHASE 2 — RESUME INTELLIGENCE

## Goal

Convert resumes into structured engineering evidence.

### Modules

* resume parser
* knowledge graph
* metric extraction
* architecture extraction
* skill extraction

### Deliverables

```json
{
  "skills": [],
  "tools": [],
  "architectures": [],
  "metrics": [],
  "experience_bullets": []
}
```

---

# PHASE 3 — JD INTELLIGENCE

## Goal

Understand the REAL engineering identity behind the JD.

### Modules

* role identity classification
* platform dominance detection
* orchestration pattern extraction
* semantic tier mapping
* hidden expectation extraction

### Deliverables

```json
{
  "role_identity": "",
  "tier1_signals": [],
  "tier2_signals": [],
  "hidden_expectations": []
}
```

---

# PHASE 4 — IDENTITY SAFETY

## Goal

Prevent unrealistic resume mutation.

### Modules

* Green/Yellow/Red detection
* risk scoring
* mutation boundary rules
* stretch-mode control

### Deliverables

```json
{
  "green": [],
  "yellow": [],
  "red": [],
  "risk_level": ""
}
```

---

# PHASE 5 — RETRIEVAL ENGINE

## Goal

Retrieve only relevant candidate evidence.

### Modules

* keyword retrieval
* semantic retrieval later
* bullet ranking
* evidence compression

### Deliverables

```json
{
  "retrieved_bullets": [],
  "retrieved_projects": [],
  "retrieved_metrics": []
}
```

---

# PHASE 6 — NARRATIVE GENERATION

## Goal

Generate believable engineering bullets.

### Requirements

* operational realism
* systems reasoning
* human engineering voice
* ATS precision
* follow-up defensibility

### Avoid

* generic AI language
* fake metrics
* over-polished wording
* keyword stuffing

---

# PHASE 7 — REVIEW & CRITIQUE

## Goal

Refine outputs until convergence.

### Reviewers

* ATS reviewer
* recruiter reviewer
* engineering reviewer
* trust reviewer
* readability reviewer

### Convergence Rule

Stop optimization once:

* readability declines
* semantics become unnatural
* density becomes excessive
* additional iterations provide marginal value

---

# PHASE 8 — FINAL OUTPUT

## Goal

Generate production-quality final resume.

### Components

* LaTeX renderer
* one-page validator
* visual audit
* trust summary
* interview risk report

---

# SUGGESTED TECH STACK

## Frontend

* React
* TypeScript
* Tailwind CSS

---

## Backend

* FastAPI
* Python

---

## AI Models

* Claude
* OpenAI

---

## Retrieval

Initial:

* keyword retrieval

Later:

* embeddings
* semantic retrieval

---

## Storage

Initial:

* JSON files

Later:

* PostgreSQL
* vector database

---

# OUT OF SCOPE FOR V1

Do NOT build:

* authentication
* billing
* enterprise infrastructure
* Kubernetes
* distributed agents
* cloud scaling
* analytics dashboards
* team workspaces

Focus ONLY on:

## orchestration quality.

---

# FINAL MVP SUCCESS CRITERIA

The MVP succeeds if:

* resumes feel human-written
* resumes survive follow-up questioning
* resumes remain believable
* resumes maintain ATS compatibility
* identity positioning remains realistic
* users understand WHY changes happened
* outputs feel trustworthy

The MVP fails if:

* resumes feel AI-generated
* over-tailoring creates interview risk
* formatting breaks
* identity mutation becomes unrealistic
* outputs become keyword-dense and unnatural
* orchestration becomes impossible to maintain
