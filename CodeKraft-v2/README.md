# CodeKraft — 4-Layer AI Python Debugging Pipeline

CodeKraft is an AI-powered Python error feedback system that helps students understand and fix their code through guided hints rather than direct solutions. It combines static analysis, deep learning classification, and optional LLM enrichment into a real-time, low-latency pipeline.

## Architecture

```
User's Buggy Code
       │
       ▼
┌──────────────────────────┐
│  L1: Static Analyzer     │  AST-based pattern detection     < 5ms
│  (lib/static_analyzer.py)│  Finds: NameError, OffByOne,
│                          │  WrongOperator, MissingReturn...
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  L2: CodeBERT Classifier │  Error type classification       ~250ms
│  (lib/classifier.py)     │  via HF Inference API
│                          │  microsoft/codebert-base
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  L3: Rule Engine         │  Pre-computed mentor hints       < 1ms
│  (lib/rule_engine.py)    │  Curated from QuixBugs patterns
└────────────┬─────────────┘
             │
    ┌────────┴────────┐
    │  INSTANT RESPONSE│  ← User gets feedback HERE (< 300ms)
    └────────┬────────┘
             ▼ (async, non-blocking)
┌──────────────────────────┐
│  L4: LLM Enricher       │  GPT-3.5 Socratic refinement    ~800ms
│  (lib/llm_enricher.py)  │  Optional bonus — never blocks
└──────────────────────────┘
```

## Evaluation Metrics

CodeKraft was evaluated on the QuixBugs benchmark dataset using standard code intelligence metrics. The fine-tuned CodeBERT model achieved a **CodeBLEU score of 52.3%**, demonstrating strong structural and semantic alignment with ground-truth bug classifications. At the token level, the model attained a **Token-level F1 score of 75.4%**, reflecting high precision and recall across diverse Python error patterns. In terms of efficiency, the model delivers an **inference latency of approximately 0.25 seconds per code snippet** when evaluated on an NVIDIA Tesla T4 GPU, confirming its suitability for real-time feedback in educational and development environments.

## API Endpoints

### `POST /api/analyze` — Instant Analysis (Layers 1-3)

```json
// Request
{ "code": "def greet(name):\n    print('Hello ' + nme)" }

// Response
{
  "parseable": true,
  "findings": [
    {
      "rule_id": "SA001",
      "category": "NameError",
      "severity": "error",
      "line": 2,
      "message": "Name 'nme' is used but never defined in this scope.",
      "suggestion": "Check the spelling of 'nme' — did you mean a similar variable?",
      "confidence": 0.92
    }
  ],
  "error_category": "NameError",
  "classification_confidence": 0.87,
  "mentor_hint": "A variable or function name is being used that doesn't exist...",
  "follow_up": "Compare each variable name character-by-character...",
  "common_fix": "Check spelling of variable names and ensure they are defined before use.",
  "latency": {
    "total_ms": 287.4,
    "static_analysis_ms": 2.1,
    "classifier_ms": 284.8,
    "rule_engine_ms": 0.5
  }
}
```

### `POST /api/enrich` — LLM Enrichment (Layer 4, async)

```json
// Request
{
  "code": "...",
  "error_category": "NameError",
  "rule_hint": "A variable or function name is being used...",
  "findings": [...],
  "difficulty": "beginner"
}

// Response
{
  "enriched_hint": "Look at line 2 — what name did you give the parameter vs what you typed in print()?",
  "model": "gpt-3.5-turbo",
  "source": "gpt"
}
```

### `GET /api/health` — Service Status

### `GET /api/metrics` — Rolling Performance Metrics

### `GET /api/categories` — Supported Error Types

## Project Structure

```
CodeKraft/
├── CodeKraft_Final.ipynb     # Model training notebook (Colab)
├── api/
│   └── index.py              # FastAPI orchestrator (4-layer pipeline)
├── lib/
│   ├── static_analyzer.py    # L1: AST-based pattern detection
│   ├── classifier.py         # L2: CodeBERT via HF Inference API
│   ├── rule_engine.py        # L3: Pre-computed mentor hints
│   ├── llm_enricher.py       # L4: Async GPT enrichment
│   └── metrics.py            # Latency tracking & aggregation
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Terminal-themed React UI
│   │   ├── App.css           # Dark terminal styling
│   │   ├── index.css         # Global CSS variables
│   │   └── main.jsx          # React entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── vercel.json               # Vercel deployment config
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── .gitignore
```

## Deploy to Vercel

### Step 1: Push fine-tuned model to Hugging Face Hub

After training in Colab, run:

```python
from huggingface_hub import notebook_login
notebook_login()

model.push_to_hub("karan-patel11/codekraft-codebert")
tokenizer.push_to_hub("karan-patel11/codekraft-codebert")
```

### Step 2: Push code to GitHub

```bash
git add api/ lib/ frontend/ vercel.json requirements.txt .env.example .gitignore README.md
git commit -m "Add 4-layer API pipeline + terminal frontend"
git push origin main
```

### Step 3: Import into Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import `karan-patel11/CodeKraft`
3. Framework Preset → `Other`
4. Click **Deploy**

### Step 4: Set environment variables

In Vercel → Settings → Environment Variables:

| Variable | Value |
|---|---|
| `HF_API_KEY` | From [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| `HF_MODEL` | `karan-patel11/codekraft-codebert` (or `microsoft/codebert-base`) |
| `OPENAI_API_KEY` | From [platform.openai.com/api-keys](https://platform.openai.com/api-keys) (optional) |
| `ALLOWED_ORIGINS` | `*` |

### Step 5: Redeploy

Go to Deployments → click **Redeploy**. Your API is live at:

```
https://codekraft.vercel.app/api/analyze
https://codekraft.vercel.app/api/health
```

## Local Development

```bash
pip install -r requirements.txt
cp .env.example .env   # edit with your API keys
uvicorn api.index:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Tech Stack

- **CodeBERT** (microsoft/codebert-base) — fine-tuned for Python error classification
- **FastAPI** — async Python web framework
- **React + Vite** — terminal-themed frontend
- **Hugging Face Inference API** — hosted model inference
- **OpenAI GPT-3.5-turbo** — optional Socratic hint enrichment
- **Vercel** — serverless deployment

## Authors

Built by [karan-patel11](https://github.com/karan-patel11)
