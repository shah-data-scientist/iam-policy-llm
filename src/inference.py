"""
Local inference using the fine-tuned adapter.

GPU (Colab / CUDA):  uses unsloth for fast 4-bit inference
CPU (local PC):      falls back to transformers + peft automatically

Usage:
    python src/inference.py
    # or import and call generate_policy() directly
"""

import json
import os

from data_utils import extract_json_from_output


def load_model(adapter_path: str = "iam-policy-adapter"):
    """
    Load the fine-tuned adapter.
    Tries unsloth (GPU) first; falls back to transformers+peft (CPU).
    adapter_path can be a local directory or a HuggingFace repo ID.
    """
    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except ImportError:
        cuda_available = False

    if cuda_available:
        return _load_unsloth(adapter_path)
    else:
        return _load_cpu(adapter_path)


def _load_unsloth(adapter_path: str):
    from unsloth import FastLanguageModel
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter_path,
        max_seq_length=2048,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    print("Loaded with unsloth (GPU)")
    return model, tokenizer


def _load_cpu(adapter_path: str):
    """CPU inference via transformers + peft. ~45-90s per generation on a modern CPU."""
    import json as _json
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    # Read base model name from saved adapter config
    # Remap unsloth-specific quantised IDs to standard HF equivalents for CPU loading
    _UNSLOTH_REMAP = {
        "unsloth/llama-3.2-3b-instruct-unsloth-bnb-4bit": "meta-llama/Llama-3.2-3B-Instruct",
        "unsloth/llama-3.2-3b-bnb-4bit": "meta-llama/Llama-3.2-3B",
    }
    config_path = os.path.join(adapter_path, "adapter_config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            raw_id = _json.load(f).get(
                "base_model_name_or_path", "meta-llama/Llama-3.2-3B-Instruct"
            )
        base_model_id = _UNSLOTH_REMAP.get(raw_id, raw_id)
    else:
        base_model_id = adapter_path  # Hub repo — load directly

    print(f"Loading base model from {base_model_id} (CPU mode, this may take a minute)…")
    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    base = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype="auto",
        device_map="cpu",
        low_cpu_mem_usage=True,
    )

    if os.path.exists(config_path):
        model = PeftModel.from_pretrained(base, adapter_path)
    else:
        model = base  # Hub model already has adapter merged or is standalone

    model.eval()
    print("Loaded with transformers (CPU)")
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
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.1,
        do_sample=False,
    )
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
