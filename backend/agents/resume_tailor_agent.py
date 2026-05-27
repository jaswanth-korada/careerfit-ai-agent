from schemas.analysis_schema import GuardrailReport, TailoredResume, Classification, KeywordAnalysis, ResumeMatch
from services.llm_client import llm_client
from services.semantic_matching import normalize_skill
from pathlib import Path
import os
import re


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
TEMPLATE_FILES = {
    "classic": "classic.tex",
    "ats_clean": "ats_clean.tex",
    "modern": "modern.tex",
    "compact": "compact.tex",
    "enterprise": "enterprise.tex",
}
TRUSTED_LATEX_BULLET_PREFIX = "\0TRUSTED_LATEX_BULLET\0"


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _latex_section(title: str, body: str) -> str:
    if not body.strip():
        return ""
    lines = []
    in_items = False
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("- "):
            if not in_items:
                lines.append("\\begin{itemize}")
                in_items = True
            lines.append(f"\\item {_latex_escape(line[2:].strip())}")
        else:
            if in_items:
                lines.append("\\end{itemize}")
                in_items = False
            lines.append(_latex_escape(line))
    if in_items:
        lines.append("\\end{itemize}")
    return f"\\section*{{{_latex_escape(title)}}}\n" + "\n".join(lines)


def _strip_prerendered_resume_fragments(resume: str) -> str:
    candidate_starts: list[int] = []
    for match in re.finditer(r"(?m)^#\s+(.+?)\s*$", resume):
        title = match.group(1).strip()
        if "tailored resume draft" in title.lower() or _is_resume_section_title(title):
            continue
        suffix = resume[match.start():]
        has_core_sections = all(
            re.search(rf"(?im)^#{{1,6}}\s+{section}\s*$", suffix)
            for section in ["Summary", "Technical Skills", "Professional Experience"]
        )
        if has_core_sections:
            candidate_starts.append(match.start())

    if candidate_starts:
        return resume[candidate_starts[-1]:].strip()
    return resume


def _section_map(resume: str) -> tuple[str, dict[str, str]]:
    resume = _strip_prerendered_resume_fragments(resume)
    section_aliases = {
        "summary", "professional summary", "skills", "technical skills", "core skills",
        "experience", "professional experience", "work experience", "education",
        "certification", "certifications", "projects", "awards", "publications",
    }
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
    header_lines: list[str] = []
    sections: dict[str, str] = {}
    current_title: str | None = None
    current_lines: list[str] = []
    seen_resume_section = False

    def flush_section() -> None:
        if current_title and current_title not in sections:
            sections[current_title] = "\n".join(current_lines).strip()

    for raw in resume.strip().splitlines():
        match = heading_pattern.match(raw.strip())
        if match:
            title = match.group(2).strip()
            normalized = title.lower()
            if "tailored resume draft" in normalized:
                flush_section()
                break
            is_resume_section = seen_resume_section or normalized in section_aliases
            if is_resume_section:
                flush_section()
                current_title = normalized
                current_lines = []
                seen_resume_section = True
            else:
                header_lines.append(raw)
            continue

        if current_title:
            current_lines.append(raw)
        else:
            header_lines.append(raw)

    flush_section()
    return "\n".join(header_lines).strip(), sections


def _find_section(sections: dict[str, str], names: list[str]) -> str:
    for wanted in names:
        for title, body in sections.items():
            if wanted in title:
                return body
    return ""


def _is_resume_section_title(title: str) -> bool:
    normalized = title.strip().lower()
    return normalized in {
        "summary", "professional summary", "skills", "technical skills", "core skills",
        "experience", "professional experience", "work experience", "education",
        "certification", "certifications", "projects", "awards", "publications",
    }


def _clean_resume_section_body(body: str) -> str:
    clean_lines: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        lowered = line.lower().strip("# ")
        if not line:
            continue
        if "tailored resume draft" in lowered:
            break
        if re.match(r"^#{1,6}\s+(summary|technical skills|skills|core skills|professional experience|experience|work experience)\b", line, re.IGNORECASE):
            break
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()


def _clean_resume_header(header: str) -> str:
    clean_lines: list[str] = []
    for raw in header.splitlines():
        if "tailored resume draft" in raw.lower():
            break
        clean_lines.append(raw.rstrip())

    last_candidate_heading = None
    for index, line in enumerate(clean_lines):
        match = re.match(r"^#\s+(.+?)\s*$", line.strip())
        if match and not _is_resume_section_title(match.group(1)):
            last_candidate_heading = index
    if last_candidate_heading is not None:
        clean_lines = clean_lines[last_candidate_heading:]

    return "\n".join(line for line in clean_lines if line.strip()).strip()


