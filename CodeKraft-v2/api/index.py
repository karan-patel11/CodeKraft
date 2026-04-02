"""
CodeKraft API v2 — 4-Layer AI Python Debugging Pipeline

Architecture (latency targets):
  Layer 1: Static Analyzer   (AST heuristics)       →  < 5ms   ← INSTANT
  Layer 2: CodeBERT Classifier (HF Inference API)    →  ~250ms  ← FAST
  Layer 3: Rule Engine        (pre-computed hints)   →  < 1ms   ← INSTANT
  ─── INSTANT RESPONSE RETURNED TO USER HERE ───────────────────
  Layer 4: LLM Enricher      (GPT-3.5, optional)    →  ~800ms  ← ASYNC BONUS

The user gets actionable feedback in < 300ms. The LLM enrichment
is a BONUS delivered separately — never blocks the primary response.
"""

import os
import sys
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Ensure lib/ is importable ────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib import static_analyzer
from lib import classifier
from lib import rule_engine
from lib import llm_enricher
from lib.metrics import RequestMetrics, get_aggregator, measure

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("codekraft")

# ── Config ────────────────────────────────────────────────────────────────────
_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,*").split(",")
    if o.strip()
]

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CodeKraft API",
    description="4-layer AI Python debugging pipeline: Static Analysis → CodeBERT → Rule Engine → LLM",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  Request / Response Models
# ══════════════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10000, description="Buggy Python code")

class AnalyzeResponse(BaseModel):
    """Instant response from Layers 1-3 (returned in < 300ms)."""
    # ── Layer 1: Static Analysis ──
    parseable: bool
    syntax_error: Optional[str] = None
    findings: list
    code_stats: dict

    # ── Layer 2: Classification ──
    error_category: str
    classification_confidence: float
    classification_source: str
    classification_model: str

    # ── Layer 3: Rule Engine Hint ──
    mentor_hint: str
    follow_up: Optional[str] = None
    difficulty: Optional[str] = None
    common_fix: Optional[str] = None

    # ── Metrics ──
    latency: dict

class EnrichRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10000)
    error_category: str
    rule_hint: str
    findings: list = []
    difficulty: str = "intermediate"

class EnrichResponse(BaseModel):
    """Async LLM-enriched response from Layer 4."""
    enriched_hint: str
    model: str
    source: str


