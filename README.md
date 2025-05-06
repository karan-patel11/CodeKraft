# CodeKraft
Hybrid Architecture for Intelligent Code Error Feedback

A CodeT5-based deep learning assistant that pinpoints Python code errors and delivers mentor-style hints via the OpenAI GPT API—so new coders can learn by solving, not by copying.

## 🚀 Project Overview

New Python learners often get stalled by cryptic red-lined errors. CodeKraft fine-tunes Salesforce’s CodeT5 on a curated subset of the TSSB-3M-ext dataset, focusing exclusively on easy and medium difficulty bugs. Once CodeT5 predicts a suggested fix, the pipeline calls OpenAI’s GPT API to craft a hint that nudges the student toward understanding the root problem without revealing the full answer.

## 🔧 Key Features

* **Error Localization**: Learns common syntactic and logical bug patterns (SStuB) to isolate the problematic snippet.
* **Difficulty-Focused Training**: Filters for low/medium difficulty examples, boosting reliability on beginner-level mistakes.
* **Hybrid Architecture**: Combines a specialized code-generation model (CodeT5) with a conversational LLM mentor (OpenAI GPT).
* **Efficient Inference**: Applies input truncation and batching for sub-second responses on GPU (or CPU fallback).
* **Modular Pipeline**: Clear separation of data preprocessing, model fine-tuning, and inference for easy customization.

## 📈 Evaluation Metrics

*(Exact-match accuracy is intentionally omitted; see below for more informative metrics.)*

* **CodeBLEU**: 52.3% on the easy+medium subset (captures syntax & structure similarity)
* **Token-level F1**: 75.4% (measures partial token overlap for nuanced fixes)
* **Inference Latency**: \~0.25s per snippet on a Tesla T4 GPU

These metrics better reflect real-world hint usefulness and partial correctness than strict exact matches.

## 🛠️ Installation & Setup

```bash
git clone https://github.com/kaps117/CodeKraft.git
cd CodeKraft
pip install -r requirements.txt
```

(Optional) Authenticate with Hugging Face:

```bash
export HF_TOKEN="<your_token_here>"
```

## 🎓 Usage

1. **Fine-tune your model:**

   ```bash
   python finetune.py \
     --dataset zirui3/TSSB-3M-ext \
     --filter low medium \
     --model Salesforce/codet5-base \
     --output_dir codet5_easy_medium
   ```
2. **Run the API server:**

   ```bash
   uvicorn serve:app --reload
   ```
3. **Get a hint:**

   ```bash
   curl -X POST http://localhost:8000/fix \
     -H "Content-Type: application/json" \
     -d '{"pattern": "MissingColon", "buggy": "for i in range(5) print(i)"}'
   ```

Response:

```json
{"hint": "It looks like your loop header is missing a colon at the end. Try adding `:` after `range(5)` to define the loop block."}
```

## 🔮 Future Directions

* Expand to high-difficulty bug patterns via curriculum learning
* Dashboard for educator analytics on common errors
* Multi-language support beyond Python

## 📄 License

[MIT License](LICENSE)