def _markdown_heading_count(markdown: str, title: str) -> int:
    return len(re.findall(rf"(?im)^#\s+{re.escape(title)}\s*$", markdown))


def _markdown_section_body(markdown: str, title: str) -> str:
    pattern = re.compile(
        rf"(?im)^#{{1,6}}\s+{re.escape(title)}\s*$",
    )
    match = pattern.search(markdown)
    if not match:
        return ""
    next_heading = re.search(r"(?m)^#{1,6}\s+", markdown[match.end():])
    end = match.end() + next_heading.start() if next_heading else len(markdown)
    return markdown[match.end():end]


def _validate_final_resume_markdown(markdown: str) -> None:
    required_sections = ["Summary", "Technical Skills", "Professional Experience", "Education", "Certifications"]
    errors: list[str] = []
    for section in required_sections:
        count = _markdown_heading_count(markdown, section)
        if count != 1:
            errors.append(f"expected exactly one {section} section, found {count}")

    if "tailored resume draft" in markdown.lower():
        errors.append("Tailored Resume Draft leaked into final resume Markdown")

    if errors:
        raise ValueError("Invalid final resume Markdown: " + "; ".join(errors))


def _markdown_to_latex_lines(markdown: str) -> str:
    lines: list[str] = []
    in_items = False
    rendered_header = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            if in_items:
                lines.append("\\end{itemize}")
                in_items = False
            lines.append("")
            continue
        if line.startswith("# "):
            if in_items:
                lines.append("\\end{itemize}")
                in_items = False
            if not rendered_header:
                lines.append("\\begin{center}")
                lines.append(f"{{\\LARGE\\textbf{{{_latex_escape(line[2:].strip())}}}}}")
                lines.append("\\end{center}")
                rendered_header = True
            else:
                lines.append(f"\\section*{{{_latex_escape(line[2:].strip())}}}")
        elif line.startswith("## "):
            if in_items:
                lines.append("\\end{itemize}")
                in_items = False
            lines.append(f"\\section*{{{_latex_escape(line[3:].strip())}}}")
        elif line.startswith("- "):
            if not in_items:
                lines.append("\\begin{itemize}[leftmargin=*]")
                in_items = True
            lines.append(f"\\item {_latex_escape(line[2:].strip())}")
        else:
            if in_items:
                lines.append("\\end{itemize}")
                in_items = False
            lines.append(_latex_escape(line))
    if in_items:
        lines.append("\\end{itemize}")
    return "\n".join(lines)


def _build_full_latex(markdown: str) -> str:
    return (
        "\\documentclass[11pt]{article}\n"
        "\\usepackage[margin=0.65in]{geometry}\n"
        "\\usepackage{enumitem}\n"
        "\\usepackage[hidelinks]{hyperref}\n"
        "\\setlength{\\parindent}{0pt}\n"
        "\\setlength{\\parskip}{4pt}\n"
        "\\begin{document}\n"
        f"{_markdown_to_latex_lines(markdown)}\n"
        "\\end{document}\n"
    )


def _build_latex(summary: str, skills: list[str], bullets: list[str]) -> str:
    skill_text = _latex_escape(", ".join(skills))
    bullet_text = "\n".join([f"\\item {_latex_escape(bullet)}" for bullet in bullets])
    return (
        "\\documentclass[11pt]{article}\n"
        "\\usepackage[margin=0.7in]{geometry}\n"
        "\\usepackage{enumitem}\n"
        "\\begin{document}\n"
        "\\section*{Summary}\n"
        f"{_latex_escape(summary)}\n\n"
        "\\section*{Core Skills}\n"
        f"{skill_text}\n\n"
        "\\section*{Tailored Experience Bullets}\n"
        "\\begin{itemize}[leftmargin=*]\n"
        f"{bullet_text}\n"
        "\\end{itemize}\n"
        "\\end{document}\n"
    )