# ══════════════════════════════════════════════════════════════════════════════
#  PRIMARY ENDPOINT: /api/analyze  (Layers 1-3, instant)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_code(request: AnalyzeRequest):
    """
    Runs the 3-layer instant analysis pipeline:
      1. Static analysis (AST parsing + pattern detection)
      2. CodeBERT classification (error type via HF API)
      3. Rule engine hint lookup (pre-computed mentor hints)

    Returns immediately — no LLM calls in this path.

    ```json
    POST /api/analyze
    { "code": "def greet(name):\\n    print('Hello ' + nme)" }
    ```
    """
    metrics = RequestMetrics()
    metrics.code_lines = len(request.code.splitlines())

    try:
        # ── LAYER 1: Static Analysis (< 5ms) ─────────────────────────────
        with measure("static_analysis") as t1:
            sa_result = static_analyzer.analyze(request.code)
        metrics.static_analysis_ms = t1["elapsed_ms"]
        metrics.findings_count = len(sa_result.findings)
        metrics.complexity = sa_result.complexity_score

        sa_dict = sa_result.to_dict()

        # ── LAYER 2: CodeBERT Classification (~250ms) ────────────────────
        with measure("classifier") as t2:
            cls_result = await classifier.classify(
                code=request.code,
                static_category=sa_result.top_category,
            )
        metrics.classifier_ms = t2["elapsed_ms"]
        metrics.classification_source = cls_result.get("source", "unknown")
        metrics.classification_confidence = cls_result.get("confidence", 0.0)

        # Determine best error category: prefer classifier if confident, else static
        predicted_label = cls_result.get("predicted_label", "Unknown")
        if cls_result.get("confidence", 0) < 0.4 and sa_result.top_category:
            predicted_label = sa_result.top_category
            logger.info(f"Low classifier confidence — using static category: {predicted_label}")

        metrics.error_category = predicted_label

        # ── LAYER 3: Rule Engine Hint (< 1ms) ────────────────────────────
        with measure("rule_engine") as t3:
            hint_data = rule_engine.get_hint_dict(predicted_label)
        metrics.rule_engine_ms = t3["elapsed_ms"]

        # Fallback hint if rule engine has no match
        if not hint_data:
            hint_data = {
                "category": predicted_label,
                "hint": (
                    f"An issue of type '{predicted_label}' was detected. "
                    "Review your code carefully around the flagged lines."
                ),
                "follow_up": "Try running your code with a small test input and trace each variable.",
                "difficulty": "intermediate",
                "common_fix": "Compare your logic against the expected algorithm step by step.",
            }

        # ── Compute total latency ─────────────────────────────────────────
        metrics.total_ms = (
            metrics.static_analysis_ms + metrics.classifier_ms + metrics.rule_engine_ms
        )

        # Record metrics
        get_aggregator().record(metrics)

        logger.info(
            f"Analyzed in {metrics.total_ms:.1f}ms | "
            f"category={predicted_label} | "
            f"confidence={metrics.classification_confidence:.3f} | "
            f"source={metrics.classification_source} | "
            f"findings={metrics.findings_count}"
        )

        return AnalyzeResponse(
            # Layer 1
            parseable=sa_result.parseable,
            syntax_error=sa_result.syntax_error,
            findings=sa_dict["findings"],
            code_stats=sa_dict["stats"],
            # Layer 2
            error_category=predicted_label,
            classification_confidence=metrics.classification_confidence,
            classification_source=metrics.classification_source,
            classification_model=cls_result.get("model", ""),
            # Layer 3
            mentor_hint=hint_data["hint"],
            follow_up=hint_data.get("follow_up"),
            difficulty=hint_data.get("difficulty"),
            common_fix=hint_data.get("common_fix"),
            # Metrics
            latency=metrics.to_dict()["latency"],
        )

    except Exception as e:
        get_aggregator().record_error()
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
#  ENRICHMENT ENDPOINT: /api/enrich  (Layer 4, async bonus)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/enrich", response_model=EnrichResponse)
async def enrich_hint(request: EnrichRequest):
    """
    Layer 4: LLM-enriched mentor hint.

    Called by the frontend AFTER the instant /api/analyze response is
    already displayed. This is a bonus refinement — never blocks the user.

    ```json
    POST /api/enrich
    {
      "code": "...",
      "error_category": "NameError",
      "rule_hint": "A variable name is used but never defined...",
      "findings": [...],
      "difficulty": "beginner"
    }
    ```
    """
    result = await llm_enricher.enrich(
        code=request.code,
        error_category=request.error_category,
        rule_hint=request.rule_hint,
        static_findings=request.findings,
        difficulty=request.difficulty,
    )
    return EnrichResponse(**result)


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH & METRICS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    """Service health check."""
    return {
        "status": "healthy",
        "service": "codekraft-api",
        "version": "2.0.0",
        "architecture": "4-layer pipeline",
                "layers": [
            "L1: Static Analyzer (AST, < 5ms)",
            "L2: CodeBERT Classifier (HF API, ~250ms)",
            "L3: Rule Engine (pre-computed, < 1ms)",
            "L4: LLM Enricher (Groq/Llama3, ~800ms, async optional)",
        ],
        "hf_model": os.getenv("HF_MODEL", "microsoft/codebert-base"),
        "groq_model": os.getenv("GROQ_MODEL", "llama3-70b-8192"),
        "hf_configured": bool(os.getenv("HF_API_KEY")),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),

    }


@app.get("/api/metrics")
async def metrics():
    """Rolling performance metrics (last 100 requests)."""
    return get_aggregator().summary()


@app.get("/api/categories")
async def categories():
    """List all supported error categories."""
    return {"categories": rule_engine.get_all_categories()}
