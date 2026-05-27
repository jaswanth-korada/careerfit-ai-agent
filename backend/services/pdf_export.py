import os
import re
import shutil
import subprocess
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger("careerfit.pdf_export")


class LatexCompilerNotFoundError(RuntimeError):
    pass


class LatexCompilationError(RuntimeError):
    pass


def slugify(value: str | None, fallback: str) -> str:
    raw = (value or fallback).strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw or fallback


def safe_resume_filename(candidate_name: str | None, company_name: str | None, role_title: str | None) -> str:
    candidate = slugify(candidate_name, "resume")
    company = slugify(company_name, "company")
    role = slugify(role_title, "role")
    stem = "_".join(part for part in [candidate, company, role] if part)
    stem = stem[:110].strip("_")
    return f"{stem}.pdf"


def latex_to_plain_text(latex: str) -> str:
    text = latex
    text = re.sub(r"\\begin\{center\}|\\end\{center\}", "\n", text)
    text = re.sub(r"\\section\*\{([^}]*)\}", r"\n\1\n", text)
    text = re.sub(r"\\item\s+", "- ", text)
    text = re.sub(r"\\(LARGE|textbf|href)\{([^}]*)\}", r"\2", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", "", text)
    text = text.replace(r"\&", "&").replace(r"\%", "%").replace(r"\_", "_").replace(r"\#", "#")
    text = re.sub(r"[{}]", "", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_line(line: str, max_chars: int = 92) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    words = line.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def write_simple_text_pdf(text: str, output_path: Path) -> None:
    page_width = 612
    page_height = 792
    margin_x = 54
    top_y = 742
    line_height = 14
    pages: list[list[str]] = [[]]
    line_count_limit = 48
    for raw in text.splitlines():
        wrapped = _wrap_line(raw)
        if not wrapped:
            wrapped = [""]
        for line in wrapped:
            if len(pages[-1]) >= line_count_limit:
                pages.append([])
            pages[-1].append(line)

    objects: list[str] = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
    for page_index, page_lines in enumerate(pages):
        page_obj_id = 3 + page_index * 2
        content_obj_id = page_obj_id + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {content_obj_id} 0 R >>"
        )
        commands = ["BT", "/F1 10 Tf", f"{margin_x} {top_y} Td"]
        for index, line in enumerate(page_lines):
            if index > 0:
                commands.append(f"0 -{line_height} Td")
            commands.append(f"({_pdf_escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands)
        objects.append(f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj_id, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{obj_id} 0 obj\n{obj}\nendobj\n".encode("latin-1", errors="replace"))
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    output_path.write_bytes(pdf)


def _looks_like_latex_template(content: str) -> bool:
    return bool(
        re.search(r"\\documentclass(?:\[[^\]]*\])?\{", content)
        or "\\begin{document}" in content
        or "\\usepackage" in content
    )


def compile_latex_or_fallback(
    final_resume_latex: str,
    output_dir: Path,
    filename: str,
    allow_plain_text_fallback: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    is_latex_template = _looks_like_latex_template(final_resume_latex)
    pdflatex = shutil.which("pdflatex")

    if is_latex_template and not pdflatex:
        logger.error("[pdf-export] renderer=pdflatex status=missing filename=%s", filename)
        raise LatexCompilerNotFoundError(
            "LaTeX compiler not found. Download the LaTeX file or install MiKTeX to generate PDF."
        )

    if pdflatex and is_latex_template:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tex_path = tmp_path / "resume.tex"
            tex_path.write_text(final_resume_latex, encoding="utf-8")
            result = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            pdf_path = tmp_path / "resume.pdf"
            if result.returncode == 0 and pdf_path.exists():
                shutil.copyfile(pdf_path, output_path)
                logger.info("[pdf-export] renderer=pdflatex status=success filename=%s", filename)
                return output_path
            logger.error(
                "[pdf-export] renderer=pdflatex status=failed filename=%s returncode=%s stderr=%s stdout_tail=%s",
                filename,
                result.returncode,
                result.stderr[-1000:],
                result.stdout[-1000:],
            )
            raise LatexCompilationError("LaTeX compilation failed. Download the LaTeX file and check the compiler log.")

    if is_latex_template and not allow_plain_text_fallback:
        logger.error("[pdf-export] renderer=fallback_text status=blocked_for_latex filename=%s", filename)
        raise LatexCompilationError("LaTeX compilation failed. Download the LaTeX file and check the compiler log.")

    logger.info("[pdf-export] renderer=fallback_text status=success filename=%s", filename)
    plain_text = latex_to_plain_text(final_resume_latex)
    write_simple_text_pdf(plain_text, output_path)
    return output_path
