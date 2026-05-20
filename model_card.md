# Model Card: IAM Policy Generator

## Model Details

- **Base model:** Llama 3.2 3B Instruct (Meta)
- **Fine-tuning method:** QLoRA (rank 16, 4-bit quantisation)
- **Framework:** unsloth + trl SFTTrainer
- **Task:** Instruction-following — IAM policy generation

## Intended Use

Generate **draft** AWS IAM policies from plain-English access control requirements, with NIST SP 800-53 control mappings and risk notes.

**NOT for direct production use.** All outputs must be reviewed by a qualified engineer or auditor before deployment.

## Training Data

| Source | File | Type | Count |
|---|---|---|---|
| Hand-crafted seed examples | `data/raw/seed_examples.jsonl` | Human / domain expert | 20 |
| AWS documentation scraping | `data/raw/scraped_aws_docs.jsonl` | Public / official | 32 |
| Gemini Flash Lite synthetic | `data/raw/synthetic_batch_01.jsonl` | Synthetic, reviewed | 450 |

**Total:** 502 examples — 451 train / 51 test (90/10 split, random_state=42)

- No PII in training data
- No proprietary or client data
- Synthetic examples generated with Gemini Flash Lite using top-5 complexity-scored seeds as few-shot context
- Dataset card: [data/dataset_card.md](data/dataset_card.md)

## Limitations

- AWS IAM only — does not cover Azure RBAC or GCP IAM
- Does not account for Service Control Policies (SCPs) or permission boundaries
- May hallucinate ARNs for non-standard or custom resources
- NIST control mappings are indicative, not exhaustive

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Over-permissive policy generated | Medium | `policy_validator.py` flags wildcard actions and privilege escalation as HIGH severity |
| Wildcard actions (*) in output | Low | `policy_validator.py` `wildcard_action` check — blocks HIGH severity outputs |
| Privilege escalation via IAM/STS actions | Medium | `policy_validator.py` `privilege_escalation` check — flags iam:*, sts:*, PassRole |
| Missing Condition blocks | Medium | `policy_validator.py` `missing_condition` check — MEDIUM severity warning |
| ARN hallucination | Medium | Unmitigated — validate ARNs against AWS account inventory before deployment |
| PII in prompt logged | Low | Inference runs locally or on private Colab session |
| Model used without review | Medium | Mandatory disclaimer in UI; `policy_validator.py` severity rating surfaces review need |

See [docs/red_team_report.md](docs/red_team_report.md) for the full adversarial evaluation covering 20 attacks across 4 categories.

## Evaluation

Evaluated on 51 held-out test examples. See [notebooks/03_evaluate.ipynb](notebooks/03_evaluate.ipynb) for full methodology.

| Metric | Base Llama 3.2 3B | Fine-tuned (QLoRA) |
|---|---|---|
| JSON validity rate | 78.4% | **96.1%** |
| NIST mapping recall | 0.0% | **53.3%** |
| ROUGE-L | 0.326 | **0.589** |

**Training details:** 451 examples, 3 epochs, 171 steps, final loss 0.617. Hardware: Google Colab T4 (16 GB), runtime ~8 minutes. Trainable parameters: 9.2M / 3.22B (0.28%).

## Adversarial Evaluation

20 adversarial prompts were tested across four attack categories: prompt injection, privilege escalation, policy manipulation, and compliance bypass. Key findings:

- **Prompt injection resistance:** strong — instruction-tuning suppresses most override attempts
- **Privilege escalation:** model fulfils what it is asked — over-permissive inputs yield over-permissive outputs; caught by `policy_validator.py`
- **ARN hallucination:** unmitigated — cannot be detected by static validation alone

Full methodology and findings: [docs/red_team_report.md](docs/red_team_report.md)
Results data: [results/red_team_results.json](results/red_team_results.json)

## Ethical Considerations

Fine-tuning on access control policy generation carries a dual-use risk: the same model could assist in crafting overly permissive policies. Mitigations applied:

- `src/policy_validator.py` detects and flags HIGH/MEDIUM severity outputs automatically
- Red-teaming report documents attack surface and residual risks
- Model card and demo UI include a mandatory human-review disclaimer
- Model weights published with a responsible-use notice