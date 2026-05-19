# IAM Policy Generator — Project Context

## What This Is

OpenClassrooms Projet 14 — a QLoRA fine-tuned Llama 3.2 3B model that generates
AWS IAM policies from plain-English access control requirements, with NIST SP 800-53
control mappings. Built as a portfolio project to demonstrate LLM fine-tuning skills
for AI Governance / IT Audit roles (targeting Switzerland, available July 2026).

## Owner

Shahul SHAIK — Senior IT Audit / AI Governance expert (CISA, 15 years).
This project bridges domain expertise (access control, compliance frameworks) with
modern ML engineering (QLoRA, instruction tuning, LLM evaluation).

## Current Status

Phase 1 — Dataset Construction (COMPLETE ✓)

- [x] Project scaffold created (notebooks, src, data dirs)
- [x] 20 seed examples in `data/raw/seed_examples.jsonl`
- [x] Notebook 01 updated: google-genai SDK, gemini-flash-lite-latest
- [x] `src/build_dataset.py` — CLI pipeline (more reliable than nbconvert)
- [x] `data/raw/synthetic_batch_01.jsonl` — 450 Gemini synthetic examples
- [x] `data/raw/scraped_aws_docs.jsonl` — 32 real AWS doc examples
- [x] `data/processed/train.jsonl` — 451 examples (90%)
- [x] `data/processed/test.jsonl` — 51 examples (10%)

Phase 2 — Training (COMPLETE ✓)

- [x] Notebook 02 updated: Colab data upload + HuggingFace Hub push
- [x] Trained on Colab T4 — 451 examples, 3 epochs, 171 steps, loss 0.617, ~8 min
- [x] `iam-policy-adapter/` saved locally (LoRA weights ~50 MB)

Phase 3 — Evaluation & Deploy (COMPLETE ✓)

- [x] Notebook 03 run on Colab — eval_results.json saved
  - JSON validity: 78.4% → 96.1%
  - NIST recall: 0.0% → 53.3%
  - ROUGE-L: 0.326 → 0.589
- [x] Notebook 04 run on Colab — inference demo working, Gradio UI tested
- [x] README.md, model_card.md updated with real results
- [ ] Deploy `app.py` to HuggingFace Spaces (optional)

## Project Structure

```
iam-policy-llm/
├── data/
│   ├── raw/seed_examples.jsonl     ← 20 hand-crafted examples, DONE
│   ├── processed/                  ← train.jsonl + test.jsonl, not yet created
│   └── dataset_card.md
├── notebooks/
│   ├── 01_dataset_build.ipynb      ← run this first (locally or Colab)
│   ├── 02_finetune.ipynb           ← run on Google Colab free T4
│   ├── 03_evaluate.ipynb           ← before/after metrics
│   └── 04_inference_demo.ipynb     ← Gradio UI
├── src/
│   ├── data_utils.py               ← load_jsonl, format_prompt, extract_actions
│   ├── train.py                    ← CLI version of notebook 02
│   └── inference.py                ← generate_policy() function
├── model_card.md                   ← governance artifact
├── CLAUDE.md                       ← this file
└── requirements.txt
```

## Data Format

Every training example is a JSONL record:

```json
{
  "instruction": "Generate an AWS IAM policy for the following requirement",
  "input": "<plain-English access control requirement>",
  "output": {
    "policy": { "Version": "2012-10-17", "Statement": [...] },
    "nist_controls": ["AC-3", "AC-6"],
    "risk_notes": "..."
  }
}
```

See `data/raw/seed_examples.jsonl` for 20 reference examples covering S3, EC2,
DynamoDB, IAM, Secrets Manager, SQS, CloudWatch, CloudFormation, Athena, ECS,
RDS, Lambda, KMS, SNS, Config, Route53, cross-account, and break-glass patterns.

## Training Approach

- **Base model:** `unsloth/llama-3.2-3b-instruct`
- **Method:** QLoRA (4-bit quantisation, LoRA rank 16)
- **GPU:** Google Colab free tier T4 (~2 hours for 1000 examples, 3 epochs)
- **Framework:** `unsloth` + `trl` SFTTrainer

Key hyperparameters (in notebook 02 and src/train.py):
- `r=16`, `lora_alpha=16`, target modules: q/v/k/o proj
- `learning_rate=2e-4`, `per_device_train_batch_size=2`, `gradient_accumulation_steps=4`

## Evaluation Metrics (notebook 03)

1. **JSON validity rate** — does the model output parseable JSON?
2. **Least-privilege compliance** — are granted actions a subset of ground truth?
3. **NIST mapping accuracy** — do predicted controls match labelled controls?
4. **ROUGE-L** — lexical overlap with ground truth output

## Immediate Next Step

Project is functionally complete. Optional remaining step:
deploy `app.py` to HuggingFace Spaces for a public demo link.

To regenerate the dataset from scratch:
```bash
python src/build_dataset.py
```

## Stack

| Component | Tool |
|---|---|
| Fine-tuning | unsloth + trl |
| Base model | Llama 3.2 3B Instruct |
| Evaluation | lm-eval-harness + custom metrics |
| Demo UI | Gradio |
| Hosting | HuggingFace Hub (adapter) + HuggingFace Spaces (demo) |