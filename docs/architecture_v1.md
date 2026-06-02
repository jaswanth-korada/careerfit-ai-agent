# CareerFit AI — Architecture V1

## System Goal

CareerFit AI converts a resume and job description into a tailored, ATS-readable, recruiter-trusted, and interview-defensible resume.

The system is designed around credibility, not keyword stuffing.

---

# High-Level Pipeline

```text
Resume + JD Upload
        ↓
Pre-Assessment Engine
        ↓
Identity Boundary Engine
        ↓
JD Decomposition Engine
        ↓
Candidate Knowledge Graph
        ↓
Promise = Proof Validator
        ↓
Retrieval Engine
        ↓
Tool-to-Workload Coupling Engine
        ↓
Engineering Narrative Design Engine
        ↓
ATS + Human Balance Engine
        ↓
Recursive Critique Loop
        ↓
Trust & Defensibility Engine
        ↓
LaTeX Rendering Engine
        ↓
One-Page Validation
        ↓
Visual Change Audit
        ↓
Interview Risk Report
        ↓
Memory Log Update
```

---

# Core Modules

## 1. Pre-Assessment Engine

Checks whether the JD is worth pursuing before generating a resume.

Responsibilities:

* duplicate JD detection
* visa/work authorization gate check
* fit assessment
* gap detection
* proceed / caution / skip recommendation

Output:

```json
{
  "fit_level": "Strong | Moderate | Weak | Hard Gate",
  "technical_match": "High | Medium | Low",
  "experience_match": "High | Medium | Low",
  "structural_gates": [],
  "gaps": [],
  "recommendation": "Proceed | Proceed with caution | Skip"
}
```

---

## 2. Identity Boundary Engine

Prevents unrealistic resume positioning.

Zones:

* Green: strongly proven identity
* Yellow: transferable but partially proven identity
* Red: weakly supported or unsafe identity

Output:

```json
{
  "green_identities": [],
  "yellow_identities": [],
  "red_identities": [],
  "recommended_mode": "Safe | Balanced | Aggressive Stretch",
  "risk_notes": []
}
```

Core rule:
Do not transform the candidate into a different engineer. Only amplify believable identities already supported by experience.

---

## 3. JD Decomposition Engine

Extracts the real engineering intent of the JD.

Responsibilities:

* role identity classification
* platform dominance detection
* orchestration style detection
* ATS signal extraction
* hidden recruiter expectation detection
* semantic dominance tiering

Output:

```json
{
  "role_identity": "",
  "platform_dominance": "",
  "orchestration_style": "",
  "tier1_signals": [],
  "tier2_signals": [],
  "tier3_minimize": [],
  "hidden_expectations": []
}
```

---

## 4. Candidate Knowledge Graph

Converts the candidate resume into structured engineering evidence.

Stores:

* skills
* tools
* experiences
* projects
* metrics
* workloads
* architecture patterns
* domains
* certifications

Output:

```json
{
  "skills": [],
  "tools": [],
  "experience_bullets": [],
  "metrics": [],
  "projects": [],
  "architectures": [],
  "certifications": []
}
```

---

## 5. Promise = Proof Validator

Ensures skills are supported by real evidence.

Rule:
Skills section = promise
Experience section = proof

Responsibilities:

* map skills to bullets/projects
* detect unsupported skills
* downgrade weak claims
* remove irrelevant skills
* warn user about proof gaps

Output:

```json
{
  "proven_skills": [],
  "weak_skills": [],
  "unsupported_skills": [],
  "removed_skills": [],
  "proof_map": {}
}
```

---

## 6. Retrieval Engine

Retrieves only the most relevant candidate evidence for the JD.

Purpose:
Avoid sending the full resume context into the LLM every time.

Workflow:

```text
JD signals
    ↓
candidate evidence search
    ↓
top relevant bullets/projects/skills
    ↓
compressed prompt context
```

Benefits:

* lower token usage
* less hallucination
* less noise
* better JD-specific relevance

---

## 7. Tool-to-Workload Coupling Engine

Transforms tool mentions into engineering ownership.

Bad:

```text
Used Spark and Airflow.
```

Good:

```text
Reworked Airflow dependency chains and parallelized Spark workloads to reduce runtime bottlenecks.
```

Pattern:

```text
Tool → workload → operational behavior → engineering outcome
```

---

## 8. Engineering Narrative Design Engine

