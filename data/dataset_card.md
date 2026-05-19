# Dataset Card: IAM Policy Training Data

## Overview

Instruction-tuning dataset for AWS IAM policy generation with NIST SP 800-53 mappings.

## Format

JSONL — one example per line:

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

## Sources

| File | Source | Count | Notes |
|---|---|---|---|
| raw/aws_docs_examples.jsonl | AWS IAM User Guide | ~200 | Public documentation |
| raw/synthetic_gpt4.jsonl | GPT-4 generated | ~800 | Manually reviewed |
| processed/train.jsonl | Combined + cleaned | ~900 | 90% split |
| processed/test.jsonl | Combined + cleaned | ~100 | 10% split |

## Curation Process

1. Scraped AWS IAM policy examples from public documentation
2. Generated synthetic examples using GPT-4 with structured prompts
3. Manually reviewed all synthetic examples for correctness
4. Removed duplicates and malformed JSON
5. Split 90/10 train/test, stratified by policy complexity

## Known Limitations

- AWS IAM only
- Skewed toward S3, EC2, Lambda — fewer examples for niche services
- NIST mappings validated against SP 800-53 Rev 5 only