from schemas.analysis_schema import InterviewPrep, Classification, KeywordAnalysis, ResumeMatch
from services.llm_client import llm_client


def _fallback_interview_prep(classification: Classification) -> InterviewPrep:
    consulting = "consult" in classification.business_domain.lower() or "consult" in classification.company_maturity.lower()
    fintech = "fintech" in classification.business_domain.lower()
    saas = "saas" in classification.business_domain.lower()
    construction = "construction" in classification.business_domain.lower() or "industrial" in classification.business_domain.lower()
    adtech = "ad-tech" in classification.business_domain.lower() or "media" in classification.business_domain.lower()
    return InterviewPrep(
        sql_questions=[
            "[medium] How would you design fact and dimension tables for a reporting warehouse? Hint: discuss grain, dimensions, late-arriving data, and metric definitions.",
            "[medium] Explain how you would validate row counts and detect duplicates after an ETL load. Hint: reconcile source counts, uniqueness checks, and anomaly thresholds.",
            "[hard] How would you optimize a slow SQL query used by business dashboards? Hint: inspect query plan, filters, joins, partitions, indexes, and materialization.",
        ],
        data_modeling_questions=[
            "[medium] How would you model golden datasets for reusable business metrics? Hint: define ownership, grain, lineage, and consumer contracts.",
            "[hard] How do you handle schema evolution without breaking downstream analysts? Hint: versioning, compatibility, deprecation, and communication.",
        ],
        data_platform_questions=[
            "[medium] What SLAs would you define for a critical analytics pipeline? Hint: freshness, completeness, latency, incident response, and consumer impact.",
            "[hard] How would you design analytics enablement for multiple stakeholder teams? Hint: certified datasets, documentation, access patterns, and feedback loops.",
        ],
        data_engineering_questions=[
            "[medium] Design an ETL pipeline that ingests data from multiple cloud sources into a warehouse. Hint: orchestration, retries, idempotency, and validation.",
            "[hard] How do you handle schema changes in production pipelines? Hint: contracts, backward compatibility, alerts, and consumer coordination.",
            "[medium] What monitoring and alerting would you add to a critical data pipeline? Hint: freshness, volume, quality, latency, and failure routing.",
        ],
        cloud_questions=[
            "[medium] When would you use AWS Glue vs Lambda vs Airflow for data integration? Hint: workload duration, orchestration needs, cost, and operational control.",
            "[medium] How would you optimize cloud data storage for cost and performance? Hint: file formats, partitioning, lifecycle policies, and workload patterns.",
            "[hard] How do you design secure access controls for data pipelines? Hint: least privilege, secrets, auditability, and data classification.",
        ],
        data_quality_questions=[
            "[medium] What checks would you put on a financial or business-critical dataset before publishing it? Hint: completeness, reconciliation, validity, and freshness.",
            "[hard] How would you respond if a trusted dashboard metric changed unexpectedly overnight? Hint: triage lineage, isolate releases, quantify impact, and communicate.",
        ],
        domain_business_questions=[
            "[medium] How do data reliability and trust affect business decisions in this domain? Hint: tie data quality to customer, revenue, risk, or operational impact.",
            "[medium] How would you prioritize a stakeholder request when data quality, speed, and scope conflict? Hint: clarify decision impact and negotiate a phased delivery.",
        ]
        + ([
            "[medium] How would you model project cost, schedule, and resource data for project performance dashboards? Hint: define project grain, job cost categories, dates, owners, and KPI consumers.",
            "[hard] How would you integrate ERP, estimating, bidding, or BIM data without claiming expertise in unsupported tools? Hint: discuss API/file ingestion, canonical models, validation, and stakeholder definitions.",
            "[medium] What operational KPIs would you clarify before building cost forecasting reports? Hint: ask about committed cost, actual cost, change orders, labor, schedule variance, and forecast ownership.",
        ] if construction else [])
        + (["[hard] In FinTech, how would you protect financial data integrity and privacy while enabling analytics? Hint: controls, lineage, reconciliation, and access boundaries."] if fintech else [])
        + (["[medium] In consulting, how would you handle ambiguous client requirements for a cloud modernization roadmap? Hint: discovery, governance, architecture documentation, and phased decisions."] if consulting else [])
        + (["[medium] In SaaS, how would you evaluate whether API integration data is reliable enough for customer-facing reporting? Hint: contracts, retries, drift, and observability."] if saas else [])
        + (["[hard] In ad-tech, how would you keep campaign measurement and attribution metrics consistent across batch and event pipelines? Hint: event definitions, identity, latency, deduping, and reconciliation."] if adtech else []),
        behavioral_questions=[
            "[medium] Tell me about a time you handled ambiguous requirements. Hint: show how you clarified the decision, scoped options, and aligned stakeholders.",
            "[medium] Tell me about a time a pipeline failed and how you fixed it. Hint: cover detection, root cause, mitigation, prevention, and communication.",
            "[medium] How do you communicate technical tradeoffs to non-technical stakeholders? Hint: connect cost, reliability, timeline, and business impact.",
        ] + (["[hard] Describe how you would manage expectations with a difficult client. Hint: align on outcomes, risks, decision rights, and documented next steps."] if consulting else []),
        resume_defense_questions=[
            "[hard] You mention 800GB+ daily processing. What was the architecture, bottleneck, and reliability model? Hint: be ready to name services, partitioning, orchestration, and failure handling.",
            "[hard] You mention 33% query improvement. What exact optimization caused the improvement? Hint: show before/after query behavior and how it was measured.",
            "[medium] You mention data quality checks. What types of checks did you implement? Hint: describe completeness, uniqueness, validity, reconciliation, and alerting.",
        ],
        confidence=0.66,
        evidence=classification.evidence[:8],
    )


