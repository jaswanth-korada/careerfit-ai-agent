from services.rule_classifier import classify_jd
from schemas.analysis_schema import Classification
from services.llm_client import llm_client


def run_jd_classifier(job_description: str) -> Classification:
    fallback = Classification(**classify_jd(job_description))
    return llm_client.generate(
        schema=Classification,
        fallback=fallback,
        route="jd_classifier",
        system_prompt=(
            "PROMPT_VERSION=v2. You are the JD Classifier Agent for a recruiter-grade resume intelligence system. "
            "Classify only what the job description supports. Weight business-domain semantics above generic data "
            "engineering keywords. Prioritize company/product context, customer/business language, industry entities, "
            "and ecosystem terminology. Generic terms such as SQL, Spark, Airflow, warehouse, ETL, or pipelines may "
            "shape engineering_domain but must not dominate business_domain. Generic software terms such as platform, "
            "APIs, integrations, and Salesforce are weaker than industry signals. Evidence must be meaningful phrases "
            "with brief reasons, not isolated keywords."
        ),
        user_prompt=(
            "Classify this job description by business domain, engineering domain, delivery speed pattern, "
            "and company maturity. Include likely alternative business domains only when supported. Use domains such as "
            "Construction / Industrial Services, Energy / Utilities, Manufacturing, Logistics / Supply Chain, Healthcare, "
            "FinTech / Financial Infrastructure, Ad-Tech / Media Analytics, SaaS / Business Operations, Consulting / "
            "Enterprise Transformation, and Retail / E-commerce when the JD's business language supports them. Classify "
            "maturity using labels such as Enterprise Consulting, Growth-stage FinTech Platform, Mid-size Industrial "
            "Enterprise, SaaS Product Company, Big Tech / Platform Organization, or Enterprise Internal Analytics Team. "
            "ERP/reporting/dashboard/warehouse workflows are Batch-heavy; Kafka/Kinesis/Flink/events/real-time are Streaming-heavy; "
            "ETL/ELT plus streaming is Hybrid. Evidence entries should look like 'phrase - reason'. Add rationale explaining "
            "why the domain won over alternatives.\n\n"
            f"JOB DESCRIPTION:\n{job_description}"
        ),
    )
