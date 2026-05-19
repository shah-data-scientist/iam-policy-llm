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

Phase 1 — Dataset Construction (in progress)

- [x] Project scaffold created (notebooks, src, data dirs)
- [x] 20 seed examples in `data/raw/seed_examples.jsonl`
- [ ] Scale to ~500 examples via GPT-4 synthetic generation (notebook 01)
- [ ] Train/test split → `data/processed/train.jsonl` + `data/processed/test.jsonl`
- [ ] QLoRA training on Google Colab (notebook 02)
- [ ] Evaluation framework (notebook 03)
- [ ] Gradio demo + HuggingFace Spaces deploy (notebook 04)

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

Run `notebooks/01_dataset_build.ipynb` to expand seed examples to ~500 using GPT-4.
Requires `OPENAI_API_KEY` environment variable. Review synthetic outputs manually
before saving to `data/raw/synthetic_batch_01.jsonl`, then run the merge + split cells.

## Stack

| Component | Tool |
|---|---|
| Fine-tuning | unsloth + trl |
| Base model | Llama 3.2 3B Instruct |
| Evaluation | lm-eval-harness + custom metrics |
| Demo UI | Gradio |
| Hosting | HuggingFace Hub (adapter) + HuggingFace Spaces (demo) |