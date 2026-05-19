# IAM Policy Generator — Fine-tuned LLM

A QLoRA fine-tuned Llama 3.2 3B model that generates AWS IAM policies from plain-English requirements, with NIST SP 800-53 control mappings.

## What It Does

```
Input:  "Finance team needs read-only access to S3 invoices bucket,
         no delete, MFA required"

Output: IAM JSON policy + NIST control mapping + risk notes
```

## Project Structure

```
iam-policy-llm/
├── data/
│   ├── raw/                    # source data (AWS docs, synthetic)
│   ├── processed/              # cleaned JSONL training files
│   └── dataset_card.md         # data provenance
├── notebooks/
│   ├── 01_dataset_build.ipynb  # dataset curation
│   ├── 02_finetune.ipynb       # QLoRA training (Google Colab)
│   ├── 03_evaluate.ipynb       # before/after evaluation
│   └── 04_inference_demo.ipynb # end-user demo
├── src/
│   ├── data_utils.py           # dataset cleaning helpers
│   ├── train.py                # training script (CLI)
│   └── inference.py            # local inference
├── model_card.md
└── requirements.txt
```

## Stack

| Component | Tool |
|---|---|
| Base model | Llama 3.2 3B Instruct |
| Fine-tuning | unsloth + trl (SFTTrainer) |
| Quantisation | QLoRA (4-bit) |
| GPU | Google Colab free tier (T4) |
| Evaluation | lm-eval-harness + custom metrics |
| Serving | Ollama (local) / HuggingFace Spaces |

## Evaluation Results

| Metric | Base Llama 3.2 | Fine-tuned |
|---|---|---|
| Valid JSON output | — | — |
| Correct least-privilege | — | — |
| NIST mapping accuracy | — | — |
| ROUGE-L | — | — |

*Results will be filled after training.*

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```python
from src.inference import generate_policy

policy = generate_policy(
    "The data engineering team needs read and list access to "
    "the s3://prod-analytics bucket. No write or delete. MFA required."
)
print(policy)
```

## Limitations

- AWS IAM only (not Azure / GCP)
- Requires human review before production use
- May hallucinate ARNs for non-standard resources

## Author

Shahul SHAIK — AI Governance & IT Audit