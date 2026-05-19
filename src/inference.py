"""
Local inference using the fine-tuned adapter.
Requires the adapter saved to iam-policy-adapter/ after training.
"""

import json
from data_utils import extract_json_from_output


def load_model(adapter_path: str = "iam-policy-adapter"):
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter_path,
        max_seq_length=2048,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    return model, tokenizer


def generate_policy(requirement: str, model=None, tokenizer=None) -> dict:
    if model is None or tokenizer is None:
        model, tokenizer = load_model()

    prompt = (
        "### Instruction:\nGenerate an AWS IAM policy for the following requirement\n\n"
        f"### Input:\n{requirement}\n\n"
        "### Response:\n"
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=512, temperature=0.1)
    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    response_text = decoded.split("### Response:")[-1].strip()

    result = extract_json_from_output(response_text)
    if result is None:
        return {"raw_output": response_text, "parse_error": True}
    return result


if __name__ == "__main__":
    requirement = (
        "The finance team needs read-only access to the S3 bucket 'prod-invoices'. "
        "No write or delete permissions. MFA must be required."
    )
    policy = generate_policy(requirement)
    print(json.dumps(policy, indent=2))
