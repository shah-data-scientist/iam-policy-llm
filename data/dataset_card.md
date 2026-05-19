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
| raw/seed_examples.jsonl | Hand-crafted (domain expert) | 20 | Covers 18 AWS services |
| raw/scraped_aws_docs.jsonl | AWS service documentation | ~50–100 | Scraped via BeautifulSoup, enriched with Gemini |
| raw/synthetic_batch_01.jsonl | Gemini 1.5 Flash generated | ~500 | 10 service themes × 5 batches × 10 examples |
| processed/train.jsonl | Combined + cleaned | ~520–560 | 90% split |
| processed/test.jsonl | Combined + cleaned | ~55–60 | 10% split |

## Curation Process

1. 20 seed examples hand-crafted by a senior IT Audit / AI Governance expert
2. Scraped real IAM policy JSON from 12 AWS service documentation pages
3. Used Gemini 1.5 Flash (temp=0.2) to generate plain-English `input` and NIST mappings for scraped policies
4. Generated ~500 synthetic examples using Gemini 1.5 Flash (temp=0.8) with seeds as few-shot context
5. Manually reviewed all synthetic and scraped outputs for correctness
6. Removed duplicates and malformed JSON
7. Split 90/10 train/test with fixed random seed (42)

## Known Limitations

- AWS IAM only
- Skewed toward S3, EC2, Lambda — fewer examples for niche services
- NIST mappings validated against SP 800-53 Rev 5 only