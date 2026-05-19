---
marp: true
theme: default
paginate: true
---

# IAM Policy Generator
## QLoRA Fine-tuned Llama 3.2 3B

**Shahul SHAIK** — Senior IT Audit / AI Governance (CISA, 15 years)
OpenClassrooms Projet 14 — May 2026

---

# The Problem

Writing AWS IAM policies is **error-prone and time-consuming**

- Engineers copy-paste policies without understanding the security implications
- Over-permissive policies are the #1 cause of cloud data breaches
- Mapping policies to compliance frameworks (NIST, ISO 27001) is manual work
- Junior engineers lack the domain knowledge to apply least-privilege correctly

> *"The average IAM policy in production grants 3–5x more permissions than needed."*

---

# The Solution

**Plain-English requirement → IAM Policy + NIST controls + Risk notes**

Input:
> *"The finance team needs read-only access to S3 bucket prod-invoices. No delete. MFA required."*

Output:
- A valid, least-privilege IAM policy JSON
- Relevant NIST SP 800-53 Rev5 control IDs (AC-3, AC-6, SC-7)
- A one-sentence risk note for the audit trail

---

# Demo Output (actual model output)

```json
{
  "policy": {
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::prod-invoices", "arn:aws:s3:::prod-invoices/*"],
      "Condition": { "Bool": { "aws:MultiFactorAuthPresent": "true" } }
    }]
  },
  "nist_controls": ["AC-3", "AC-6", "SC-7"],
  "risk_notes": "MFA requirement prevents unauthorized data access.
                 Resource scope limited to the specific bucket."
}
```

---

# Technical Architecture

```
Plain-English requirement
        │
        ▼
  Llama 3.2 3B Instruct          ← Meta open-source base model
  (QLoRA fine-tuned, 4-bit)      ← LoRA adapters trained on domain data
        │
        ▼
┌─────────────────────────────┐
│  IAM Policy JSON            │  ← valid, deployable AWS policy
│  NIST SP 800-53 controls    │  ← AC-3, AC-6, SC-28, IA-2 …
│  Risk notes                 │  ← one-sentence audit artifact
└─────────────────────────────┘
```

**Stack:** Python · unsloth · trl · HuggingFace · Gemini API · BeautifulSoup4 · Gradio

---

# Dataset Construction — 3 Layers

| Layer | Source | Count | Role |
|---|---|---|---|
| Seed examples | Hand-crafted by domain expert | 20 | Few-shot anchors, quality baseline |
| AWS documentation | Scraped from 12 official service pages | 32 | Real-world patterns |
| Synthetic | Gemini Flash Lite, few-shot prompted | 450 | Volume and diversity |

**Total: 502 examples — 451 train / 51 test**

Services: S3, EC2, Lambda, RDS, DynamoDB, IAM, KMS, SQS, SNS, CloudWatch, CloudTrail, ECS, CloudFormation, API Gateway, VPC, Route53

---

# Dataset Quality

Automated quality audit before training:

| Metric | Result |
|---|---|
| Structural validity | 502 / 502 (100%) |
| Avg IAM actions per policy | 4.7 |
| Has Condition block | 93% |
| Has Deny statement | 23% |
| Multiple Statement blocks | 35% |
| Avg NIST controls per example | 2.7 |

Prompting strategy: top-5 complexity-scored seeds as few-shot context + strict system instruction requiring specific ARNs, conditions, and deny statements.

---

# Fine-tuning Approach — QLoRA

**Why QLoRA?**
Llama 3.2 3B has 3.2 billion parameters — full fine-tuning requires ~24 GB VRAM.
QLoRA makes it fit on a free Colab T4 (16 GB).

| Technique | Effect |
|---|---|
| 4-bit quantisation (bitsandbytes) | Cuts base model memory from ~12 GB to ~3 GB |
| LoRA adapters (rank 16) | Only 9.2M parameters trained (0.28% of total) |
| Gradient accumulation (steps=4) | Simulates larger batch size on limited VRAM |

