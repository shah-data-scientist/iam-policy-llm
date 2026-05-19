import json
import re
from pathlib import Path


def load_jsonl(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(data: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def format_prompt(example: dict) -> str:
    return (
        f"### Instruction:\n{example['instruction']}\n\n"
        f"### Input:\n{example['input']}\n\n"
        f"### Response:\n{json.dumps(example['output'], indent=2)}"
    )


def extract_json_from_output(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def is_valid_policy(policy: dict) -> bool:
    required_keys = {"Version", "Statement"}
    return required_keys.issubset(policy.keys())


def extract_actions(policy: dict) -> set[str]:
    actions = set()
    for statement in policy.get("Statement", []):
        raw = statement.get("Action", [])
        if isinstance(raw, str):
            actions.add(raw)
        else:
            actions.update(raw)
    return actions
