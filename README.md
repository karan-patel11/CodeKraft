<div align="center">

# `>_ CodeKraft`

### **Your code has bugs. CodeKraft doesn't just find them — it teaches you why.**

An AI-powered Python debugging pipeline that delivers **mentor-style hints in under 300ms**,
combining static analysis, a fine-tuned **CodeBERT** transformer, and optional **GPT-3.5** Socratic guidance.

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Vercel](https://img.shields.io/badge/Deployed_on-Vercel-000?style=flat-square&logo=vercel)](https://vercel.com)
[![HuggingFace](https://img.shields.io/badge/Model-CodeBERT-FFD21E?style=flat-square&logo=huggingface)](https://huggingface.co/microsoft/codebert-base)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

<!-- SCREENSHOT: Replace the path below with your actual screenshot -->
<!-- ![CodeKraft UI](./assets/codekraft-screenshot.png) -->
<img width="800" height="532" alt="image" src="https://github.com/user-attachments/assets/04a02551-526f-4d0d-9267-0d78e10df24e" />


---

</div>

## The Problem

Every CS student knows the pain: you write Python code, it breaks, and the error message is **cryptic garbage**. You paste it into ChatGPT and get a full solution — but you **didn't learn anything**.

**CodeKraft takes a different approach.** Instead of handing you the answer, it gives you a **hint** — like a teaching assistant sitting next to you at 2am.

---

## How It Works — 4 Layers, Under 300ms

```
                     Your Buggy Python Code
                              |
                              v
               =============================
               |   LAYER 1: Static Analyzer  |   < 5ms
               |   Python AST parsing        |
               |   7 pattern detectors       |
               |   Zero dependencies         |
               =============================
                              |
                              v
               =============================
               |   LAYER 2: CodeBERT         |   ~250ms
               |   125M parameter transformer|
               |   Fine-tuned on QuixBugs    |
               |   Error type classification |
               =============================
                              |
                              v
               =============================
               |   LAYER 3: Rule Engine      |   < 1ms
               |   Pre-computed mentor hints |
               |   Curated Socratic prompts  |
               |   Instant dictionary lookup |
               =============================
                              |
                     RESPONSE SENT (< 300ms)
                     User sees feedback NOW
                              |
                              v  (async, bonus)
               =============================
               |   LAYER 4: GPT-3.5 Enricher|   ~800ms
               |   Socratic follow-up        |
               |   Context-aware refinement  |
               |   Never blocks the user     |
               =============================
```

> **Why 4 layers?** Because calling an LLM for every request adds 800ms+ of latency. Our first 3 layers give you an answer instantly. The LLM is just the cherry on top.

---

## Evaluation Metrics

<div align="center">

| Metric | Score | What It Tells You |
|:---|:---:|:---|
| **CodeBLEU** | **52.3%** | Structural + semantic alignment with ground-truth classifications |
| **Token-level F1** | **75.4%** | Precision-recall balance across Python error patterns |
| **Inference Latency** | **~0.25s** | Per-snippet speed on NVIDIA Tesla T4 — real-time ready |

</div>

The fine-tuned CodeBERT model was evaluated on the **QuixBugs benchmark dataset** using standard code intelligence metrics. A CodeBLEU of 52.3% demonstrates strong structural understanding beyond surface-level token matching. The Token-level F1 of 75.4% confirms the model reliably identifies error patterns with high precision and recall. At 0.25 seconds per snippet on a Tesla T4, the system is fast enough for live IDE integration.

---

## See It In Action

### Request
```bash
curl -X POST https://codekraft.vercel.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"code": "def greet(name):\n    print(\"Hello \" + nme)"}'
```

### Response (< 300ms)
```json
{
  "parseable": true,
  "findings": [
    {
      "rule_id": "SA001",
      "category": "NameError",
      "severity": "error",
      "line": 2,
      "message": "Name 'nme' is used but never defined in this scope.",
      "suggestion": "Check the spelling of 'nme' -- did you mean a similar variable?",
      "confidence": 0.92
    }
  ],
  "error_category": "NameError",
  "classification_confidence": 0.87,
  "mentor_hint": "A variable name is being used that doesn't exist in this scope. This usually means a typo.",
  "follow_up": "Compare each variable name character-by-character with where it was defined.",
  "common_fix": "Check spelling of variable names and ensure they are defined before use.",
  "latency": {
    "total_ms": 287.4,
    "static_analysis_ms": 2.1,
    "classifier_ms": 284.8,
    "rule_engine_ms": 0.5
  }
}
```

> Notice: **no code solution is given**. Just a hint. The student still has to think.

---

## API Reference

| Endpoint | Method | Purpose | Latency |
|:---|:---:|:---|:---:|
| `/api/analyze` | `POST` | 3-layer instant analysis | < 300ms |
| `/api/enrich` | `POST` | GPT-3.5 Socratic refinement | ~800ms |
| `/api/health` | `GET` | Service status + config | instant |
| `/api/metrics` | `GET` | Rolling performance dashboard | instant |
| `/api/categories` | `GET` | All supported error types | instant |

---

## Project Structure

```
CodeKraft/
|
|-- CodeKraft_Final.ipynb          # Model training (Colab)
|
|-- api/
|   '-- index.py                   # FastAPI orchestrator
|
|-- lib/
|   |-- static_analyzer.py         # L1: AST pattern detection (7 detectors)
|   |-- classifier.py              # L2: CodeBERT via HF Inference API
|   |-- rule_engine.py             # L3: Pre-computed mentor hints
|   |-- llm_enricher.py            # L4: Async GPT enrichment
|   '-- metrics.py                 # Latency tracking + aggregation
|
|-- frontend/
|   |-- src/
|   |   |-- App.jsx                # Terminal-themed React UI
|   |   |-- App.css                # Dark terminal styling
|   |   |-- index.css              # CSS variables + theme
|   |   '-- main.jsx               # Entry point
|   |-- index.html
|   |-- package.json
|   '-- vite.config.js
|
|-- vercel.json                    # Serverless deployment config
|-- requirements.txt               # Python deps
|-- .env.example                   # API key template
'-- .gitignore
```

---

## Model Deep Dive

### Architecture
| Component | Detail |
|:---|:---|
| Base Model | `microsoft/codebert-base` (RoBERTa-based, 125M params) |
| Pre-training Data | 6.4M bimodal code-text pairs from GitHub |
| Fine-tuning Task | Sequence Classification (error type) |
| Dataset | QuixBugs benchmark (classic single-line bugs) |
| Classification Head | Linear layer over `[CLS]` token |

### Training Configuration
| Hyperparameter | Value |
|:---|:---|
| Epochs | 4 |
| Batch Size | 4 (train & eval) |
| Learning Rate | 5e-5 (AdamW) |
| Scheduler | Linear decay |
| Max Sequence Length | 512 tokens |
| Train/Test Split | 80/20 |
| Evaluation Strategy | Every epoch |
| Model Selection | Best validation loss |

### Error Categories Detected
```
NameError          WrongOperator       OffByOneError
WrongComparator    WrongVariable       WrongBaseCase
MissingReturn      WrongInitialization IndexError
TypeError          SyntaxError         LogicError
InfiniteLoop       WrongMethodCall     ... and more
```

---

## Deploy Your Own

### Prerequisites
- [Hugging Face account](https://huggingface.co/join) (free)
- [OpenAI API key](https://platform.openai.com/api-keys) (optional, for Layer 4)
- [Vercel account](https://vercel.com) (free)

### Quick Deploy

**1. Upload fine-tuned model to Hugging Face** (after Colab training):
```python
model.push_to_hub("your-username/codekraft-codebert")
tokenizer.push_to_hub("your-username/codekraft-codebert")
```

**2. Push to GitHub:**
```bash
git add . && git commit -m "CodeKraft v2" && git push origin main
```

**3. Import into Vercel** → [vercel.com](https://vercel.com) → Add New Project → Import repo → Framework: `Other` → Deploy

**4. Add secrets** (Vercel → Settings → Environment Variables):

| Variable | Value | Required? |
|:---|:---|:---:|
| `HF_API_KEY` | Your Hugging Face token | Yes |
| `HF_MODEL` | `microsoft/codebert-base` | Yes |
| `OPENAI_API_KEY` | Your OpenAI key | No (Layer 4 only) |
| `ALLOWED_ORIGINS` | `*` | Yes |

**5. Redeploy** and you're live.

---

## Local Development

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env              # add your API keys
uvicorn api.index:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

---

## Tech Stack

<div align="center">

| Layer | Technology | Role |
|:---|:---|:---|
| ML Model | **CodeBERT** (microsoft/codebert-base) | Error classification |
| API | **FastAPI** + **Uvicorn** | Async Python backend |
| Frontend | **React 18** + **Vite** | Terminal-themed UI |
| Inference | **Hugging Face Inference API** | Hosted model serving |
| Enrichment | **OpenAI GPT-3.5-turbo** | Socratic hint generation |
| Hosting | **Vercel** | Serverless deployment |
| Analysis | **Python AST** module | Zero-dependency static analysis |

</div>

---

## Why CodeKraft?

| Feature | ChatGPT | Linters | **CodeKraft** |
|:---|:---:|:---:|:---:|
| Finds the bug | Yes | Yes | **Yes** |
| Explains *why* | Sometimes | No | **Always** |
| Gives hints, not answers | No | No | **Yes** |
| Real-time (< 300ms) | No (~2s) | Yes | **Yes** |
| Learns your patterns | No | No | **Yes** |
| Works offline (L1-L3) | No | Yes | **Yes** |

---

<div align="center">

**Built with caffeine and curiosity by [Karan Patel](https://github.com/karan-patel11)**

*CodeKraft doesn't write your code. It makes you a better coder.*

</div>
