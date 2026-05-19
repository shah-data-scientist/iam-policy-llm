# IAM Policy Generator — QLoRA Fine-tuned Llama 3.2 3B

A fine-tuned LLM that generates **AWS IAM policies** from plain-English access control
requirements, with **NIST SP 800-53 control mappings** and risk notes.

Built as a portfolio project to demonstrate LLM fine-tuning for AI Governance / IT Audit roles.

---

## Demo

> *"Finance team needs read-only access to S3 bucket `prod-invoices`. No delete. MFA required."*

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": [
        "arn:aws:s3:::prod-invoices",
        "arn:aws:s3:::prod-invoices/*"
      ],
      "Condition": {
        "Bool": { "aws:MultiFactorAuthPresent": "true" }
      }
    }
  ]
}
```

**NIST controls:** AC-3, AC-6, SC-7  
**Risk note:** MFA requirement prevents unauthorized data access. Resource scope limited to the specific bucket and its contents.

---

## Pipeline

```
Plain-English requirement
        │
        ▼
 Llama 3.2 3B Instruct
 (QLoRA fine-tuned, 4-bit)
        │
        ▼
┌──────────────────────────┐
│  IAM Policy JSON         │
│  NIST SP 800-53 controls │
│  Risk notes              │
└──────────────────────────┘
```

---

## Dataset

Three-layer training dataset (502 examples total — 451 train / 51 test):

| Layer | Source | Count | Quality |
|---|---|---|---|
| Seed examples | Hand-crafted by domain expert | 20 | Highest |
| AWS documentation | Scraped from 12 service doc pages | 32 | High — official patterns |
| Synthetic | Gemini Flash Lite, few-shot from seeds | 450 | Good — reviewed |

Services covered: S3, EC2, Lambda, RDS, DynamoDB, IAM, KMS, Secrets Manager, SQS,
SNS, CloudWatch, CloudTrail, ECS, CloudFormation, Athena, API Gateway, VPC, Route53.

---

## Training

- **Base model:** `unsloth/llama-3.2-3b-instruct`
- **Method:** QLoRA — 4-bit quantisation, LoRA rank 16, 0.28% of parameters trained (9.2M / 3.2B)
- **Hardware:** Google Colab free T4 (16 GB VRAM) — 474 seconds (~8 min) for 451 examples × 3 epochs
- **Framework:** `unsloth` + `trl` SFTTrainer
- **Training loss:** 0.617

---

## Evaluation

Evaluated on 51 held-out test examples (10% split):

| Metric | Base Llama 3.2 3B | Fine-tuned | Change |
|---|---|---|---|
| JSON validity rate | 78.4% | **96.1%** | +17.7 pp |
| NIST mapping recall | 0.0% | **53.3%** | +53.3 pp |
| ROUGE-L | 0.326 | **0.589** | +0.263 |
| Least-privilege (strict) | 78.4% | 21.6% | see note |

> **Note on least-privilege metric:** the base model scores high because it outputs policies with empty or missing `Action` fields (technically a subset of anything). The fine-tuned model generates complete, specific action sets which differ from ground truth — valid alternatives that fail the strict subset check. The NIST recall and ROUGE-L metrics are the meaningful indicators of improvement.

---

## Project Structure

```
iam-policy-llm/
├── app.py                      ← HuggingFace Spaces entry point
├── data/
│   ├── raw/
│   │   ├── seed_examples.jsonl         ← 20 hand-crafted examples
│   │   ├── synthetic_batch_01.jsonl    ← Gemini synthetic (generated)
│   │   └── scraped_aws_docs.jsonl      ← AWS docs scraping (generated)
│   ├── processed/
│   │   ├── train.jsonl                 ← 90% split (generated)
│   │   └── test.jsonl                  ← 10% split (generated)
│   └── dataset_card.md
├── notebooks/
│   ├── 01_dataset_build.ipynb  ← run locally (needs GEMINI_API_KEY)
│   ├── 02_finetune.ipynb       ← run on Google Colab T4
│   ├── 03_evaluate.ipynb       ← before/after metrics
│   └── 04_inference_demo.ipynb ← interactive demo
├── src/
│   ├── data_utils.py           ← load/save/validate helpers
│   ├── scrape_aws_docs.py      ← AWS documentation scraper
│   ├── train.py                ← CLI training script
│   └── inference.py            ← generate_policy() function
├── model_card.md
├── data/dataset_card.md
├── results/
│   └── eval_results.json           ← quantitative evaluation output
├── docs/
│   └── presentation.md             ← Marp slide deck
└── requirements.txt
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Build the dataset (local, ~15 min)
```bash
# Set your Gemini API key
echo "GEMINI_API_KEY=your_key_here" > .env

# Run notebook 01 — generates synthetic + scrapes AWS docs
jupyter lab notebooks/01_dataset_build.ipynb
```

### 3. Train on Google Colab
Upload `data/processed/train.jsonl` to Google Drive, then open `notebooks/02_finetune.ipynb`
in Colab (free T4 runtime). Training takes ~2 hours for ~500 examples.

### 4. Run inference locally
```python
import sys
sys.path.insert(0, 'src')
from inference import generate_policy

result = generate_policy(
    "DevOps team needs to start and stop EC2 instances in eu-west-1 only. "
    "No terminate or security group changes."
)
print(result['policy'])
print(result['nist_controls'])
```

### 5. CLI training (alternative to notebook)
```bash
python src/train.py \
  --data data/processed/train.jsonl \
  --adapter iam-policy-adapter \
  --epochs 3 \
  --hub-repo your-username/llama-3.2-3b-iam-policy
```

---

## Limitations

- AWS IAM only — does not cover Azure RBAC or GCP IAM
- Does not model Service Control Policies (SCPs) or permission boundaries
- May hallucinate ARNs for non-standard or custom resources
- NIST control mappings are indicative, not exhaustive
- **All outputs must be reviewed by a qualified engineer before production use**

---

## Author

**Shahul SHAIK** — Senior IT Audit / AI Governance (CISA, 15 years)  
OpenClassrooms Projet 14 — targeting AI Governance roles, Switzerland, July 2026.