Rewrites resume bullets so they sound like real engineering experience.

Optimizes for:

* operational ownership
* systems reasoning
* architecture intent
* production realism
* follow-up question survivability
* human engineering voice

Avoids:

* keyword dumping
* artificial metrics
* generic AI wording
* over-polished corporate language

---

## 9. ATS + Human Balance Engine

Balances exact ATS terms with natural engineering language.

Core rule:
ATS precision lives in nouns.
Human realism lives in verbs and reasoning.

Example:

* ATS nouns: AWS Glue, EMR, PySpark, S3, Lambda, EventBridge
* Human reasoning: why the pipeline was event-driven, why partitioning mattered, why metadata-driven design reduced rewrites

---

## 10. Recursive Critique Loop

Runs multiple internal reviews before final output.

Reviewers:

* ATS reviewer
* recruiter reviewer
* engineering manager reviewer
* operational realism reviewer
* readability reviewer
* interview defensibility reviewer

Convergence rule:
Stop improving when additional changes reduce readability, increase density, or provide only marginal value.

---

## 11. Trust & Defensibility Engine

Scores resume credibility.

Dimensions:

```json
{
  "ats_alignment": "",
  "recruiter_trust": "",
  "operational_credibility": "",
  "interview_defensibility": "",
  "identity_coherence": ""
}
```

The goal is not fake precision. Scores should be explained with evidence.

---

## 12. LaTeX Rendering Engine

Generates the final resume using the candidate’s exact LaTeX format.

Responsibilities:

* preserve template
* preserve Overleaf compatibility
* preserve spacing
* preserve icon usage
* preserve section structure
* avoid formatting drift

This module is separate from orchestration logic.

---

## 13. One-Page Validation

Ensures the resume fits on one page.

Compression order:

```text
remove redundancy
→ remove filler
→ tighten syntax
→ merge overlap
→ preserve strong semantics
```

Never remove strong operational reasoning just to save space.

---

## 14. Visual Change Audit

Creates a side-by-side explanation of every change.

Shows:

* added content
* removed content
* unchanged content
* JD signal addressed
* framework rule applied

Purpose:
Explainable Resume Engineering.

---

## 15. Interview Risk Report

Forecasts likely interview vulnerabilities.

Examples:

* unsupported technology claims
* weak depth in a platform
* transferable but not direct experience
* likely follow-up questions
* architecture scrutiny areas

---

## 16. Memory Log Update

Stores completed JD processing history.

Tracks:

* company
* role
* date
* fit level
* selected identity
* risk zone
* final resume version

Used for:

* duplicate detection
* historical comparison
* application activity dashboard

---

# Suggested Backend Folder Structure

```text
backend/
├── agents/
│   ├── ats_reviewer.py
│   ├── recruiter_reviewer.py
│   ├── engineering_reviewer.py
│   └── interview_risk_reviewer.py
│
├── orchestration/
│   ├── pipeline.py
│   ├── jd_decomposer.py
│   ├── identity_boundary.py
│   └── critique_loop.py
│
├── retrieval/
│   ├── resume_parser.py
│   ├── knowledge_graph.py
│   └── retriever.py
│
├── validators/
│   ├── promise_proof.py
│   ├── visa_gate.py
│   ├── duplicate_check.py
│   └── one_page_check.py
│
├── scoring/
│   ├── fit_score.py
│   └── trust_score.py
│
├── rendering/
│   ├── latex_renderer.py
│   └── change_audit.py
│
├── memory/
│   └── jd_log.py
│
└── main.py
```

---

# MVP Scope

The first version should support:

Input:

* resume text or LaTeX
* job description text
* user risk mode: Safe / Balanced / Aggressive Stretch

Output:

* pre-assessment result
* identity zone analysis
* tailored LaTeX resume
* trust score summary
* interview risk report

Out of scope for V1:

* authentication
* payments
* vector database
* team accounts
* dashboard analytics
* multi-user history
* enterprise deployment

---

# V1 Build Priority

Build in this exact order:

1. Resume parser
2. JD decomposition engine
3. Identity boundary engine
4. Promise = Proof validator
5. Basic retrieval engine
6. Narrative generation engine
7. Review agents
8. LaTeX renderer
9. One-page validation
10. Visual change audit
11. Interview risk report
12. Memory log

Do not start with UI polish. Build the orchestration core first.
