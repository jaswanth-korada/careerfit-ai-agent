import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

schemas = types.ModuleType("schemas")
analysis_schema = types.ModuleType("schemas.analysis_schema")
for name in ["GuardrailReport", "TailoredResume", "Classification", "KeywordAnalysis", "ResumeMatch"]:
    setattr(analysis_schema, name, type(name, (), {}))
sys.modules.setdefault("schemas", schemas)
sys.modules.setdefault("schemas.analysis_schema", analysis_schema)

services = types.ModuleType("services")
llm_client = types.ModuleType("services.llm_client")
llm_client.llm_client = None
semantic_matching = types.ModuleType("services.semantic_matching")
semantic_matching.normalize_skill = lambda text: " ".join(str(text).replace("/", " ").replace("-", " ").lower().split())
sys.modules.setdefault("services", services)
sys.modules.setdefault("services.llm_client", llm_client)
sys.modules.setdefault("services.semantic_matching", semantic_matching)

from agents.resume_tailor_agent import _load_selected_template, _render_latex_template


class LatexRenderingRegressionTests(unittest.TestCase):
    def test_classic_template_preserves_resume_structure_and_latex_math(self):
        classic, _ = _load_selected_template("classic")
        original_latex = r"""
\documentclass{article}
\begin{document}
\section*{Technical Skills}
\textbf{Programming Languages:} Python (PySpark, Pandas, NumPy), SQL, Spark SQL, Scala \\
\textbf{Cloud Platforms:} AWS, Azure \\
\textbf{Azure Services:} Azure Data Factory, Azure Databricks, Azure Synapse \\
\section*{Professional Experience}
\textbf{Azure Data Engineer}
\begin{itemize}[leftmargin=1.5em, itemsep=-0.3em, topsep=0em]
\item Architected 5 ELT pipelines (800GB+/day) using Azure Data Factory \& Databricks, improving availability to 99.15\%.
\item Optimized Azure Synapse queries (950ms $\rightarrow$ 640ms), reducing latency 33\%.
\item Built Spark Structured Streaming pipelines ingesting 150K events/second from Kafka.
\item Increased model refresh cadence from 2x/month $\rightarrow$ 3x/week.
\end{itemize}
\textbf{AWS Data Engineer}
\begin{itemize}[leftmargin=1.5em, itemsep=-0.3em, topsep=0em]
\item Processed 4TB/month across AWS Glue, S3, and Redshift pipelines.
\item Reduced incremental warehouse footprint (3TB $\rightarrow$ 850GB) through partitioning.
\item Improved operational throughput by 7.5x with EMR and Lambda automation.
\end{itemize}
\end{document}
"""

        rendered = _render_latex_template(
            classic,
            "# Jaswanth Korada\ncontact",
            "TEST TAILORED SUMMARY",
            ["SQL", "Python", "Azure Data Factory"],
            ["Generated Azure bullet should not replace original quantified bullets."],
            source_template=original_latex,
        )

        self.assertTrue(rendered.startswith(r"\documentclass{article}"))
        self.assertFalse(rendered.startswith("documentclass{article}"))
        self.assertIn("TEST TAILORED SUMMARY", rendered)

        self.assertIn(r"\textbf{Programming Languages:}", rendered)
        self.assertIn(r"\textbf{Cloud Platforms:}", rendered)
        self.assertIn(r"\textbf{Azure Services:}", rendered)
        self.assertNotIn("\nSQL, Python, Azure Data Factory\n", rendered)

        for expected in ["800GB+/day", "150K events/second", "99.15", "33", "7.5x", "4TB/month"]:
            self.assertIn(expected, rendered)

        self.assertIn(r"\begin{itemize}[leftmargin=1.5em, itemsep=-0.3em, topsep=0em]", rendered)
        self.assertGreaterEqual(rendered.count(r"\item "), 7)

        for arrow_expression in [
            r"(950ms $\rightarrow$ 640ms)",
            r"2x/month $\rightarrow$ 3x/week",
            r"(3TB $\rightarrow$ 850GB)",
        ]:
            self.assertIn(arrow_expression, rendered)

        self.assertNotIn(r"\textbackslash{}rightarrow", rendered)
        self.assertNotIn(r"\$\textbackslash{}rightarrow\$", rendered)


if __name__ == "__main__":
    unittest.main()