def generate_interview_prep(
    job_description: str,
    resume: str,
    classification: Classification,
    keywords: KeywordAnalysis,
    resume_match: ResumeMatch,
) -> InterviewPrep:
    fallback = _fallback_interview_prep(classification)
    return llm_client.generate(
        schema=InterviewPrep,
        fallback=fallback,
        route="interview_prep",
        system_prompt=(
            "PROMPT_VERSION=v2. You are the Interview Prep Agent. Generate realistic domain-specific, tool-specific, "
            "and resume-defense questions tied to the JD and candidate metrics. Each question must include a difficulty "
            "label and expected answer hint. Include SQL, Data Modeling, Data Platform, Cloud/Warehouse, Data Quality, "
            "Domain/Business, Behavioral, and Resume Defense categories where the schema allows. Use the detected domain: "
            "construction questions should mention project cost, schedule, resource data, ERP integrations, estimating, bidding, "
            "BIM, operational KPIs, project performance dashboards, and field operations; FinTech questions should mention privacy, "
            "integrity, trusted datasets, auditability, and metric consistency; Consulting should mention client ambiguity, governance, "
            "architecture documentation, and stakeholder management; SaaS should mention API contracts, integrations, reporting, and schema drift."
        ),
        user_prompt=(
            "Generate interview prep questions across SQL, data modeling, data platform, data engineering, cloud/warehouse, "
            "data quality, domain/business, behavioral, and resume defense. Use difficulty labels like [easy], [medium], "
            "or [hard], and include a concise expected-answer hint in each question. Focus on questions the candidate is "
            "likely to face because of this JD and this resume.\n\n"
            f"JOB DESCRIPTION:\n{job_description}\n\n"
            f"CLASSIFICATION:\n{classification.model_dump_json()}\n\n"
            f"KEYWORDS:\n{keywords.model_dump_json()}\n\n"
            f"MATCH REPORT:\n{resume_match.model_dump_json()}\n\n"
            f"RESUME:\n{resume}"
        ),
    )