def _build_full_resume_markdown(resume: str, summary: str, skills: list[str], bullets: list[str]) -> str:
    header, sections = _section_map(resume)
    header = _clean_resume_header(header)
    if not header:
        header = "# Resume"
    elif not header.lstrip().startswith("#"):
        header = "# " + header.splitlines()[0].lstrip("# ").strip() + "\n" + "\n".join(header.splitlines()[1:])

    experience = _find_section(sections, ["experience", "professional experience", "work experience"])
    original_skills = _find_section(sections, ["technical skills", "skills", "core skills"])
    education = _find_section(sections, ["education"])
    certifications = _find_section(sections, ["certification", "certifications"])
    skills_body = _clean_resume_section_body(original_skills) if original_skills.strip() else ", ".join(skills)

    experience_lines: list[str] = []
    original_lines = [line.strip() for line in _clean_resume_section_body(experience).splitlines() if line.strip()]
    inserted_tailored = False
    tailored_insertions = _select_tailored_insertions(bullets, _bullet_items(original_lines), limit=2)
    tailored_set = {bullet.lower() for bullet in tailored_insertions}
    for line in original_lines:
        if line.startswith("- ") and not inserted_tailored and tailored_insertions:
            experience_lines.extend([f"- {bullet}" for bullet in tailored_insertions])
            inserted_tailored = True
        if line.startswith("- "):
            clean = line[2:].strip()
            if clean and clean.lower() not in tailored_set:
                experience_lines.append("- " + clean)
        else:
            experience_lines.append(line)
    if not inserted_tailored:
        experience_lines.extend([f"- {bullet}" for bullet in tailored_insertions])

    final_sections = [
        header.strip(),
        "# Summary\n" + summary.strip(),
        "# Technical Skills\n" + skills_body,
        "# Professional Experience\n" + "\n".join(experience_lines).strip(),
        "# Education\n" + _clean_resume_section_body(education),
        "# Certifications\n" + _clean_resume_section_body(certifications),
    ]

    final_markdown = "\n\n".join(section.strip() for section in final_sections if section.strip())
    _validate_final_resume_markdown(final_markdown)
    return final_markdown


def _extract_name_and_contact(header: str) -> tuple[str, str]:
    lines = [line.strip() for line in header.splitlines() if line.strip()]
    if not lines:
        return "Resume", ""
    name = lines[0].lstrip("#").strip()
    contact = " | ".join(line.lstrip("#").strip() for line in lines[1:])
    return name or "Resume", contact


def _bullet_items(lines: list[str]) -> list[str]:
    return [line[2:].strip() for line in lines if line.strip().startswith("- ")]


def _trusted_latex_bullet(text: str) -> str:
    return TRUSTED_LATEX_BULLET_PREFIX + text


def _is_trusted_latex_bullet(text: str) -> bool:
    return text.startswith(TRUSTED_LATEX_BULLET_PREFIX)


def _bullet_text(text: str) -> str:
    return text[len(TRUSTED_LATEX_BULLET_PREFIX):] if _is_trusted_latex_bullet(text) else text


def _is_strong_original_bullet(bullet: str) -> bool:
    lowered = _bullet_text(bullet).lower()
    return bool(
        re.search(r"\b\d+(?:\.\d+)?\s*(?:%|k|m|gb|tb|ms|sec|/day|events/sec|x)\b", lowered)
        or re.search(r"\b\d+(?:\.\d+)?\s*(?:percent|uptime|latency|reduction|improvement)\b", lowered)
        or any(
            term in lowered
            for term in [
                "architecture", "production", "ci/cd", "pipeline", "data pipeline", "uptime",
                "latency", "throughput", "optimized", "performance", "scale", "events/sec",
                "800gb", "150k", "99.15",
            ]
        )
    )


def _normalize_bullet_key(bullet: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _bullet_text(bullet).lower()).strip()


def _select_tailored_insertions(tailored_bullets: list[str], original_bullets: list[str], limit: int = 2) -> list[str]:
    original_keys = {_normalize_bullet_key(bullet) for bullet in original_bullets}
    selected: list[str] = []
    for bullet in tailored_bullets:
        key = _normalize_bullet_key(bullet)
        if not key or key in original_keys or key in {_normalize_bullet_key(item) for item in selected}:
            continue
        if any(key in original_key or original_key in key for original_key in original_keys if len(original_key) > 30):
            continue
        selected.append(bullet)
        if len(selected) >= limit:
            break
    return selected


def _split_experience_bullets_by_role(original_experience: str) -> tuple[list[str], list[str], list[str]]:
    azure: list[str] = []
    aws: list[str] = []
    other: list[str] = []
    current_role = "other"
    for raw in original_experience.splitlines():
        line = raw.strip()
        lowered = line.lower()
        if not line:
            continue
        if not line.startswith("- "):
            if any(term in lowered for term in ["azure", "app orchid", "synapse", "data factory"]):
                current_role = "azure"
            elif any(term in lowered for term in ["aws", "chakravuyha", "s3", "glue", "redshift"]):
                current_role = "aws"
            if not line.startswith((r"\item", r"\resumeItem")):
                continue
        if line.startswith("- "):
            bullet = line[2:].strip()
        elif line.startswith(r"\item"):
            bullet = line[len(r"\item"):].strip()
        elif line.startswith(r"\resumeItem"):
            match = re.match(r"\\resumeItem\{(.+)\}\s*$", line)
            bullet = match.group(1).strip() if match else ""
        else:
            continue
        bullet = re.sub(r"\s*\\\\\s*$", "", bullet).strip()
        if not bullet:
            continue
        if line.startswith((r"\item", r"\resumeItem")):
            bullet = _trusted_latex_bullet(bullet)
        if current_role == "azure" or any(term in lowered for term in ["azure", "synapse", "data factory", "databricks"]):
            azure.append(bullet)
        elif current_role == "aws" or any(term in lowered for term in ["aws", "s3", "glue", "lambda", "emr", "redshift"]):
            aws.append(bullet)
        else:
            other.append(bullet)
    return azure, aws, other


