"""
Layer 4: LLM Enricher — async Groq-based mentor hint refinement.

Called ONLY AFTER Layers 1-3 have already returned an instant response
to the user. This layer takes the structured findings and refines the
hint into a context-aware, pedagogical explanation.

This is a BONUS enrichment — the system works fully without it.
Powered by Groq (FREE) using Llama 3 70B.
"""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("codekraft.llm_enricher")

# ── Groq config (100% free) ───────────────────
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama3-70b-8192")
GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"


SYSTEM_PROMPT = """You are CodeKraft, a patient Python tutor who helps students fix bugs by guiding them — never by giving the answer directly.

Rules:
1. NEVER show the corrected code.
2. Give exactly ONE concise hint (2-3 sentences max).
3. Point to the specific line or variable involved.
4. Use the Socratic method — ask a question that leads the student to the fix.
5. Match the difficulty level provided."""


def _build_user_prompt(
    code: str,
    error_category: str,
    rule_hint: Optional[str],
    static_findings: list,
    difficulty: str,
) -> str:
    """Build the user prompt from structured internal data."""
    findings_text = ""
    if static_findings:
        findings_text = "\n".join(
            f"  - Line {f.get('line', '?')}: [{f.get('rule_id')}] {f.get('message')}"
            for f in static_findings[:3]
        )

    return f"""Student's code:
```python
{code}
