"""
Layer 4: LLM Enricher — async GPT-based mentor hint refinement.

Called ONLY AFTER Layers 1-3 have already returned an instant response
to the user. This layer takes the structured findings and refines the
hint into a context-aware, pedagogical explanation.

This is a BONUS enrichment — the system works fully without it.
"""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("codekraft.llm_enricher")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


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
    """Build the GPT user prompt from structured internal data."""
    findings_text = ""
    if static_findings:
        findings_text = "\n".join(
            f"  - Line {f.get('line', '?')}: [{f.get('rule_id')}] {f.get('message')}"
            for f in static_findings[:3]  # cap at 3 findings
        )

    return f"""Student's code:
```python
{code}
```

Internal analysis:
  Error category: {error_category}
  Difficulty level: {difficulty}
  Static findings:
{findings_text or '  (none)'}

Our rule-based hint: "{rule_hint or 'N/A'}"

Task: Refine this into a single, personalized Socratic hint for the student. Do NOT repeat the rule-based hint verbatim — build on it with specific line references from their code."""


async def enrich(
    code: str,
    error_category: str,
    rule_hint: Optional[str] = None,
    static_findings: Optional[list] = None,
    difficulty: str = "intermediate",
) -> dict:
    """
    Generate an LLM-enriched mentor hint.

    This is called AFTER the instant response is already sent to the user.
    The result is delivered as a secondary, optional enrichment.

    Returns:
        {
            "enriched_hint": str,
            "model": str,
            "source": "gpt" | "skipped"
        }
    """
    if not OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not set — skipping LLM enrichment")
        return {
            "enriched_hint": rule_hint or "",
            "model": "none",
            "source": "skipped",
        }

    user_prompt = _build_user_prompt(
        code=code,
        error_category=error_category,
        rule_hint=rule_hint,
        static_findings=static_findings or [],
        difficulty=difficulty,
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.6,
                    "max_tokens": 100,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            return {
                "enriched_hint": content,
                "model": OPENAI_MODEL,
                "source": "gpt",
            }

    except Exception as e:
        logger.error(f"LLM enrichment failed: {e}")
        return {
            "enriched_hint": rule_hint or "",
            "model": "none",
            "source": "skipped",
            "error": str(e),
        }
