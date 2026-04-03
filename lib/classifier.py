"""
Layer 2: CodeBERT Classifier — error type classification via HF Inference API.

Calls the fine-tuned CodeBERT model hosted on Hugging Face to classify
the error type of a given Python code snippet. This layer runs AFTER
static analysis and uses those findings to enrich its input.

Expected latency: ~250ms (HF Inference API, warm model).
                  ~15-30s (cold start, first call after idle).
"""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("codekraft.classifier")

# ── Config ────────────────────────────────────────────────────────────────────
HF_API_KEY = os.getenv("HF_API_KEY", "")

# Your fine-tuned model on HF Hub. After running the Colab notebook:
#   model.push_to_hub("karan-patel11/codekraft-codebert")
#   tokenizer.push_to_hub("karan-patel11/codekraft-codebert")
#
# Falls back to base CodeBERT (zero-shot, lower accuracy) if not set.
HF_MODEL = os.getenv("HF_MODEL", "microsoft/codebert-base")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"


async def classify(code: str, static_category: Optional[str] = None) -> dict:
    """
    Classify the error type of a Python code snippet.

    Args:
        code: The buggy Python source code.
        static_category: Optional hint from the static analyzer (used as
                         a prefix to improve classification accuracy).

    Returns:
        {
            "predicted_label": str,      # e.g. "OffByOneError"
            "confidence": float,         # 0.0 – 1.0
            "all_scores": [...],         # full label distribution
            "model": str,                # model identifier
            "source": "codebert" | "static_fallback"
        }
    """
    if not HF_API_KEY:
        logger.warning("HF_API_KEY not set — falling back to static analysis category")
        return _static_fallback(static_category)

    # Prepend static category as a classification hint (improves accuracy)
    input_text = code
    if static_category:
        input_text = f"[{static_category}] {code}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                HF_API_URL,
                headers={"Authorization": f"Bearer {HF_API_KEY}"},
                json={"inputs": input_text},
            )

            # Handle model loading (cold start)
            if resp.status_code == 503:
                body = resp.json()
                wait_time = body.get("estimated_time", 20)
                logger.info(f"Model loading, estimated wait: {wait_time}s")
                return {
                    "predicted_label": static_category or "Unknown",
                    "confidence": 0.0,
                    "all_scores": [],
                    "model": HF_MODEL,
                    "source": "static_fallback",
                    "model_loading": True,
                    "estimated_wait": wait_time,
                }

            resp.raise_for_status()
            data = resp.json()

            # HF text-classification returns [[{"label": ..., "score": ...}, ...]]
            if isinstance(data, list) and data:
                scores = data[0] if isinstance(data[0], list) else data
                if scores and isinstance(scores[0], dict):
                    top = max(scores, key=lambda s: s.get("score", 0))
                    return {
                        "predicted_label": top["label"],
                        "confidence": round(top["score"], 4),
                        "all_scores": [
                            {"label": s["label"], "score": round(s["score"], 4)}
                            for s in sorted(scores, key=lambda x: -x.get("score", 0))
                        ],
                        "model": HF_MODEL,
                        "source": "codebert",
                    }

            logger.warning(f"Unexpected HF response shape: {type(data)}")
            return _static_fallback(static_category)

    except httpx.HTTPStatusError as e:
        logger.error(f"HF API error {e.response.status_code}: {e.response.text}")
        return _static_fallback(static_category)
    except Exception as e:
        logger.error(f"Classifier failed: {e}")
        return _static_fallback(static_category)


def _static_fallback(category: Optional[str]) -> dict:
    """Fallback when HF API is unavailable — uses static analysis category."""
    return {
        "predicted_label": category or "Unknown",
        "confidence": 0.6 if category else 0.0,
        "all_scores": [],
        "model": "static-analysis",
        "source": "static_fallback",
    }