def _merge_preserved_and_tailored(original_bullets: list[str], tailored_bullets: list[str], limit: int = 1) -> list[str]:
    insertions = _select_tailored_insertions(tailored_bullets, original_bullets, limit=limit)
    if not original_bullets:
        return insertions
    if not insertions:
        return original_bullets
    return original_bullets[:1] + insertions + original_bullets[1:]


def _dedupe_bullets(bullets: list[str], seen: set[str]) -> list[str]:
    deduped: list[str] = []
    for bullet in bullets:
        key = _normalize_bullet_key(bullet)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(bullet)
    return deduped


def _split_bullets_for_template(bullets: list[str], original_experience: str) -> tuple[list[str], list[str], list[str]]:
    original_azure, original_aws, original_other = _split_experience_bullets_by_role(original_experience)
    tailored_azure: list[str] = []
    tailored_aws: list[str] = []
    tailored_other: list[str] = []
    for bullet in bullets:
        lowered = bullet.lower()
        if any(term in lowered for term in ["azure", "synapse", "data factory", "databricks"]):
            tailored_azure.append(bullet)
        elif any(term in lowered for term in ["aws", "s3", "glue", "lambda", "emr", "redshift"]):
            tailored_aws.append(bullet)
        else:
            tailored_other.append(bullet)

    seen: set[str] = set()
    azure = _dedupe_bullets(_merge_preserved_and_tailored(original_azure, tailored_azure, limit=1), seen)
    aws = _dedupe_bullets(_merge_preserved_and_tailored(original_aws, tailored_aws, limit=1), seen)
    other = _dedupe_bullets(_merge_preserved_and_tailored(original_other, tailored_other, limit=1), seen)
    return azure, aws, other


def _items_to_latex(bullets: list[str]) -> str:
    lines: list[str] = []
    for bullet in bullets:
        if _is_trusted_latex_bullet(bullet):
            lines.append(f"\\item {_bullet_text(bullet)}")
        else:
            lines.append(f"\\item {_latex_escape(bullet)}")
    return "\n".join(lines)


def _latex_to_plain_text(text: str) -> str:
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\$": "$",
        r"\#": "#",
        r"\_": "_",
        r"\{": "{",
        r"\}": "}",
    }
    for latex, plain in replacements.items():
        text = text.replace(latex, plain)
    return text.strip()


def _strip_skill_line_markup(line: str) -> str:
    line = re.sub(r"%.*$", "", line).strip()
    line = re.sub(r"^\\item\s+", "", line).strip()
    line = line.lstrip("-").strip()
    line = re.sub(r"\\\\\s*$", "", line).strip()
    return line


def _extract_structured_skills(skills_section: str) -> list[tuple[str | None, str]]:
    entries: list[tuple[str | None, str]] = []
    for raw in skills_section.splitlines():
        line = _strip_skill_line_markup(raw)
        if line.startswith("\\") and not line.startswith((r"\textbf", r"\item")):
            continue
        if not line:
            continue
        label = None
        value = line
        match = (
            re.match(r"^\\textbf\{([^{}:]+)\s*:\s*\}\s*(.+)$", line)
            or re.match(r"^\\textbf\{([^{}]+?)\}\s*:?\s*(.+)$", line)
            or re.match(r"^\*\*([^*:]+)\s*:\s*\*\*\s*(.+)$", line)
            or re.match(r"^\*\*([^*]+?)\*\*\s*:?\s*(.+)$", line)
            or re.match(r"^([^:]+)\s*:\s*(.+)$", line)
        )
        if match:
            label = _latex_to_plain_text(match.group(1).strip().rstrip(":"))
            value = _latex_to_plain_text(match.group(2).strip())
        entries.append((label, value))
    return entries


