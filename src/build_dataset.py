"""
Standalone dataset builder — runs the full notebook 01 pipeline from the CLI.

Usage (from project root):
    python src/build_dataset.py

Outputs:
    data/raw/synthetic_batch_01.jsonl   ~500 Gemini-synthetic examples
    data/raw/scraped_aws_docs.jsonl     AWS-docs-scraped + Gemini-enriched examples
    data/processed/train.jsonl          90% split
    data/processed/test.jsonl           10% split
"""

import json
import os
import re
import sys
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(__file__))
from data_utils import load_jsonl, save_jsonl, is_valid_policy
from scrape_aws_docs import scrape_all

# ── Config ──────────────────────────────────────────────────────────────────

GEMINI_MODEL    = "gemini-flash-lite-latest"
BATCH_SIZE      = 10
BATCHES_PER_THEME = 5
SLEEP_SEC       = 5   # Gemini free tier: 15 RPM → safe at 1 call / 5s

SERVICE_THEMES = [
    "S3 bucket policies, Glacier, cross-account S3 access",
    "EC2 instances, Auto Scaling, AMI management, Systems Manager",
    "Lambda functions, API Gateway, Step Functions",
    "RDS databases, DynamoDB tables, ElastiCache, Redshift",
    "IAM roles, STS assume-role, permission boundaries, cross-account",
    "KMS key policies, Secrets Manager, ACM certificates",
    "SQS queues, SNS topics, EventBridge rules, Kinesis",
    "CloudWatch logs and alarms, CloudTrail, AWS Config, GuardDuty",
    "CodePipeline, CodeBuild, ECR, CloudFormation, CodeDeploy",
    "VPC flow logs, Route53, CloudFront, API Gateway, WAF",
]

ROOT = os.path.join(os.path.dirname(__file__), "..")
SEEDS_PATH      = os.path.join(ROOT, "data", "raw", "seed_examples.jsonl")
SYNTHETIC_PATH  = os.path.join(ROOT, "data", "raw", "synthetic_batch_01.jsonl")
SCRAPED_PATH    = os.path.join(ROOT, "data", "raw", "scraped_aws_docs.jsonl")
TRAIN_PATH      = os.path.join(ROOT, "data", "processed", "train.jsonl")
TEST_PATH       = os.path.join(ROOT, "data", "processed", "test.jsonl")

# ── Gemini client ────────────────────────────────────────────────────────────

load_dotenv(os.path.join(ROOT, ".env"))
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SYSTEM_INSTRUCTION = """You generate realistic, production-quality AWS IAM policy \
training examples for IT security professionals.

Every policy you generate MUST follow these rules:
1. Include 3-6 IAM actions per statement — never just 1 action
2. Use specific resource ARNs (e.g. arn:aws:s3:::prod-bucket/*) not bare "*"
3. Add at least one Condition block per policy — choose from: MFA required, \
aws:SourceVpc, aws:RequestedRegion, aws:PrincipalTag, aws:MultiFactorAuthAge, \
aws:CurrentTime, or StringEquals on resource tags
4. Use multiple Statement blocks when the scenario involves different resources \
or permission levels
5. Add an explicit Deny statement for sensitive operations (Delete*, admin actions, \
disableLogging, PassRole) when the scenario warrants it
6. Apply strict least-privilege: only grant actions the requirement explicitly asks for

Output format: JSON object with keys instruction, input, output.
output must contain: policy (valid AWS IAM JSON), \
nist_controls (2-4 NIST SP 800-53 Rev5 IDs), risk_notes (one sentence)."""

# ── Step 1 — Load & validate seeds ──────────────────────────────────────────

def step1_load_seeds():
    print("\n=== Step 1: Load seeds ===")
    seed = load_jsonl(SEEDS_PATH)
    errors = []
    for i, ex in enumerate(seed):
        if not all(k in ex for k in ["instruction", "input", "output"]):
            errors.append(f"Example {i}: missing keys")
        elif not is_valid_policy(ex["output"].get("policy", {})):
            errors.append(f"Example {i}: invalid policy structure")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    print(f"  {len(seed)} seed examples loaded and validated")
    return seed

# ── Step 2 — Synthetic generation ───────────────────────────────────────────

def _complexity_score(ex):
    stmts = ex["output"]["policy"].get("Statement", [])
    actions = sum(
        len(s.get("Action", [])) if isinstance(s.get("Action"), list) else 1
        for s in stmts
    )
    has_condition = any("Condition" in s for s in stmts)
    has_deny = any(s.get("Effect") == "Deny" for s in stmts)
    return len(stmts) * 3 + actions + has_condition * 5 + has_deny * 4


def _safe_parse(text):
    try:
        raw = json.loads(text)
        if isinstance(raw, list):
            return raw
        return next(v for v in raw.values() if isinstance(v, list))
    except (json.JSONDecodeError, StopIteration):
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass
    return None


