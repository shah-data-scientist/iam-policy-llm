"""
HuggingFace Spaces entry point — IAM Policy Generator demo.
Set HF_REPO to your pushed adapter before deploying.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import gradio as gr
from inference import load_model, generate_policy

HF_REPO = "YOUR_HF_USERNAME/llama-3.2-3b-iam-policy"  # <-- set this

model, tokenizer = load_model(HF_REPO)

DISCLAIMER = (
    "⚠️ **Review all outputs before use.** "
    "This model generates draft policies only — not validated for production."
)

EXAMPLES = [
    "Finance team needs read-only access to S3 bucket prod-invoices. No delete. MFA required.",
    "DevOps can start and stop EC2 instances in eu-west-1 only. No terminate or security group changes.",
    "Data science team needs full access to SageMaker but no access to production S3 buckets.",
    "Lambda function needs to read secrets from Secrets Manager and write logs to CloudWatch.",
    "Auditors need read-only access to CloudTrail logs and Config rules. No write access anywhere.",
]


def generate(requirement: str) -> tuple[str, str, str]:
    if not requirement.strip():
        return "", "", "Please enter a requirement."
    result = generate_policy(requirement.strip(), model, tokenizer)
    if result.get("parse_error"):
        return "", "", f"Parse error — raw output:\n{result.get('raw_output', '')}"
    policy_json = json.dumps(result.get("policy", {}), indent=2)
    nist = ", ".join(result.get("nist_controls", []))
    risk = result.get("risk_notes", "")
    return policy_json, nist, risk


with gr.Blocks(title="IAM Policy Generator") as demo:
    gr.Markdown("# IAM Policy Generator")
    gr.Markdown(
        "Fine-tuned Llama 3.2 3B — generates AWS IAM policies from plain English, "
        "with NIST SP 800-53 control mappings."
    )
    gr.Markdown(DISCLAIMER)

    with gr.Row():
        with gr.Column():
            requirement = gr.Textbox(
                lines=4,
                label="Access Control Requirement",
                placeholder="Describe who needs access to what, with any constraints…",
            )
            submit = gr.Button("Generate Policy", variant="primary")
            gr.Examples(examples=EXAMPLES, inputs=requirement)

        with gr.Column():
            policy_out = gr.Code(language="json", label="IAM Policy JSON")
            nist_out = gr.Textbox(label="NIST SP 800-53 Controls")
            risk_out = gr.Textbox(label="Risk Notes")

    submit.click(fn=generate, inputs=requirement, outputs=[policy_out, nist_out, risk_out])

if __name__ == "__main__":
    demo.launch()
