import { useState, useEffect, useRef } from "react";
import "./App.css";

const EXAMPLE_CODE = `def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

result = calculate_average([10, 20, 30, 40])
print("Average:", resultt)`;

const API_BASE = import.meta.env.VITE_API_URL || "";

/* ── Hooks ────────────────────────────────────── */
function useTypewriter(text, speed = 14, active = false) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    if (!active || !text) { setDisplayed(""); return; }
    setDisplayed("");
    let i = 0;
    const id = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, active]);
  return displayed;
}

/* ── Small Components ─────────────────────────── */
function Dots() {
  const [n, setN] = useState(1);
  useEffect(() => {
    const id = setInterval(() => setN((c) => (c % 3) + 1), 420);
    return () => clearInterval(id);
  }, []);
  return <span className="dots">{"█".repeat(n)}</span>;
}

function TitleBar({ title, subtitle }) {
  return (
    <div className="titlebar">
      <div className="traffic-lights">
        <span className="tl red" />
        <span className="tl yellow" />
        <span className="tl green" />
      </div>
      <span className="tb-title">{title}</span>
      {subtitle && <span className="tb-sub">{subtitle}</span>}
    </div>
  );
}

function LineNums({ code }) {
  const count = (code || "\n").split("\n").length;
  return (
    <div className="line-nums">
      {Array.from({ length: Math.max(count, 1) }, (_, i) => (
        <span key={i}>{String(i + 1).padStart(2, " ")}</span>
      ))}
    </div>
  );
}

