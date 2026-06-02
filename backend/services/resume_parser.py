import re
from typing import List

from schemas.careerfit_models import ResumeEvidence


KNOWN_TOOLS = [
    "Python", "SQL", "PySpark", "Spark", "Spark SQL", "Kafka", "Airflow",
    "AWS Glue", "Glue", "EMR", "S3", "Lambda", "SQS", "EventBridge",
    "Redshift", "CloudWatch", "IAM", "KMS", "CloudFormation",
    "Azure Data Factory", "ADF", "Databricks", "Synapse", "ADLS",
    "Snowflake", "PostgreSQL", "MySQL", "Oracle", "SQL Server",
    "Terraform", "Docker", "GitHub Actions", "Bamboo", "Git"
]


def _extract_bullets(text: str) -> List[str]:
    """Extract bullet-like lines from plain text or LaTeX resume."""
    bullets = []

    for line in text.splitlines():
        cleaned = line.strip()

        if cleaned.startswith("\\item"):
            cleaned = cleaned.replace("\\item", "").strip()
            bullets.append(cleaned)

        elif cleaned.startswith("- ") or cleaned.startswith("• "):
            bullets.append(cleaned[2:].strip())

    return bullets


def _extract_tools(text: str) -> List[str]:
    """Find known tools mentioned in the resume."""
    found = []

    lower_text = text.lower()

    for tool in KNOWN_TOOLS:
        if tool.lower() in lower_text:
            found.append(tool)

    return sorted(set(found))


def _extract_metrics(text: str) -> List[str]:
    """Extract simple metric patterns such as %, TB, GB, ms, seconds, hours."""
    metric_patterns = [
        r"\d+\.?\d*\s?%",
        r"\d+\.?\d*\s?(GB|TB|MB)\+?/?(?:day|month)?",
        r"\d+\.?\d*\s?(ms|seconds|minutes|hours)",
        r"\d+\.?\d*x",
        r"\d+\+?\s?(daily workloads|pipelines|DAGs|validation tests|users|analysts)"
    ]

    metrics = []

    for pattern in metric_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                continue

    combined_pattern = "|".join(metric_patterns)
    matches = re.finditer(combined_pattern, text, flags=re.IGNORECASE)

    for match in matches:
        metrics.append(match.group(0))

    return sorted(set(metrics))


def _extract_certifications(text: str) -> List[str]:
    """Extract common certification lines."""
    certifications = []

    cert_keywords = [
        "AWS Certified",
        "Azure Data Engineer",
        "Solutions Architect",
        "Microsoft Certified"
    ]

    for line in text.splitlines():
        for keyword in cert_keywords:
            if keyword.lower() in line.lower():
                certifications.append(line.strip())

    return certifications


def parse_resume(resume_text: str) -> ResumeEvidence:
    """
    Parse resume text or LaTeX into structured candidate evidence.
    This is V1: rule-based, simple, and explainable.
    """

    bullets = _extract_bullets(resume_text)
    tools = _extract_tools(resume_text)
    metrics = _extract_metrics(resume_text)
    certifications = _extract_certifications(resume_text)

    return ResumeEvidence(
        skills=tools,
        tools=tools,
        experience_bullets=bullets,
        projects=[],
        metrics=metrics,
        architectures=[],
        certifications=certifications
    )