**Result:** full fine-tuning behaviour at a fraction of the compute cost.

---

# Training Run

| Parameter | Value |
|---|---|
| Base model | `unsloth/llama-3.2-3b-instruct` |
| LoRA rank | 16 |
| Target modules | q_proj, k_proj, v_proj, o_proj |
| Learning rate | 2e-4 |
| Epochs | 3 |
| Batch size (effective) | 8 (2 × 4 accumulation steps) |
| Training examples | 451 |
| Total steps | 171 |
| Final training loss | 0.617 |
| Hardware | Google Colab T4 (free tier) |
| **Wall-clock time** | **~8 minutes** |

---

# Evaluation Results

Tested on 51 held-out examples (10% split):

| Metric | Base Llama 3.2 3B | Fine-tuned | Change |
|---|---|---|---|
| JSON validity | 78.4% | **96.1%** | +17.7 pp |
| NIST mapping recall | 0.0% | **53.3%** | +53.3 pp |
| ROUGE-L | 0.326 | **0.589** | +0.263 |

**Key finding:** the base model has zero concept of NIST control mapping.
Fine-tuning teaches the output schema and the domain-specific compliance vocabulary — skills not present in the base model's pre-training.

---

# What Fine-tuning Actually Changed

| Capability | Base model | Fine-tuned |
|---|---|---|
| Output format | Free-form prose or malformed JSON | Structured JSON every time |
| NIST controls | Never produced | Contextually correct 53% of the time |
| Specific ARNs | Rare — tends to use `*` | Consistent bucket/table/function ARNs |
| MFA conditions | Rarely applied | Applied when requirement mentions MFA |
| Deny statements | Almost never | Generated when scenario warrants it |
| Risk notes | Not produced | Consistent governance artifact |

---

# Limitations

- **AWS IAM only** — does not cover Azure RBAC or GCP IAM
- **No Service Control Policies (SCPs)** — org-level guardrails not modelled
- **ARN hallucination** — may generate plausible but non-existent resource names for custom resources
- **NIST recall at 53%** — correct direction, not exhaustive; human review required
- **Training set size** — 502 examples is small; a larger dataset would improve recall and reduce hallucinations
- **All outputs must be reviewed by a qualified engineer before production use**

---

# Skills Demonstrated

This project bridges **IT Audit domain expertise** and **ML engineering**:

| Domain | Skills |
|---|---|
| AI/ML | LLM fine-tuning (QLoRA), instruction tuning, dataset construction, evaluation metrics |
| Cloud Security | AWS IAM policy design, least-privilege, NIST SP 800-53 control mapping |
| Engineering | Python, HuggingFace ecosystem, Gemini API, web scraping, data pipelines |
| AI Governance | Model cards, dataset cards, bias/risk assessment, human-review disclaimers |

**Relevance for AI Governance roles:** demonstrates ability to build, evaluate, and govern domain-specific AI tools — not just use them.

---

# Project Artefacts

| Artefact | Description |
|---|---|
| `data/raw/seed_examples.jsonl` | 20 hand-crafted reference examples |
| `data/processed/train.jsonl` | 451-example training set |
| `notebooks/02_finetune.ipynb` | Reproducible Colab training notebook |
| `notebooks/03_evaluate.ipynb` | Before/after evaluation with 4 metrics |
| `iam-policy-adapter/` | Fine-tuned LoRA weights (~50 MB) |
| `results/eval_results.json` | Quantitative evaluation results |
| `model_card.md` | Governance document — intended use, risks, limitations |
| `app.py` | Gradio demo (deployable to HuggingFace Spaces) |

---

# Thank You

**Shahul SHAIK**
Senior IT Audit / AI Governance — CISA, 15 years

*OpenClassrooms Projet 14 — AI Engineer programme*
*Targeting AI Governance / IT Audit roles — Switzerland — Available July 2026*

---

> *"The same domain knowledge that makes a good auditor — understanding what access is necessary and what is excessive — is exactly what makes a good AI governance practitioner."*
