import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.pdf_export import LatexCompilerNotFoundError, compile_latex_or_fallback


class PdfExportTests(unittest.TestCase):
    def test_template_latex_requires_pdflatex(self):
        latex = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"
        with tempfile.TemporaryDirectory() as tmp:
            with patch("services.pdf_export.shutil.which", return_value=None):
                with self.assertRaisesRegex(
                    LatexCompilerNotFoundError,
                    "LaTeX compiler not found. Download the LaTeX file or install MiKTeX to generate PDF.",
                ):
                    compile_latex_or_fallback(latex, Path(tmp), "resume.pdf")

    def test_plain_text_fallback_is_allowed_for_non_template_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("services.pdf_export.shutil.which", return_value=None):
                pdf_path = compile_latex_or_fallback("Plain resume text", Path(tmp), "resume.pdf")
        self.assertTrue(pdf_path.name.endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
