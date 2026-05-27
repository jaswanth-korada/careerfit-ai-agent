import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import type { AnalysisRequest, FullAnalysisResponse, SavedAnalysis } from './types';

const API_URL = 'http://127.0.0.1:8000/full-analysis';
const PDF_EXPORT_URL = 'http://127.0.0.1:8000/export-resume-pdf';
const HISTORY_KEY = 'careerfit_recent_analyses';
const DRAFT_KEY = 'careerfit_input_draft';
const resumeTemplates = [
  ['classic', 'Classic'] as const,
  ['ats_clean', 'ATS Clean'] as const,
  ['modern', 'Modern'] as const,
  ['compact', 'Compact'] as const,
  ['enterprise', 'Enterprise'] as const,
];

const tabs = [
  'JD Classification',
  'ATS Keywords',
  'Resume Match',
  'Truthfulness Guardrails',
  'Tailored Resume',
  'Interview Prep',
  'Hiring Manager Verdict',
] as const;

type TabName = (typeof tabs)[number];

function list(items: string[] | null | undefined): string[] {
  return Array.isArray(items) ? items.filter(Boolean) : [];
}

function text(value: string | null | undefined, fallback = 'Not provided'): string {
  return value && value.trim() ? value : fallback;
}

function score(value: number | null | undefined): number {
  return Math.max(0, Math.min(100, Math.round(Number(value ?? 0))));
}

function confidence(value: number | null | undefined): number {
  return Math.max(0, Math.min(100, Math.round(Number(value ?? 0) * 100)));
}

function downloadFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function slug(value: string, fallback: string): string {
  const safe = value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').replace(/_+/g, '_');
  return safe || fallback;
}

function candidateNameFromResume(markdown: string, fallback = 'resume'): string {
  const firstLine = markdown.split('\n').find(line => line.trim().startsWith('# '));
  return firstLine?.replace(/^#\s+/, '').trim() || fallback;
}

function pdfFilename(candidate: string, company: string, role: string): string {
  return `${slug(candidate, 'resume')}_${slug(company, 'company')}_${slug(role, 'role')}`.slice(0, 110).replace(/_+$/g, '') + '.pdf';
}

async function readErrorResponse(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') || '';
  try {
    if (contentType.includes('application/json')) {
      const body = await response.json();
      if (typeof body?.detail === 'string') return body.detail;
      if (Array.isArray(body?.detail)) return body.detail.map((item: unknown) => JSON.stringify(item)).join('\n');
      return JSON.stringify(body);
    }
    return await response.text();
  } catch {
    return '';
  }
}

async function copyText(content: string, onCopied: (label: string) => void, label: string) {
  if (!content.trim()) return;
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(content);
  } else {
    const textarea = document.createElement('textarea');
    textarea.value = content;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  }
  onCopied(label);
}