/* ── Main App ─────────────────────────────────── */
export default function App() {
  const [code, setCode]           = useState("");
  const [status, setStatus]       = useState("idle"); // idle | analyzing | done | error
  const [result, setResult]       = useState(null);    // Layer 1-3 instant response
  const [enrichment, setEnrichment] = useState(null);  // Layer 4 async bonus
  const [enriching, setEnriching] = useState(false);
  const [error, setError]         = useState("");
  const textareaRef               = useRef(null);

  /* Typewriters */
  const hintTyped     = useTypewriter(result?.mentor_hint ?? "", 12, status === "done");
  const hintDone      = hintTyped.length === (result?.mentor_hint?.length ?? 0);
  const enrichedTyped = useTypewriter(enrichment?.enriched_hint ?? "", 10, hintDone && !!enrichment);

  /* ── Primary analysis (Layers 1-3, instant) ── */
  async function handleAnalyze() {
    if (!code.trim()) return;
    setStatus("analyzing");
    setResult(null);
    setEnrichment(null);
    setError("");

    try {
      const resp = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setResult(data);
      setStatus("done");

      /* Fire async enrichment (Layer 4) — non-blocking */
      fetchEnrichment(data);

    } catch (e) {
      console.error("Analysis failed:", e);
      setError(e.message);
      setStatus("error");
    }
  }

  /* ── Async enrichment (Layer 4, bonus) ── */
  async function fetchEnrichment(analyzeResult) {
    setEnriching(true);
    try {
      const resp = await fetch(`${API_BASE}/api/enrich`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code,
          error_category: analyzeResult.error_category,
          rule_hint: analyzeResult.mentor_hint,
          findings: analyzeResult.findings,
          difficulty: analyzeResult.difficulty || "intermediate",
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.source !== "skipped") {
          setEnrichment(data);
        }
      }
    } catch (e) {
      console.warn("Enrichment skipped:", e.message);
    } finally {
      setEnriching(false);
    }
  }

  function handleReset() {
    setCode(""); setStatus("idle"); setResult(null); setEnrichment(null); setError("");
    setTimeout(() => textareaRef.current?.focus(), 50);
  }

  return (
    <div className="app">

      {/* ══ HEADER ══ */}
      <header className="header">
        <div className="header-left">
          <span className="logo-bracket">[</span>
          <span className="logo-text">CodeKraft</span>
          <span className="logo-bracket">]</span>
          <span className="logo-cursor">▌</span>
          <span className="logo-desc">4-Layer AI Python Debugger</span>
        </div>
        <div className="header-right">
          <span className="hbadge">v2.0</span>
          <span className="hbadge green">● LIVE</span>
        </div>
      </header>

      {/* ══ PIPELINE BAR ══ */}
      <div className="cmdbar">
        <span className={`pipeline-step ${status !== "idle" ? "step-done" : "step-active"}`}>
          <span className="step-dot" />L1: Static Analyzer
        </span>
        <span className="cb-arrow">→</span>
        <span className={`pipeline-step ${status === "done" ? "step-done" : status === "analyzing" ? "step-active" : ""}`}>
          <span className="step-dot" />L2: CodeBERT
        </span>
        <span className="cb-arrow">→</span>
        <span className={`pipeline-step ${status === "done" ? "step-done" : ""}`}>
          <span className="step-dot" />L3: Rule Engine
        </span>
        <span className="cb-arrow">→</span>
        <span className={`pipeline-step ${enrichment ? "step-done" : enriching ? "step-active" : ""}`}>
          <span className="step-dot" />L4: LLM Enricher
          {enriching && <span className="step-tag">async</span>}
        </span>
      </div>

      {/* ══ MAIN WORKSPACE ══ */}
      <div className="workspace">

        {/* ── LEFT: INPUT ── */}
        <div className="panel left-panel">
          <TitleBar title="input.py" subtitle="~/codekraft/workspace" />

          <div className="editor-area">
            <LineNums code={code || "\n"} />
            <textarea
              ref={textareaRef}
              className="code-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={"# Paste your buggy Python code here...\n# Example:\n\ndef greet(name):\n    print('Hello ' + nme)  # ← typo!"}
              spellCheck={false}
              autoComplete="off"
            />
          </div>

          <div className="action-bar">
            <button className="ghost-btn" onClick={() => { setCode(EXAMPLE_CODE); setResult(null); setEnrichment(null); setStatus("idle"); }}>
              load example
            </button>
            <button className="ghost-btn" onClick={handleReset}>clear</button>
            <div style={{ flex: 1 }} />
            <button
              className={`run-btn${status === "analyzing" ? " running" : ""}`}
              onClick={handleAnalyze}
              disabled={status === "analyzing" || !code.trim()}
            >
              {status === "analyzing"
                ? <><Dots /> <span>analyzing</span></>
                : <><span className="run-arrow">▶</span> $ codekraft analyze</>
              }
            </button>
            {status === "done" && (
              <span className="done-tag">✓ {result?.latency?.total_ms?.toFixed(0) ?? ""}ms</span>
            )}
          </div>
        </div>

        {/* ── RIGHT: OUTPUT ── */}
        <div className="panel right-panel">
          <TitleBar
            title="output.log"
            subtitle={result ? `${result.classification_model} | confidence: ${(result.classification_confidence * 100).toFixed(1)}%` : "~/codekraft/output"}
          />

          <div className="output-scroll">

            {/* IDLE */}
            {status === "idle" && (
              <div className="idle-screen">
                <pre className="ascii-art">{`
   ██████╗ ██████╗ ██████╗ ███████╗
  ██╔════╝██╔═══██╗██╔══██╗██╔════╝
  ██║     ██║   ██║██║  ██║█████╗
  ██║     ██║   ██║██║  ██║██╔══╝
  ╚██████╗╚██████╔╝██████╔╝███████╗
   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
  ██╗  ██╗██████╗  █████╗ ███████╗████████╗
  ██║ ██╔╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝
  █████╔╝ ██████╔╝███████║█████╗     ██║
  ██╔═██╗ ██╔══██╗██╔══██║██╔══╝     ██║
  ██║  ██╗██║  ██║██║  ██║██║        ██║
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝   `}</pre>
                <p className="idle-tagline">4-Layer AI Python Error Feedback Pipeline</p>
                <div className="pipeline-steps">
                  <div className="ps"><span className="ps-num green">L1</span><span className="ps-arrow">→</span><span>Static Analyzer (AST parsing, &lt; 5ms)</span></div>
                  <div className="ps"><span className="ps-num blue">L2</span><span className="ps-arrow">→</span><span>CodeBERT classifier (error type, ~250ms)</span></div>
                  <div className="ps"><span className="ps-num amber-text">L3</span><span className="ps-arrow">→</span><span>Rule Engine (pre-computed mentor hint, &lt; 1ms)</span></div>
                  <div className="ps"><span className="ps-num cyan">L4</span><span className="ps-arrow">→</span><span>LLM Enricher (GPT-3.5, async bonus)</span></div>
                </div>
                <div className="idle-prompt">
                  <span className="sym green">▶</span>
                  <span className="idle-blink"> Waiting for input<Dots /></span>
                </div>
              </div>
            )}

            {/* ANALYZING */}
            {status === "analyzing" && (
              <div className="loading-screen">
                <div className="log-lines">
                  <p className="ll"><span className="sym green">L1</span> Running static analysis<Dots /></p>
                  <p className="ll dim">  → Parsing AST...</p>
                  <p className="ll dim">  → Detecting patterns (NameError, OffByOne, WrongOp)...</p>
                  <p className="ll"><span className="sym blue">L2</span> Calling CodeBERT classifier<Dots /></p>
                  <p className="ll dim">  → HF Inference API: microsoft/codebert-base...</p>
                  <p className="ll"><span className="sym amber">L3</span> Looking up rule engine hints<Dots /></p>
                  <p className="ll dim">  → Matching error category to pre-computed hint...</p>
                </div>
              </div>
            )}

            {/* ERROR */}
            {status === "error" && (
              <div className="error-screen">
                <p className="err-title">✖ Analysis Failed</p>
                <p className="err-msg">{error}</p>
                <button className="ghost-btn" onClick={handleReset} style={{ marginTop: 12 }}>↺ try again</button>
              </div>
            )}

            {/* DONE */}
            {status === "done" && result && (
              <div className="result-screen">

                {/* ── Findings (Layer 1) ── */}
                {result.findings && result.findings.length > 0 && (
                  <div className="result-section">
                    <div className="section-label green-label">
                      <span className="check">⚡</span>
                      <span>L1: Static Analysis Findings</span>
                      <span className="latency-tag">&lt; 5ms</span>
                    </div>
                    <div className="findings-list">
                      {result.findings.map((f, i) => (
                        <div key={i} className={`finding ${f.severity === "error" ? "finding-error" : "finding-warn"}`}>
                          <span className="finding-badge">{f.rule_id}</span>
                          <span className="finding-line">line {f.line ?? "?"}</span>
                          <span className="finding-msg">{f.message}</span>
                          <span className="finding-conf">{(f.confidence * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── Classification (Layer 2) ── */}
                <div className="result-section">
                  <div className="section-label blue-label">
                    <span>🧠</span>
                    <span>L2: CodeBERT Classification</span>
                    <span className="latency-tag">~250ms</span>
                  </div>
                  <div className="classification-box">
                    <div className="cls-main">
                      <span className="cls-label">{result.error_category}</span>
                      <span className="cls-conf">{(result.classification_confidence * 100).toFixed(1)}% confidence</span>
                      <span className={`cls-source ${result.classification_source === "codebert" ? "src-model" : "src-static"}`}>
                        {result.classification_source}
                      </span>
                    </div>
                  </div>
                </div>

                {/* ── Divider ── */}
                <div className="section-sep">
                  <span>─── L3: Rule Engine Mentor Hint {'─'.repeat(24)}</span>
                </div>

                {/* ── Mentor Hint (Layer 3) ── */}
                <div className="result-section">
                  <div className="section-label amber-label">
                    <span>💡</span>
                    <span>Instant Mentor Hint</span>
                    <span className="hint-note">&lt; 1ms • no LLM call</span>
                  </div>
                  <div className="hint-block">
                    <span className="sym amber" style={{ fontSize: 11, marginRight: 8, flexShrink: 0, marginTop: 2 }}>▶</span>
                    <span className="hint-text">
                      {hintTyped}
                      {!hintDone && <span className="cursor-blink amber-cursor">▌</span>}
                    </span>
                  </div>
                  {result.follow_up && hintDone && (
                    <div className="follow-up-box">
                      <span className="fu-label">Think about this:</span>
                      <span className="fu-text">{result.follow_up}</span>
                    </div>
                  )}
                  {result.common_fix && hintDone && (
                    <div className="fix-pattern-box">
                      <span className="fp-label">Common fix pattern:</span>
                      <span className="fp-text">{result.common_fix}</span>
                    </div>
                  )}
                </div>

                {/* ── LLM Enrichment (Layer 4) ── */}
                {(enriching || enrichment) && (
                  <>
                    <div className="section-sep">
                      <span>─── L4: GPT-3.5 Enriched Hint {'─'.repeat(22)}</span>
                    </div>
                    <div className="result-section">
                      <div className="section-label cyan-label">
                        <span>🤖</span>
                        <span>LLM-Enriched Hint</span>
                        {enriching && <span className="hint-note">loading<Dots /></span>}
                        {enrichment && <span className="hint-note">async bonus • {enrichment.model}</span>}
                      </div>
                      {enrichment && (
                        <div className="hint-block enriched-block">
                          <span className="sym cyan" style={{ fontSize: 11, marginRight: 8, flexShrink: 0, marginTop: 2 }}>▶</span>
                          <span className="hint-text enriched-text">
                            {enrichedTyped}
                            {enrichedTyped.length < (enrichment?.enriched_hint?.length ?? 0) && (
                              <span className="cursor-blink cyan-cursor">▌</span>
                            )}
                          </span>
                        </div>
                      )}
                      {enriching && !enrichment && (
                        <div className="hint-block" style={{ opacity: 0.5 }}>
                          <span className="hint-text dim">Generating enriched hint<Dots /></span>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* ── Latency Stats ── */}
                {result.latency && hintDone && (
                  <div className="result-section">
                    <div className="section-label dim-label">
                      <span>⏱</span>
                      <span>Latency Breakdown</span>
                    </div>
                    <div className="latency-grid">
                      <div className="lat-item">
                        <span className="lat-label">L1 Static</span>
                        <span className="lat-bar"><span className="lat-fill green-fill" style={{ width: `${Math.min(100, (result.latency.static_analysis_ms / result.latency.total_ms) * 100)}%` }} /></span>
                        <span className="lat-val">{result.latency.static_analysis_ms?.toFixed(1)}ms</span>
                      </div>
                      <div className="lat-item">
                        <span className="lat-label">L2 CodeBERT</span>
                        <span className="lat-bar"><span className="lat-fill blue-fill" style={{ width: `${Math.min(100, (result.latency.classifier_ms / result.latency.total_ms) * 100)}%` }} /></span>
                        <span className="lat-val">{result.latency.classifier_ms?.toFixed(1)}ms</span>
                      </div>
                      <div className="lat-item">
                        <span className="lat-label">L3 Rules</span>
                        <span className="lat-bar"><span className="lat-fill amber-fill" style={{ width: `${Math.min(100, (result.latency.rule_engine_ms / result.latency.total_ms) * 100)}%` }} /></span>
                        <span className="lat-val">{result.latency.rule_engine_ms?.toFixed(1)}ms</span>
                      </div>
                      <div className="lat-item">
                        <span className="lat-label total">Total (instant)</span>
                        <span className="lat-bar"><span className="lat-fill total-fill" style={{ width: "100%" }} /></span>
                        <span className="lat-val total">{result.latency.instant_response_ms?.toFixed(0)}ms</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="reanalyze-row">
                  <button className="ghost-btn small" onClick={handleReset}>↺ analyze another snippet</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ══ STATUS BAR ══ */}
      <footer className="statusbar">
        <span className="sb green">⬤ CodeKraft v2</span>
        <span className="sb-sep">│</span>
        <span className="sb">CodeBERT: codebert-base</span>
        <span className="sb-sep">│</span>
        <span className="sb">LLM: gpt-3.5-turbo</span>
        <span className="sb-sep">│</span>
        <span className="sb">4-Layer Pipeline</span>
        <span className="sb-push" />
        <span className="sb dim">github.com/karan-patel11/CodeKraft</span>
      </footer>
    </div>
  );
}
