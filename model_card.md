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

| Source | Type | Size |
|---|---|---|
| AWS IAM documentation examples | Public | ~200 examples |
| Synthetic (GPT-4 bootstrapped, manually reviewed) | Synthetic | ~800 examples |

- No PII in training data
- No proprietary or client data
- Dataset card: [data/dataset_card.md](data/dataset_card.md)

## Limitations

- AWS IAM only — does not cover Azure RBAC or GCP IAM
- Does not account for Service Control Policies (SCPs) or permission boundaries
- May hallucinate ARNs for non-standard or custom resources
- NIST control mappings are indicative, not exhaustive

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Over-permissive policy generated | Medium | Evaluation suite flags over-provisioning |
| Wildcard actions (*) in output | Low | Post-processing validation step |
| PII in prompt logged | Low | Inference runs locally via Ollama |
| Model used without review | Medium | README and UI include mandatory disclaimer |

## Evaluation

See [notebooks/03_evaluate.ipynb](notebooks/03_evaluate.ipynb) for full methodology and results.

## Ethical Considerations

Fine-tuning on access control policy generation carries a dual-use risk: the same model could assist in crafting overly permissive policies. Mitigations applied:

- Evaluation suite explicitly tests for least-privilege violations
- Model card and demo UI include a human-review disclaimer
- Model weights published with a responsible-use notice