def _split_skill_items(value: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    depth = 0
    index = 0
    while index < len(value):
        char = value[index]
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1

        if char == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        elif value.startswith(r"\textbar{}", index) or value.startswith(r"\|", index):
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
            index += len(r"\textbar{}") - 1 if value.startswith(r"\textbar{}", index) else len(r"\|") - 1
        else:
            current.append(char)
        index += 1

    item = "".join(current).strip()
    if item:
        items.append(item)
    return items


def _skill_priority_index(item: str, priority: list[str]) -> int:
    normalized_item = normalize_skill(item).lower()
    for index, skill in enumerate(priority):
        if normalized_item == skill or skill in normalized_item:
            return index
    return len(priority)


def _skills_to_latex(skills: list[str], original_skills_section: str) -> str:
    structured = _extract_structured_skills(original_skills_section)
    if not structured:
        return _default_structured_skills_to_latex(skills)

    priority = [normalize_skill(skill).lower() for skill in skills]
    lines: list[str] = []
    for label, value in structured:
        parts = _split_skill_items(value)
        if parts:
            parts = sorted(
                parts,
                key=lambda item: _skill_priority_index(item, priority),
            )
            value = ", ".join(parts)
        escaped_value = _latex_escape(value)
        if label:
            lines.append(f"\\textbf{{{_latex_escape(label)}:}} {escaped_value} \\\\")
        else:
            lines.append(f"{escaped_value} \\\\")
    return "\n".join(lines)


def _default_structured_skills_to_latex(skills: list[str]) -> str:
    category_keywords = {
        "Programming Languages": ["python", "sql", "spark sql", "scala", "java"],
        "Cloud Platforms": ["aws", "azure", "gcp"],
        "AWS Services": ["s3", "glue", "lambda", "emr", "redshift", "cloudwatch"],
        "Azure Services": ["data factory", "adf", "synapse", "databricks"],
        "Data Processing & Streaming": ["spark", "pyspark", "kafka", "streaming"],
        "Data Orchestration": ["airflow", "dag", "orchestration"],
        "Data Warehousing": ["snowflake", "data warehouse", "warehouse", "redshift", "synapse"],
        "Databases": ["postgres", "mysql", "sql server", "database"],
        "Infrastructure & DevOps": ["terraform", "docker", "kubernetes", "ci/cd", "devops"],
        "Data Quality & Monitoring": ["data quality", "great expectations", "monitoring"],
        "BI & Analytics Tools": ["power bi", "tableau", "looker", "visualization"],
    }
    assigned: set[str] = set()
    lines: list[str] = []
    for category, keywords in category_keywords.items():
        category_skills = [
            skill for skill in skills
            if skill not in assigned and any(keyword in skill.lower() for keyword in keywords)
        ]
        if category_skills:
            assigned.update(category_skills)
            lines.append(f"\\textbf{{{_latex_escape(category)}:}} {_latex_escape(', '.join(category_skills))} \\\\")
    remaining = [skill for skill in skills if skill not in assigned]
    if remaining:
        lines.append(f"\\textbf{{Other:}} {_latex_escape(', '.join(remaining))} \\\\")
    return "\n".join(lines)


def _extract_latex_section_body(template: str, section_names: list[str]) -> str:
    names = "|".join(re.escape(name) for name in section_names)
    pattern = re.compile(
        rf"\\section\*?\{{(?:{names})\}}\s*(.*?)(?=\\section\*?\{{|\\end\{{document\}})",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(template)
    if not match:
        return ""
    body = match.group(1).strip()
    return "" if "{{" in body and "}}" in body else body


def _best_skills_source(resume_skills: str, template_skills: str) -> str:
    if _extract_structured_skills(resume_skills):
        return resume_skills
    if _extract_structured_skills(template_skills):
        return template_skills
    return resume_skills


def _replace_experience_bullets(template: str, bullets_latex: str) -> str:
    section_pattern = re.compile(
        r"(\\section\*?\{(?:Professional Experience|Experience|Work Experience)\}.*?\\begin\{itemize\})(.*?)(\\end\{itemize\})",
        re.IGNORECASE | re.DOTALL,
    )
    return section_pattern.sub(lambda match: match.group(1) + "\n" + bullets_latex.strip() + "\n" + match.group(3), template, count=1)


def _render_latex_template(
    template: str,
    resume: str,
    summary: str,
    skills: list[str],
    bullets: list[str],
    source_template: str | None = None,
) -> str:
    header, sections = _section_map(resume)
    name, contact = _extract_name_and_contact(header)
    experience = _find_section(sections, ["experience", "professional experience", "work experience"])
    resume_skills = _find_section(sections, ["technical skills", "skills", "core skills"])
    content_template = source_template if source_template and source_template.strip() else template
    template_skills = _extract_latex_section_body(content_template, ["Technical Skills", "Skills", "Core Skills"])
    original_skills = _best_skills_source(resume_skills, template_skills)
    if not experience.strip():
        experience = _extract_latex_section_body(content_template, ["Professional Experience", "Experience", "Work Experience"])
    education = _find_section(sections, ["education"])
    certifications = _find_section(sections, ["certification", "certifications"])
    azure_bullets, aws_bullets, other_bullets = _split_bullets_for_template(bullets, experience)
    skills_latex = _skills_to_latex(skills, original_skills)

    preserved_titles = {
        "summary", "skills", "technical skills", "core skills", "experience", "professional experience",
        "work experience", "education", "certification", "certifications"
    }
    additional_sections = "\n\n".join(
        _latex_section(title.title(), body)
        for title, body in sections.items()
        if title not in preserved_titles and body
    )

    replacements = {
        "{{NAME}}": _latex_escape(name),
        "{{CONTACT_LINE}}": _latex_escape(contact),
        "{{SUMMARY}}": _latex_escape(summary),
        "{{TECHNICAL_SKILLS}}": skills_latex,
        "{{AZURE_BULLETS}}": _items_to_latex(azure_bullets),
        "{{AWS_BULLETS}}": _items_to_latex(aws_bullets),
        "{{OTHER_BULLETS}}": _items_to_latex(other_bullets),
        "{{EDUCATION_SECTION}}": _latex_section("Education", education),
        "{{CERTIFICATIONS_SECTION}}": _latex_section("Certifications", certifications),
        "{{ADDITIONAL_SECTIONS}}": additional_sections,
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def _load_selected_template(template_name: str | None) -> tuple[str, str]:
    normalized = (template_name or "classic").strip().lower().replace(" ", "_").replace("-", "_")
    warning = ""
    if normalized not in TEMPLATE_FILES:
        normalized = "classic"
        warning = "Selected resume template was unavailable. Falling back to Classic."
    filename = TEMPLATE_FILES[normalized]
    path = TEMPLATE_DIR / filename
    if not path.exists():
        path = TEMPLATE_DIR / TEMPLATE_FILES["classic"]
        warning = "Selected resume template was missing. Falling back to Classic."
    return path.read_text(encoding="utf-8"), warning


def _build_template_latex(
    resume: str,
    summary: str,
    skills: list[str],
    bullets: list[str],
    original_latex_template: str | None = None,
    resume_template: str | None = "classic",
) -> tuple[str, str]:
    template, warning = _load_selected_template("classic")
    required_placeholders = ["{{SUMMARY}}", "{{TECHNICAL_SKILLS}}", "{{AZURE_BULLETS}}", "{{AWS_BULLETS}}"]
    missing = [placeholder for placeholder in required_placeholders if placeholder not in template]
    if missing:
        warning = "Classic resume template is missing required placeholders: " + ", ".join(missing)
    source_template = original_latex_template if original_latex_template and original_latex_template.strip() else None
    return _render_latex_template(template, resume, summary, skills, bullets, source_template=source_template), warning


def _resume_supports_skill(skill: str, resume_lower: str) -> bool:
    lowered = skill.lower()
    if len(lowered) <= 3:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(lowered)}(?![a-z0-9])", resume_lower))
    return lowered in resume_lower


def _fallback_tailor_resume(
    resume: str,
    jd: str,
    classification: Classification,
    keywords: KeywordAnalysis,
    match: ResumeMatch,
    target_style: str,
    original_latex_template: str | None = None,
    resume_template: str | None = "classic",
) -> TailoredResume:
    style = target_style.lower()
    resume_lower = resume.lower()
    supported_clouds = [tool for tool in ["AWS", "Azure", "GCP"] if tool.lower() in resume_lower]
    cloud_phrase = " and ".join(supported_clouds) if supported_clouds else "cloud data platforms"
    supported_jd_terms = []
    for term in keywords.must_have + keywords.important + keywords.bonus + keywords.tools:
        normalized = normalize_skill(term)
        if _resume_supports_skill(term, resume_lower) or _resume_supports_skill(normalized, resume_lower):
            supported_jd_terms.append(normalized)
        elif normalized in {"Data Pipelines", "Data Warehouse", "API-based Data Integration", "BI / Visualization"}:
            supported_jd_terms.append(normalized)
    domain = classification.business_domain.lower()
    confident_domain = classification.confidence >= 0.75
    if confident_domain and ("construction" in domain or "industrial" in domain):
        summary = (
            f"Data Engineer with experience building operational reporting pipelines, API-based integrations, "
            f"and warehouse-ready datasets across {cloud_phrase}. Strong background in SQL, Python, data modeling, "
            "and analytics enablement for project performance reporting, operational KPIs, and cross-functional decision support."
        )
        bullets = [
            "Built API-based ingestion workflows that bring enterprise system data into analytics-ready warehouse datasets for operational reporting.",
            "Modeled SQL datasets and reporting layers that support project performance dashboards, KPI visibility, and stakeholder decision-making.",
            "Improved pipeline reliability with validation checks, retry logic, monitoring, and production support practices across cloud data workflows.",
            "Partnered with business analysts and technical stakeholders to translate operational reporting requirements into governed data models.",
        ]
    elif confident_domain and ("fintech" in style or "fintech" in domain):
        summary = (
            f"Data Engineer with experience building reliable data pipelines, warehouse models, and analytics-ready "
            f"datasets across {cloud_phrase}. Strong focus on data trust, validation, query optimization, and scalable "
            "warehouse operations that support business-critical reporting."
        )
        bullets = [
            "Built and maintained data pipelines with validation checks to improve trust in downstream analytics and operational reporting.",
            "Modeled warehouse datasets for reliable financial, customer, or business metrics while preserving source-to-report traceability.",
            "Improved SQL performance and data reliability through query tuning, partitioning, monitoring, and production support practices.",
            "Partnered with stakeholders to translate business-critical reporting needs into governed, reusable analytics datasets.",
        ]
    elif confident_domain and ("consult" in style or "consult" in domain):
        summary = (
            "Data Engineer with experience designing cloud-based data pipelines, data integration workflows, "
            f"and analytics-ready data platforms across {cloud_phrase}. Strong background in ETL/ELT development, data modeling, "
            "data quality, and cloud architecture, with experience collaborating with technical and business stakeholders to deliver "
            "reliable enterprise data solutions."
        )
        bullets = [
            f"Designed and maintained scalable ETL/ELT pipelines across {cloud_phrase} to support enterprise analytics and reporting requirements.",
            "Collaborated with business and technical stakeholders to translate data requirements into reliable data integration and transformation workflows.",
            "Developed SQL-based data models and optimized analytical workloads through partitioning, indexing, and dimensional modeling techniques.",
            "Implemented data validation and quality checks to improve reliability, consistency, and trust across downstream reporting datasets.",
            "Contributed to cloud data architecture decisions involving scalable storage, orchestration, monitoring, and production deployment practices."
        ]
    elif confident_domain and ("saas" in style or "saas" in domain):
        summary = f"Data Engineer with experience building ETL/ELT pipelines, API integrations, and warehouse-ready datasets for SaaS analytics and business operations across {cloud_phrase}."
        bullets = [
            "Built API-based ingestion workflows integrating external and internal systems into cloud data platforms.",
            "Designed SQL data models and standardized business metrics for consistent SaaS reporting and stakeholder enablement.",
            "Improved pipeline reliability through validation checks, monitoring, schema handling, and error-handling logic."
        ]
    elif confident_domain and ("ad-tech" in domain or "media" in domain):
        summary = f"Data Engineer with experience building analytics pipelines, warehouse models, and reporting datasets for campaign, audience, or product analytics across {cloud_phrase}."
        bullets = [
            "Built analytics-ready pipelines that convert raw event and business data into reliable reporting datasets.",
            "Designed SQL models supporting performance measurement, stakeholder reporting, and reusable metric definitions.",
            "Improved data quality and delivery reliability through validation, monitoring, and production support practices.",
        ]
    else:
        summary = f"Data Engineer with experience building data pipelines, integration workflows, warehouse models, and analytics systems across {cloud_phrase}."
        bullets = [
            "Built cloud data pipelines supporting analytics, reporting, and stakeholder-facing datasets.",
            "Optimized SQL-based analytical models and improved query performance.",
            "Implemented validation and monitoring practices to improve data reliability."
        ]

    resume_supported_defaults = [
        normalize_skill(term)
        for term in ["AWS", "Azure", "GCP", "Python", "SQL", "ETL", "ELT", "Data Modeling", "Airflow", "Spark", "Data Quality"]
        if term.lower() in resume_lower
    ]
    jd_weighted_order = [
        "SQL", "Python", "Azure", "AWS", "Snowflake", "Azure Data Factory", "BI / Visualization",
        "API-based Data Integration", "Data Modeling", "Data Warehouse", "Data Pipelines", "Data Quality",
        "Query Optimization", "Stakeholder Collaboration", "Spark", "Airflow"
    ]
    skills = []
    for skill in jd_weighted_order + supported_jd_terms + resume_supported_defaults:
        if skill not in skills and (_resume_supports_skill(skill, resume_lower) or skill in supported_jd_terms or skill in {"BI / Visualization", "API-based Data Integration", "Data Warehouse", "Data Pipelines"}):
            skills.append(skill)
    skills = skills[:16]
    if not skills:
        skills = ["Data Engineering", "Data Pipelines", "Data Quality"]
    final = _build_full_resume_markdown(resume, summary, skills, bullets)
    if _env_bool("PRESERVE_ORIGINAL_LATEX_TEMPLATE", True):
        latex, template_warning = _build_template_latex(resume, summary, skills, bullets, original_latex_template, resume_template)
    else:
        latex = _build_full_latex(final)
        template_warning = ""

    return TailoredResume(
        revised_summary=summary,
        revised_skills=skills,
        rewritten_bullets=bullets,
        final_resume_markdown=final,
        final_resume_latex=latex,
        template_warning=template_warning,
        confidence=0.68,
        evidence=match.strong_matches[:8],
    )


def tailor_resume(
    resume: str,
    jd: str,
    classification: Classification,
    keywords: KeywordAnalysis,
    match: ResumeMatch,
    guardrails: GuardrailReport,
    target_style: str,
    original_latex_template: str | None = None,
    resume_template: str | None = "classic",
) -> TailoredResume:
    fallback = _fallback_tailor_resume(resume, jd, classification, keywords, match, target_style, original_latex_template, resume_template)
    generated = llm_client.generate(
        schema=TailoredResume,
        fallback=fallback,
        route="resume_tailor",
        system_prompt=(
            "PROMPT_VERSION=v2. You are the Resume Tailor Agent. Tailor the resume with strategic recruiter-aware "
            "positioning while preserving truthfulness. Do not merely paraphrase ATS keywords. Reposition supported "
            "experience around the JD's domain priorities: FinTech trust/reliability/SLAs/financial integrity, "
            "Construction/Industrial operational analytics/project workflows/cost forecasting/resource planning/ERP integrations, "
            "Consulting governance/stakeholders/architecture strategy/transformation, SaaS APIs/integrations/warehouse "
            "operations, and Ad-Tech campaign measurement/attribution/analytics enablement. Use domain terms only when "
            "classifier confidence supports them; otherwise use neutral operational analytics language. Avoid vague skills "
            "like 'performance'; prefer Query Optimization, Data Reliability, Data Warehousing, and Schema Design. "
            "Return a complete final resume, not just suggestions. Preserve the original resume's contact info, experience "
            "roles, education, certifications, and any truthful unchanged sections. Replace only the summary, skills ordering, "
            "and weak or irrelevant bullets. Preserve strong quantified bullets, architecture details, production scale, "
            "performance improvements, uptime, throughput, and CI/CD evidence by default. Tailoring priority is truthfulness, "
            "then quantified evidence, then recruiter alignment, then keyword insertion. Never add unsupported JD tools or "
            "invented credentials. When producing LaTeX, preserve the original resume template structure, itemize options, "
            "skill category formatting, spacing, and section formatting; do not invent a new generic template."
        ),
        user_prompt=(
            "Create a tailored resume draft. Return a revised summary, revised skills, rewritten bullets, "
            "a complete final_resume_markdown, complete final_resume_latex, confidence, and evidence. The final resume must include "
            "the candidate header/contact info from the master resume, tailored Summary, Technical Skills, Professional Experience, "
            "Education, and Certifications when those sections exist in the master resume. The LaTeX should be compilable as a small "
            "ATS-friendly one-column article document and preserve the original LaTeX resume template structure when available. "
            "Do not regenerate complete experience sections from scratch. Keep strong original bullets, especially quantified "
            "achievements such as throughput, data volume, uptime, latency reduction, performance improvements, production "
            "architecture, and CI/CD improvements. Add only 1-2 JD-aware bullets when they are truthful and improve role alignment. "
            "Preserve structured skills categories such as Programming Languages, Cloud Platforms, AWS Services, and Azure Services. "
            "Respect the guardrails strictly. Use semantic "
            "adaptation: emphasize resume-backed adjacent strengths rather than inserting unsupported tools or metrics.\n\n"
            f"TARGET STYLE:\n{target_style}\n\n"
            f"JOB DESCRIPTION:\n{jd}\n\n"
            f"CLASSIFICATION:\n{classification.model_dump_json()}\n\n"
            f"KEYWORDS:\n{keywords.model_dump_json()}\n\n"
            f"MATCH REPORT:\n{match.model_dump_json()}\n\n"
            f"TRUTHFULNESS GUARDRAILS:\n{guardrails.model_dump_json()}\n\n"
            f"SELECTED RESUME TEMPLATE:\n{resume_template or 'classic'}\n\n"
            f"ORIGINAL LATEX TEMPLATE:\n{original_latex_template or 'Not provided'}\n\n"
            f"MASTER RESUME:\n{resume}"
        ),
    )
    final_markdown = _build_full_resume_markdown(
        resume,
        generated.revised_summary,
        generated.revised_skills,
        generated.rewritten_bullets,
    )
    if _env_bool("PRESERVE_ORIGINAL_LATEX_TEMPLATE", True):
        final_latex, template_warning = _build_template_latex(
            resume,
            generated.revised_summary,
            generated.revised_skills,
            generated.rewritten_bullets,
            original_latex_template,
            resume_template,
        )
        return generated.model_copy(update={
            "final_resume_markdown": final_markdown,
            "final_resume_latex": final_latex,
            "template_warning": template_warning,
        })
    return generated.model_copy(update={
        "final_resume_markdown": final_markdown,
        "final_resume_latex": _build_full_latex(final_markdown),
    })
