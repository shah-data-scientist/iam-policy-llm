import json
import re
import time

import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; IAM-Policy-Dataset-Builder/1.0; "
        "educational use)"
    )
}

# AWS docs pages known to contain inline IAM policy JSON
AWS_POLICY_PAGES = [
    ("S3",             "https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-policies-s3.html"),
    ("EC2",            "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-policies-for-amazon-ec2.html"),
    ("Lambda",         "https://docs.aws.amazon.com/lambda/latest/dg/access-control-identity-based.html"),
    ("DynamoDB",       "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/iam-policy-examples.html"),
    ("RDS",            "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/security_iam_id-based-policy-examples.html"),
    ("Secrets Manager","https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_examples.html"),
    ("KMS",            "https://docs.aws.amazon.com/kms/latest/developerguide/iam-policies.html"),
    ("SQS",            "https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-security-best-practices.html"),
    ("SNS",            "https://docs.aws.amazon.com/sns/latest/dg/sns-access-policy-use-cases.html"),
    ("CloudWatch",     "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/iam-identity-based-access-control-cw.html"),
    ("CloudTrail",     "https://docs.aws.amazon.com/awscloudtrail/latest/userguide/security_iam_id-based-policy-examples.html"),
    ("ECS",            "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security_iam_id-based-policy-examples.html"),
]


def _fetch(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _nearest_heading_and_para(tag) -> tuple[str | None, str | None]:
    """Walk backwards from a tag to find the nearest heading and paragraph."""
    heading, description = None, None
    for prev in tag.find_all_previous(limit=30):
        if prev.name in ("h1", "h2", "h3", "h4") and heading is None:
            heading = prev.get_text(separator=" ", strip=True)
        if prev.name == "p" and description is None:
            text = prev.get_text(strip=True)
            if len(text) > 40:
                description = text
        if heading and description:
            break
    return heading, description


def _extract_policies(soup: BeautifulSoup, source_url: str) -> list[dict]:
    """Pull every valid IAM policy JSON block out of a parsed page."""
    results = []
    seen: set[str] = set()

    # AWS docs render code in several ways depending on page vintage
    candidates = soup.select("div.highlight pre, pre.programlisting, pre")

    for block in candidates:
        raw = block.get_text()
        if '"Version"' not in raw or '"Statement"' not in raw:
            continue

        # Strip any leading line-number gutter AWS sometimes adds
        cleaned = re.sub(r"^\s*\d+\s*", "", raw, flags=re.MULTILINE).strip()

        try:
            policy = json.loads(cleaned)
        except json.JSONDecodeError:
            continue

        fingerprint = json.dumps(policy, sort_keys=True)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        heading, description = _nearest_heading_and_para(block)
        if heading is None:
            continue

        results.append(
            {
                "heading": heading,
                "description": description or heading,
                "policy": policy,
                "source_url": source_url,
            }
        )

    return results


def scrape_all(pages: list[tuple[str, str]] = AWS_POLICY_PAGES,
               sleep_sec: float = 2.0) -> list[dict]:
    """
    Scrape each page in `pages`, return raw (heading, description, policy) dicts.
    `pages` is a list of (service_label, url) pairs.
    """
    all_raw: list[dict] = []

    for service, url in pages:
        try:
            soup = _fetch(url)
            found = _extract_policies(soup, url)
            print(f"  {service:20s} {len(found):3d} policies  {url.split('/')[-1]}")
            for item in found:
                item["service"] = service
            all_raw.extend(found)
            time.sleep(sleep_sec)
        except Exception as exc:
            print(f"  {service:20s} ERROR: {exc}")

    return all_raw