def generate_batch(seed, n=10, service_hint=""):
    # Use the 5 most complex seeds as few-shot examples
    top5 = sorted(seed, key=_complexity_score, reverse=True)[:5]
    few_shot = json.dumps(top5, indent=2)
    focus = service_hint or "varied AWS services (S3, EC2, RDS, Lambda, IAM, KMS, SQS, SNS)"
    user_msg = (
        f"Here are 5 high-quality training examples that demonstrate the required complexity:\n"
        f"{few_shot}\n\n"
        f"Generate {n} NEW and DISTINCT examples.\n"
        f"Focus on: {focus}\n\n"
        f"Hard requirements:\n"
        f"- Every policy must have at least 3 IAM actions per statement\n"
        f"- Every policy must have at least one Condition block\n"
        f"- Use specific resource ARNs, not bare \"*\"\n"
        f"- At least {max(1, n // 4)} of the {n} examples must have multiple Statement blocks\n"
        f"- At least {max(1, n // 4)} of the {n} examples must include a Deny statement\n\n"
        f"Return a JSON array of exactly {n} objects. No explanation, just the JSON array."
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.8,
        ),
    )
    result = _safe_parse(response.text)
    if result is None:
        raise ValueError(f"Could not parse response as JSON array: {response.text[:200]}")
    return result


def step2_synthetic(seed):
    print("\n=== Step 2: Synthetic generation ===")
    # Resume if file already partially exists
    existing = load_jsonl(SYNTHETIC_PATH) if os.path.exists(SYNTHETIC_PATH) else []
    all_synthetic = list(existing)
    if existing:
        print(f"  Resuming — {len(existing)} examples already saved")

    total_expected = len(SERVICE_THEMES) * BATCHES_PER_THEME * BATCH_SIZE
    themes_done = len(existing) // (BATCHES_PER_THEME * BATCH_SIZE)

    for t_idx, theme in enumerate(SERVICE_THEMES):
        if t_idx < themes_done:
            print(f"  Skipping (already done): {theme[:50]}")
            continue
        print(f"\n  Theme [{t_idx+1}/{len(SERVICE_THEMES)}]: {theme[:60]}")
        for i in range(BATCHES_PER_THEME):
            try:
                batch = generate_batch(seed, n=BATCH_SIZE, service_hint=theme)
                all_synthetic.extend(batch)
                print(f"    batch {i+1}/{BATCHES_PER_THEME}: +{len(batch)} → total {len(all_synthetic)}")
                time.sleep(SLEEP_SEC)
            except Exception as e:
                print(f"    ERROR batch {i+1}: {e}")
                time.sleep(20)
        save_jsonl(all_synthetic, SYNTHETIC_PATH)

    print(f"\n  {len(all_synthetic)}/{total_expected} synthetic examples saved → {SYNTHETIC_PATH}")
    return all_synthetic

# ── Step 3 — Scrape + enrich AWS docs ───────────────────────────────────────

def enrich(raw):
    prompt = (
        f"Convert this real AWS documentation IAM policy into a training record.\n\n"
        f"Service: {raw['service']}\nTitle: {raw['heading']}\nContext: {raw['description']}\n"
        f"Policy:\n{json.dumps(raw['policy'], indent=2)}\n\n"
        "Return a JSON object with exactly these keys:\n"
        '- "instruction": "Generate an AWS IAM policy for the following requirement"\n'
        '- "input": plain-English access control requirement (2-3 sentences)\n'
        '- "output": {"policy": <exact policy JSON above>, '
        '"nist_controls": [NIST SP 800-53 rev5 IDs], "risk_notes": "one sentence"}\n\n'
        "Return only the JSON object, no explanation."
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return json.loads(response.text)


def step3_scrape(seed):
    print("\n=== Step 3: Scrape + enrich AWS docs ===")
    if os.path.exists(SCRAPED_PATH):
        existing = load_jsonl(SCRAPED_PATH)
        print(f"  {SCRAPED_PATH} already exists ({len(existing)} examples) — skipping scrape")
        return existing

    print("  Scraping AWS documentation pages...")
    raw_scraped = scrape_all()
    print(f"  {len(raw_scraped)} raw policy blocks found")

    enriched = []
    for i, raw in enumerate(raw_scraped):
        try:
            record = enrich(raw)
            enriched.append(record)
            print(f"  [{i+1}/{len(raw_scraped)}] {raw['service']:20s} {raw['heading'][:50]}")
            time.sleep(SLEEP_SEC)
        except Exception as e:
            print(f"  [{i+1}/{len(raw_scraped)}] ERROR ({raw['service']}): {e}")
            time.sleep(15)

    save_jsonl(enriched, SCRAPED_PATH)
    print(f"\n  {len(enriched)} enriched examples saved → {SCRAPED_PATH}")
    return enriched

# ── Step 4 — Merge & split ───────────────────────────────────────────────────

def step4_split(seed, synthetic, scraped):
    print("\n=== Step 4: Merge & train/test split ===")
    all_examples = seed + synthetic + scraped
    print(f"  Seeds:     {len(seed):4d}")
    print(f"  Synthetic: {len(synthetic):4d}")
    print(f"  Scraped:   {len(scraped):4d}")
    print(f"  Total:     {len(all_examples):4d}")

    train, test = train_test_split(all_examples, test_size=0.1, random_state=42)
    save_jsonl(train, TRAIN_PATH)
    save_jsonl(test, TEST_PATH)
    print(f"\n  Train: {len(train)} → {TRAIN_PATH}")
    print(f"  Test:  {len(test)}  → {TEST_PATH}")
    print("\nDataset ready — proceed to notebooks/02_finetune.ipynb")

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    seed      = step1_load_seeds()
    synthetic = step2_synthetic(seed)
    scraped   = step3_scrape(seed)
    step4_split(seed, synthetic, scraped)