function readHistory(): SavedAnalysis[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function Pill({ children }: { children: React.ReactNode }) {
  return <span className="pill">{children}</span>;
}

function Empty({ label = 'No data returned for this section.' }: { label?: string }) {
  return <p className="empty">{label}</p>;
}

function ListCard({ title, items }: { title: string; items?: string[] }) {
  const safeItems = list(items);
  return (
    <article className="card panel">
      <h3>{title}</h3>
      {safeItems.length ? (
        <ul>{safeItems.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
      ) : (
        <Empty />
      )}
    </article>
  );
}

function EvidenceCard({ title, evidence }: { title: string; evidence?: string[] }) {
  const safeEvidence = list(evidence);
  return (
    <article className="card panel evidence-card">
      <h3>{title}</h3>
      {safeEvidence.length ? (
        <div className="evidence-list">
          {safeEvidence.map((item, index) => <blockquote key={`${item}-${index}`}>{item}</blockquote>)}
        </div>
      ) : (
        <Empty label="No evidence snippets were returned." />
      )}
    </article>
  );
}

function ConfidenceMeter({ value, label = 'Confidence' }: { value?: number; label?: string }) {
  const pct = confidence(value);
  return (
    <div className="meter" aria-label={`${label}: ${pct}%`}>
      <div className="meter-label">
        <span>{label}</span>
        <strong>{pct}%</strong>
      </div>
      <div className="meter-track"><span style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

function ScoreCard({ label, value, intent = 'normal' }: { label: string; value?: number; intent?: 'normal' | 'risk' }) {
  const pct = score(value);
  return (
    <article className={`score-card ${intent}`}>
      <span>{label}</span>
      <strong>{pct}</strong>
      <div className="score-track"><span style={{ width: `${pct}%` }} /></div>
    </article>
  );
}

function ToolStack({ stack }: { stack?: Record<string, string[]> }) {
  const entries = Object.entries(stack || {}).filter(([, items]) => list(items).length > 0);
  if (!entries.length) return <Empty label="No tool stack categories were returned." />;
  return (
    <div className="tool-stack">
      {entries.map(([category, items]) => (
        <article className="tool-row" key={category}>
          <strong>{category.split('_').join(' ')}</strong>
          <div className="chips">{list(items).map(item => <Pill key={item}>{item}</Pill>)}</div>
        </article>
      ))}
    </div>
  );
}

function reviewStatus(analysis: FullAnalysisResponse): 'Accepted' | 'Accepted with caution' | 'Human review recommended' {
  const risks = list(analysis.remaining_risks).join(' ').toLowerCase();
  if (risks.includes('human review') || analysis.final_answer_confidence === 'low') {
    return 'Human review recommended';
  }
  if (analysis.quality_checks_passed) {
    return 'Accepted';
  }
  return 'Accepted with caution';
}

function QualityReviewPanel({ analysis }: { analysis: FullAnalysisResponse }) {
  const quality = analysis.quality_scores || {};
  const alt = analysis.alternative_classification;
  const status = reviewStatus(analysis);
  const items = [
    ['Classification', quality.classification_quality],
    ['Semantic match', quality.semantic_match_quality],
    ['Guardrails', quality.guardrail_quality],
    ['Tailoring', quality.tailoring_quality],
    ['Synthesis', quality.synthesis_quality],
    ['Overall quality', quality.overall_quality],
  ] as const;
  return (
    <section className="quality-panel">
      <div>
        <h2>Self-Review</h2>
        <strong className={`review-status ${status === 'Accepted' ? 'accepted' : status === 'Accepted with caution' ? 'caution' : 'review'}`}>{status}</strong>
        <p>{text(analysis.acceptance_explanation, 'No self-review explanation returned.')}</p>
        <div className="chips">
          <Pill>{text(analysis.final_answer_confidence, 'unknown')} final confidence</Pill>
          <Pill>{score(analysis.refinement_rounds)} refinement rounds</Pill>
          <Pill>{status}</Pill>
        </div>
      </div>
      <div className="quality-scores">
        {items.map(([label, value]) => <ScoreCard key={label} label={label} value={value} />)}
      </div>
      {list(analysis.remaining_risks).length > 0 && (
        <div className="remaining-risks">
          <h3>Remaining risks</h3>
          <ul>{list(analysis.remaining_risks).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </div>
      )}
      {alt && (
        <div className="remaining-risks">
          <h3>Alternative classification</h3>
          <div className="chips">
            <Pill>{text(alt.business_domain, 'No alternate business domain')}</Pill>
            <Pill>{text(alt.engineering_domain, 'No alternate engineering domain')}</Pill>
            <Pill>{text(alt.speed_pattern, 'No alternate speed pattern')}</Pill>
            <Pill>{score(alt.disagreement_score)} disagreement</Pill>
          </div>
          <ul>{list(alt.reasons).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
        </div>
      )}
    </section>
  );
}

function LoadingState() {
  return (
    <section className="card loading-state" aria-live="polite">
      <div className="spinner" />
      <div>
        <h2>Running agent workflow</h2>
        <p>Classifying the JD, checking resume evidence, and drafting truthful tailored outputs.</p>
      </div>
    </section>
  );
}

function App() {
  const [jd, setJd] = useState('');
  const [resume, setResume] = useState('');
  const [originalLatexTemplate, setOriginalLatexTemplate] = useState('');
  const [resumeTemplate, setResumeTemplate] = useState('classic');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [style, setStyle] = useState('General');
  const [analysis, setAnalysis] = useState<FullAnalysisResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabName>('JD Classification');
  const [history, setHistory] = useState<SavedAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [error, setError] = useState('');
  const [exportError, setExportError] = useState('');
  const [copied, setCopied] = useState('');

  useEffect(() => {
    setHistory(readHistory());
    try {
      const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}');
      setJd(draft.jd || '');
      setResume(draft.resume || '');
      setOriginalLatexTemplate(draft.originalLatexTemplate || '');
      setResumeTemplate(draft.resumeTemplate || 'classic');
      setCompany(draft.company || '');
      setRole(draft.role || '');
      setStyle(draft.style || 'General');
    } catch {
      // Ignore corrupted browser storage and keep the form usable.
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ jd, resume, originalLatexTemplate, resumeTemplate, company, role, style }));
  }, [jd, resume, originalLatexTemplate, resumeTemplate, company, role, style]);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(''), 1800);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const markdown = analysis?.tailored_resume?.final_resume_markdown || '';
  const latex = analysis?.tailored_resume?.final_resume_latex || '';
  const whyInterested = analysis?.why_interested_answer || '';
  const candidateName = candidateNameFromResume(markdown, 'resume');

  const canRun = jd.trim().length >= 50 && resume.trim().length >= 50 && !loading;

  const scoreItems = useMemo(() => {
    const scores = analysis?.resume_match?.scores || {};
    return [
      ['ATS score', scores.ats_score, 'normal'] as const,
      ['Recruiter readability', scores.recruiter_readability, 'normal'] as const,
      ['Hiring manager trust', scores.hiring_manager_trust, 'normal'] as const,
      ['Technical alignment', scores.technical_alignment, 'normal'] as const,
      ['Interview risk', scores.interview_risk, 'risk'] as const,
      ['Overall match', scores.overall_match, 'normal'] as const,
    ];
  }, [analysis]);

  async function runAnalysis() {
    setLoading(true);
    setError('');
    setCopied('');
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 120000);
    try {
      const payload: AnalysisRequest = {
        job_description: jd.trim(),
        resume: resume.trim(),
        original_latex_template: originalLatexTemplate.trim() || undefined,
        resume_template: resumeTemplate,
        company_name: company.trim() || undefined,
        role_title: role.trim() || undefined,
        target_style: style,
      };
      console.info('Submitting full-analysis request', {
        url: API_URL,
        method: 'POST',
        contentType: 'application/json',
        jdLength: payload.job_description.length,
        resumeLength: payload.resume.length,
      });
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (!res.ok) {
        const detail = await readErrorResponse(res);
        console.error('Full-analysis request failed', {
          status: res.status,
          statusText: res.statusText,
          detail,
        });
        throw new Error(detail || `Backend returned ${res.status} ${res.statusText}`);
      }
      const data: FullAnalysisResponse = await res.json();
      const cryptoWithRandomId = crypto as Crypto & { randomUUID?: () => string };
      const saved: SavedAnalysis = {
        id: cryptoWithRandomId.randomUUID?.() || `${Date.now()}-${Math.random()}`,
        createdAt: new Date().toISOString(),
        companyName: company,
        roleTitle: role,
        targetStyle: style,
        jd,
        resume,
        originalLatexTemplate,
        resumeTemplate,
        analysis: data,
      };
      const nextHistory = [saved, ...history].slice(0, 8);
      setAnalysis(data);
      setActiveTab('JD Classification');
      setHistory(nextHistory);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory));
    } catch (e) {
      console.error('Full-analysis fetch error', e);
      const message = e instanceof DOMException && e.name === 'AbortError'
        ? 'The analysis request timed out before the backend returned a response.'
        : e instanceof Error
          ? e.message
          : 'Something went wrong while running analysis.';
      setError(message);
    } finally {
      window.clearTimeout(timeoutId);
      setLoading(false);
    }
  }

  async function uploadLatexTemplate(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const content = await file.text();
    setOriginalLatexTemplate(content);
    event.target.value = '';
  }

  async function downloadFinalResumePdf() {
    if (!latex.trim()) return;
    setExportingPdf(true);
    setExportError('');
    try {
      const res = await fetch(PDF_EXPORT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          final_resume_latex: latex,
          company_name: company.trim() || undefined,
          role_title: role.trim() || undefined,
          candidate_name: candidateName,
        }),
      });
      if (!res.ok) {
        const detail = await readErrorResponse(res);
        throw new Error(detail || `PDF export failed with ${res.status}`);
      }
      const blob = await res.blob();
      const contentDisposition = res.headers.get('content-disposition') || '';
      const match = contentDisposition.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || pdfFilename(candidateName, company, role);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'PDF export failed. Download LaTeX or Markdown instead.');
    } finally {
      setExportingPdf(false);
    }
  }

  function openSaved(item: SavedAnalysis) {
    setJd(item.jd || '');
    setResume(item.resume || '');
    setOriginalLatexTemplate(item.originalLatexTemplate || '');
    setResumeTemplate(item.resumeTemplate || 'classic');
    setCompany(item.companyName || '');
    setRole(item.roleTitle || '');
    setStyle(item.targetStyle || 'General');
    setAnalysis(item.analysis);
    setActiveTab('JD Classification');
    setError('');
  }

  function clearHistory() {
    setHistory([]);
    localStorage.removeItem(HISTORY_KEY);
  }

  function renderTab() {
    if (!analysis) return null;
    const classification = analysis.classification || {};
    const keywords = analysis.keywords || {};
    const resumeMatch = analysis.resume_match || {};
    const guardrails = analysis.guardrails || {};
    const tailored = analysis.tailored_resume || {};
    const interview = analysis.interview_prep || {};

    switch (activeTab) {
      case 'JD Classification':
        return (
          <section className="tab-panel">
            <div className="summary-grid">
              <article className="card panel lead-panel">
                <h2>Detected Role Shape</h2>
                <div className="chips">
                  <Pill>{text(classification.business_domain)}</Pill>
                  <Pill>{text(classification.engineering_domain)}</Pill>
                  <Pill>{text(classification.speed_pattern)}</Pill>
                  <Pill>{text(classification.company_maturity)}</Pill>
                </div>
                <ConfidenceMeter value={classification.confidence} />
              </article>
              <EvidenceCard title="Evidence for classification" evidence={classification.evidence} />
            </div>
            <div className="grid2">
              <ListCard title="Alternative domains" items={classification.alternative_domains} />
              <ListCard title="Classification rationale" items={classification.rationale} />
            </div>
          </section>
        );
      case 'ATS Keywords':
        return (
          <section className="tab-panel">
            <div className="grid3">
              <ListCard title="Must-have" items={keywords.must_have} />
              <ListCard title="Important" items={keywords.important} />
              <ListCard title="Bonus" items={keywords.bonus} />
            </div>
            <div className="grid2">
              <ListCard title="Missing from resume" items={keywords.missing_from_resume} />
              <ListCard title="Soft-skill signals" items={keywords.soft_skill_signals} />
            </div>
            <div className="grid3">
              <ListCard title="Exact matches" items={keywords.exact_match} />
              <ListCard title="Semantic matches" items={keywords.semantic_match} />
              <ListCard title="Inferred matches" items={keywords.inferred_match} />
            </div>
            <article className="card panel">
              <h3>Tool stack</h3>
              <ToolStack stack={keywords.tool_stack} />
            </article>
            <EvidenceCard title="Keyword evidence" evidence={keywords.evidence} />
          </section>
        );
      case 'Resume Match':
        return (
          <section className="tab-panel">
            <div className="scoregrid">
              {scoreItems.map(([label, value, intent]) => <ScoreCard key={label} label={label} value={value} intent={intent} />)}
            </div>
            <div className="grid2">
              <ListCard title="Strong matches" items={resumeMatch.strong_matches} />
              <ListCard title="Weak matches" items={resumeMatch.weak_matches} />
              <ListCard title="Gaps" items={resumeMatch.gaps} />
              <ListCard title="Unsupported-claim risks" items={resumeMatch.unsupported_claim_risks} />
            </div>
            <EvidenceCard title="Match evidence" evidence={resumeMatch.evidence} />
          </section>
        );
      case 'Truthfulness Guardrails':
        return (
          <section className="tab-panel">
            <div className="grid3">
              <ListCard title="Do not claim" items={guardrails.do_not_claim} />
              <ListCard title="Safe reframes" items={guardrails.safe_reframes} />
              <ListCard title="Risky insertions" items={guardrails.risky_insertions} />
            </div>
            <div className="grid2">
              <ListCard title="Unsupported tools" items={guardrails.unsupported_tools} />
              <ListCard title="Unsupported scale claims" items={guardrails.unsupported_scale_claims} />
              <ListCard title="Unsupported domain claims" items={guardrails.unsupported_domain_claims} />
              <ListCard title="Unsupported architecture ownership" items={guardrails.unsupported_architecture_claims} />
            </div>
            <EvidenceCard title="Guardrail evidence" evidence={guardrails.evidence} />
          </section>
        );
      case 'Tailored Resume':
        return (
          <section className="tab-panel">
            <section className="resume-subsection">
              <h2>Tailoring Suggestions</h2>
              <div className="grid2">
                <ListCard title="Rewritten bullets" items={tailored.rewritten_bullets} />
                <ListCard title="Revised skills" items={tailored.revised_skills} />
              </div>
            </section>

            <article className="card panel action-panel">
              <div>
                <h2>Export Final Resume</h2>
                <p>ATS-friendly one-column resume generated from the master resume with truthfulness guardrails applied.</p>
                {tailored.template_warning && <p className="warning-note">{tailored.template_warning}</p>}
              </div>
              <div className="actions">
                <button onClick={downloadFinalResumePdf} disabled={exportingPdf || !latex.trim()}>
                  {exportingPdf ? 'Generating PDF...' : 'Download Final Resume PDF'}
                </button>
                <button onClick={() => downloadFile('final_tailored_resume.tex', latex, 'application/x-tex')}>Download Final Resume LaTeX</button>
                <button onClick={() => downloadFile('final_tailored_resume.md', markdown, 'text/markdown')}>Download Final Resume Markdown</button>
              </div>
            </article>
            {exportError && <section className="card error-state"><strong>PDF export failed</strong><p>{exportError}</p></section>}

            <article className="card panel">
              <h2>Final Resume Preview</h2>
              <pre>{text(tailored.final_resume_markdown, 'No final resume draft returned.')}</pre>
            </article>
            <div className="grid2">
              <article className="card panel">
                <h3>Final Resume Markdown</h3>
                <pre>{text(tailored.final_resume_markdown, 'No Markdown draft returned.')}</pre>
              </article>
              <article className="card panel">
                <h3>Final Resume LaTeX</h3>
                <pre>{text(tailored.final_resume_latex, 'No LaTeX draft returned.')}</pre>
              </article>
            </div>
          </section>
        );
      case 'Interview Prep':
        return (
          <section className="tab-panel">
            <div className="grid2">
              <ListCard title="SQL questions" items={interview.sql_questions} />
              <ListCard title="Data modeling questions" items={interview.data_modeling_questions} />
              <ListCard title="Data platform questions" items={interview.data_platform_questions} />
              <ListCard title="Data engineering questions" items={interview.data_engineering_questions} />
              <ListCard title="Cloud questions" items={interview.cloud_questions} />
              <ListCard title="Data quality questions" items={interview.data_quality_questions} />
              <ListCard title="Domain/business questions" items={interview.domain_business_questions} />
              <ListCard title="Behavioral questions" items={interview.behavioral_questions} />
              <ListCard title="Resume defense questions" items={interview.resume_defense_questions} />
            </div>
          </section>
        );
      case 'Hiring Manager Verdict':
        return (
          <section className="tab-panel">
            <div className="grid2">
              <article className="card panel">
                <h2>Hiring Manager Verdict</h2>
                <p>{text(analysis.brutal_hiring_manager_verdict)}</p>
              </article>
              <article className="card panel action-panel vertical">
                <div>
                  <h2>Why Interested Answer</h2>
                  <p>{text(analysis.why_interested_answer)}</p>
                </div>
                <button onClick={() => copyText(whyInterested, setCopied, 'Why-interested answer')}>Copy Answer</button>
              </article>
            </div>
          </section>
        );
      default:
        return null;
    }
  }

  return (
    <main>
      <header className="app-header">
        <div>
          <h1>CareerFit AI Agent</h1>
          <p>Explainable JD analysis, truthful resume tailoring, and interview prep in one workflow.</p>
        </div>
        <div className="header-meta">
          {analysis && <Pill>{confidence(analysis.classification?.confidence)}% JD confidence</Pill>}
          {copied && <span className="copied">{copied} copied</span>}
        </div>
      </header>

      <section className="card input-shell">
        <div className="controls">
          <label>
            <span>Company</span>
            <input placeholder="Company name" value={company} onChange={e => setCompany(e.target.value)} />
          </label>
          <label>
            <span>Role</span>
            <input placeholder="Role title" value={role} onChange={e => setRole(e.target.value)} />
          </label>
          <label>
            <span>Style</span>
            <select value={style} onChange={e => setStyle(e.target.value)}>
              <option>General</option>
              <option>Big Tech</option>
              <option>SaaS</option>
              <option>Consulting</option>
              <option>Startup</option>
            </select>
          </label>
          <label>
            <span>Select Resume Template</span>
            <select value={resumeTemplate} onChange={e => setResumeTemplate(e.target.value)}>
              {resumeTemplates.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="grid2 editors">
          <label>
            <span>Job Description</span>
            <textarea value={jd} onChange={e => setJd(e.target.value)} placeholder="Paste JD here..." />
          </label>
          <label>
            <span>Master Resume Content</span>
            <textarea value={resume} onChange={e => setResume(e.target.value)} placeholder="Paste resume markdown/text here..." />
          </label>
        </div>

        <section className="latex-template-input">
          <div className="section-title compact">
            <div>
              <h2>Paste Original LaTeX Template</h2>
              <p>For exact PDF formatting, provide your original LaTeX resume template. If provided, it overrides the selected built-in template.</p>
            </div>
            <label className="file-button">
              Upload .tex
              <input type="file" accept=".tex,text/x-tex,text/plain" onChange={uploadLatexTemplate} />
            </label>
          </div>
          <textarea
            className="latex-template-textarea"
            value={originalLatexTemplate}
            onChange={e => setOriginalLatexTemplate(e.target.value)}
            placeholder="Paste your original LaTeX resume template here. If omitted, the app uses the selected built-in template."
          />
        </section>

        <div className="run-row">
          <button className="primary" onClick={runAnalysis} disabled={!canRun}>
            {loading ? 'Analyzing...' : 'Run Full Agent Workflow'}
          </button>
          <span>{jd.trim().length < 50 || resume.trim().length < 50 ? 'Paste at least 50 characters in both text areas.' : 'Ready to analyze.'}</span>
        </div>
      </section>

      {!!history.length && (
        <section className="history">
          <div className="section-title">
            <h2>Recent Analyses</h2>
            <button className="ghost" onClick={clearHistory}>Clear</button>
          </div>
          <div className="history-list">
            {history.map(item => (
              <button className="history-item" key={item.id} onClick={() => openSaved(item)}>
                <strong>{item.roleTitle || 'Untitled role'}</strong>
                <span>{item.companyName || 'Unknown company'} - {new Date(item.createdAt).toLocaleString()}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {error && <section className="card error-state"><strong>Analysis failed</strong><p>{error}</p></section>}
      {loading && <LoadingState />}

      {analysis && !loading && (
        <section className="results">
          <QualityReviewPanel analysis={analysis} />
          <nav className="tabs" aria-label="Analysis sections">
            {tabs.map(tab => (
              <button
                key={tab}
                className={activeTab === tab ? 'active' : ''}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </nav>
          {renderTab()}
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
