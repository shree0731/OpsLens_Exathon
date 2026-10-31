import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Wizard, WizardStep } from '../components/common/Wizard';
import { fetchApi } from '../api/client';
import { 
  Sparkles, 
  Code2, 
  ShieldCheck, 
  Table2, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Clock, 
  Database, 
  ArrowRight, 
  RotateCcw,
  Zap,
  TrendingUp,
  FileCheck2,
  ExternalLink
} from 'lucide-react';

const ASK_STEPS: WizardStep[] = [
  { id: 1, title: 'Ask Question', subtitle: 'Natural language or template', description: 'Enter an operational question or pick from curated production templates' },
  { id: 2, title: 'Generated SQL', subtitle: 'Exasol optimized query', description: 'Review and optionally adjust the generated SQL query' },
  { id: 3, title: 'Guardrail Review', subtitle: '5-point security audit', description: 'Zero-trust guardrail checks ensuring query safety and compliance' },
  { id: 4, title: 'Query Results', subtitle: 'Execution output', description: 'Live query output returned directly from Exasol Personal' },
  { id: 5, title: 'Confirm & Save', subtitle: 'Audit & telemetry log', description: 'Persist execution metrics to OPSLENS.QUERY_STATS' },
];

export const AskPage: React.FC = () => {
  const navigate = useNavigate();

  // Wizard state
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [question, setQuestion] = useState<string>('What is our monthly revenue trend?');
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('revenue_by_month');
  
  // Generated SQL state
  const [generatedSql, setGeneratedSql] = useState<string>('');
  const [providerInfo, setProviderInfo] = useState<string>('Template Catalog');
  const [isTemplate, setIsTemplate] = useState<boolean>(true);
  
  // Guardrail review state
  const [guardrails, setGuardrails] = useState<any>(null);
  
  // Execution results state
  const [results, setResults] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load templates on mount
  useEffect(() => {
    fetchApi<any[]>('/api/ask/templates')
      .then((data) => {
        setTemplates(data || []);
        if (data && data.length > 0) {
          setGeneratedSql(data[0].sql);
        }
      })
      .catch((err) => console.error('Failed to load templates:', err));
  }, []);

  // Handle template selection
  const handleSelectTemplate = (t: any) => {
    setSelectedTemplateId(t.id);
    setQuestion(t.question);
    setGeneratedSql(t.sql);
  };

  // Step 1 -> Step 2: Generate SQL
  const handleGenerateSql = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetchApi<any>('/api/ask', {
        method: 'POST',
        body: JSON.stringify({ question }),
      });
      setGeneratedSql(res.sql);
      setProviderInfo(res.provider === 'llm' ? 'LLM Provider' : 'Template Catalog');
      setIsTemplate(res.is_template);
      setGuardrails(res.guardrails);
      setCurrentStep(1);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate SQL.');
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2 -> Step 3: Validate SQL with Guardrails
  const handleValidateGuardrails = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetchApi<any>('/api/ask/validate', {
        method: 'POST',
        body: JSON.stringify({ sql: generatedSql }),
      });
      setGuardrails(res);
      setCurrentStep(2);
    } catch (err: any) {
      setErrorMessage(err.message || 'Validation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  // Step 3 -> Step 4: Execute SQL on Exasol
  const handleExecuteSql = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetchApi<any>('/api/ask/run', {
        method: 'POST',
        body: JSON.stringify({ sql: generatedSql, question }),
      });
      setResults(res);
      setCurrentStep(3);
    } catch (err: any) {
      setErrorMessage(err.message || 'Execution error on Exasol engine.');
    } finally {
      setIsLoading(false);
    }
  };

  // Next button logic
  const handleNext = () => {
    if (currentStep === 0) {
      handleGenerateSql();
    } else if (currentStep === 1) {
      handleValidateGuardrails();
    } else if (currentStep === 2) {
      handleExecuteSql();
    } else if (currentStep === 3) {
      setCurrentStep(4);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setErrorMessage(null);
      setCurrentStep(currentStep - 1);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setResults(null);
    setErrorMessage(null);
  };

  const isGuardrailSafe = guardrails ? guardrails.is_safe : false;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300">
      <Wizard
        title="Ask-the-Warehouse"
        subtitle="Conversational Intelligence & Guardrailed Text-to-SQL"
        steps={ASK_STEPS}
        currentStep={currentStep}
        onStepChange={(step) => {
          if (step < currentStep) setCurrentStep(step);
        }}
        onNext={handleNext}
        onBack={handleBack}
        onFinish={handleReset}
        isNextDisabled={
          (currentStep === 0 && !question.trim()) ||
          (currentStep === 1 && !generatedSql.trim()) ||
          (currentStep === 2 && !isGuardrailSafe)
        }
        isNextLoading={isLoading}
        nextLabel={
          currentStep === 0
            ? 'Generate SQL'
            : currentStep === 1
            ? 'Review Guardrails'
            : currentStep === 2
            ? 'Execute on Exasol'
            : currentStep === 3
            ? 'Confirm & Save'
            : 'Ask Another Question'
        }
      >
        {/* Error message alert */}
        {errorMessage && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs font-medium text-rose-700 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* STEP 1: Ask a Question */}
        {currentStep === 0 && (
          <div className="space-y-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Operational Question (Natural Language)
              </label>
              <div className="relative">
                <textarea
                  rows={3}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="e.g. What is our monthly revenue trend?"
                  className="w-full text-sm rounded-xl border border-slate-200 p-3.5 outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all font-medium text-slate-800"
                />
                <div className="absolute right-3 bottom-3 flex items-center gap-1.5 text-xs text-brand-600 bg-brand-50 px-2 py-0.5 rounded-md font-semibold">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Exasol AI Copilot</span>
                </div>
              </div>
            </div>

            {/* Clickable Sample Questions */}
            <div>
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">
                  Or pick a curated production template (8 available)
                </span>
                <span className="text-xs text-slate-400">Zero-shot instant answer</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {templates.map((t) => {
                  const isSelected = t.id === selectedTemplateId;
                  return (
                    <div
                      key={t.id}
                      onClick={() => handleSelectTemplate(t)}
                      className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-brand-50/80 border-brand-500 shadow-xs'
                          : 'bg-white border-slate-200 hover:border-brand-300 hover:bg-slate-50/60'
                      }`}
                    >
                      <p className="text-xs font-bold text-slate-900 line-clamp-1">{t.question}</p>
                      <p className="text-[11px] text-slate-500 mt-1 line-clamp-1">{t.summary}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Generated SQL */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Generated SQL Query (Editable)
                </span>
                <p className="text-xs text-slate-500 mt-0.5">
                  Synthesized for Exasol Personal schema <code className="font-mono text-brand-700">OPSLENS</code>.
                </p>
              </div>

              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-brand-50 text-brand-700 border border-brand-200">
                <Database className="w-3.5 h-3.5" />
                <span>{providerInfo}</span>
              </span>
            </div>

            <div className="relative">
              <textarea
                rows={10}
                value={generatedSql}
                onChange={(e) => setGeneratedSql(e.target.value)}
                className="w-full font-mono text-xs text-slate-900 bg-slate-900 text-slate-100 rounded-xl p-4 outline-none focus:ring-2 focus:ring-brand-500 transition-all leading-relaxed"
                spellCheck={false}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
              <span>Press Next to execute 5-point automated security guardrails review.</span>
              <button
                onClick={() => {
                  const tmpl = templates.find((t) => t.id === selectedTemplateId);
                  if (tmpl) setGeneratedSql(tmpl.sql);
                }}
                className="text-brand-600 hover:text-brand-800 font-semibold flex items-center gap-1"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset to template original</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Guardrail Review */}
        {currentStep === 2 && guardrails && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Security Guardrail Audit
                </span>
                <p className="text-xs text-slate-500 mt-0.5">
                  Zero-trust verification before query execution against Exasol.
                </p>
              </div>

              <span
                className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold ${
                  guardrails.is_safe
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    : 'bg-rose-100 text-rose-800 border border-rose-300'
                }`}
              >
                {guardrails.is_safe ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                <span>{guardrails.is_safe ? 'All 5 Guardrails Passed' : 'Security Policy Violation'}</span>
              </span>
            </div>

            {/* Chips List */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { key: 'select_only', label: '1. SELECT-Only (Read-Only)', icon: <ShieldCheck className="w-4 h-4" /> },
                { key: 'single_statement', label: '2. Single Statement (No Injection)', icon: <Code2 className="w-4 h-4" /> },
                { key: 'opslens_schema_only', label: '3. OPSLENS Schema Scope Only', icon: <Database className="w-4 h-4" /> },
                { key: 'limit_enforced', label: '4. LIMIT Quota Enforced (<= 1000)', icon: <Clock className="w-4 h-4" /> },
                { key: 'engine_validated', label: '5. Exasol Engine Dry-Run Validated', icon: <FileCheck2 className="w-4 h-4" /> },
              ].map(({ key, label, icon }) => {
                const chip = guardrails.chips?.[key];
                const passed = chip?.passed;

                return (
                  <div
                    key={key}
                    className={`p-3.5 rounded-xl border flex items-start justify-between gap-3 ${
                      passed
                        ? 'bg-emerald-50/50 border-emerald-200 text-emerald-900'
                        : 'bg-rose-50/60 border-rose-200 text-rose-900'
                    }`}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className={`p-1.5 rounded-lg ${passed ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                        {icon}
                      </div>
                      <div>
                        <p className="text-xs font-bold">{label}</p>
                        <p className={`text-[11px] mt-0.5 ${passed ? 'text-emerald-700' : 'text-rose-700 font-medium'}`}>
                          {chip?.reason || (passed ? 'Verified' : 'Failed')}
                        </p>
                      </div>
                    </div>

                    <span className="flex-shrink-0">
                      {passed ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-5 h-5 text-rose-600" />
                      )}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Read-only SQL view */}
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Verified Query String:
              </span>
              <pre className="font-mono text-xs text-slate-700 overflow-x-auto whitespace-pre-wrap">
                {generatedSql}
              </pre>
            </div>
          </div>
        )}

        {/* STEP 4: Query Results Table */}
        {currentStep === 3 && results && (
          <div className="space-y-4">
            {/* Execution Metrics Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center gap-4 text-xs font-semibold text-slate-700">
                <span className="flex items-center gap-1.5">
                  <Table2 className="w-4 h-4 text-brand-600" />
                  <strong>{results.row_count}</strong> rows returned
                </span>
                <span>•</span>
                <span className="flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-amber-500" />
                  Execution latency: <strong>{results.duration_sec}s</strong>
                </span>
              </div>

              <span className="text-[11px] font-mono font-medium text-slate-500">
                Query ID: {results.query_id}
              </span>
            </div>

            {/* Results Table */}
            <div className="border border-slate-200 rounded-xl overflow-hidden max-h-[380px] overflow-y-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-100 text-slate-700 font-bold sticky top-0 border-b border-slate-200 z-10">
                  <tr>
                    {(results.columns || []).map((col: string) => (
                      <th key={col} className="p-2.5 whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {(results.rows || []).map((row: any, i: number) => (
                    <tr key={i} className="hover:bg-slate-50/80 transition-colors">
                      {(results.columns || []).map((col: string) => (
                        <td key={col} className="p-2.5 font-mono text-slate-800 whitespace-nowrap">
                          {row[col] !== null && row[col] !== undefined ? String(row[col]) : 'NULL'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* STEP 5: Confirm & Finish */}
        {currentStep === 4 && (
          <div className="space-y-6 text-center max-w-xl mx-auto py-6">
            <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-sm">
              <CheckCircle2 className="w-8 h-8 stroke-[2.5]" />
            </div>

            <div>
              <h3 className="text-xl font-bold text-slate-900 tracking-tight">
                Request Resolved in {results?.duration_sec ?? 0.04} Seconds
              </h3>
              <p className="text-sm font-semibold text-emerald-700 mt-1">
                vs. typical weeks in an analytics ticket backlog!
              </p>
            </div>

            <div className="bg-slate-50 border border-slate-200/90 rounded-2xl p-4 text-left space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Query Telemetry ID:</span>
                <span className="font-mono font-bold text-slate-800">{results?.query_id || 'ask_confirmed'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Audit Status:</span>
                <span className="font-semibold text-emerald-700">Persisted to OPSLENS.QUERY_STATS</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Total Rows Retrieved:</span>
                <span className="font-semibold text-slate-800">{results?.row_count ?? 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Exasol Execution Time:</span>
                <span className="font-semibold text-slate-800">{results?.duration_sec ?? 0.04}s</span>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors"
              >
                Ask Another Question
              </button>

              <button
                onClick={() => navigate('/lineage')}
                className="px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold text-xs rounded-xl shadow-xs transition-colors"
              >
                View Pipeline Lineage
              </button>
            </div>
          </div>
        )}
      </Wizard>
    </div>
  );
};
