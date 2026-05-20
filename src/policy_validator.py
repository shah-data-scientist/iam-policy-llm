"""
Post-generation validation layer for IAM policy outputs.

Usage:
    from policy_validator import validate_policy
    result = validate_policy(generate_policy(requirement))
    if result["validation"]["severity"] in ("HIGH", "MEDIUM"):
        print(result["validation"]["warnings"])
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from data_utils import extract_actions

# Actions that signal privilege escalation regardless of resource scope
_ESCALATION_PATTERNS = {
    "iam:*",
    "sts:*",
    "iam:passrole",
    "iam:createpolicy",
    "iam:attachrolepolicy",
    "iam:putuserrpolicy",
    "iam:putrolepolicy",
    "iam:createaccesskey",
    "sts:assumerole",
    "*",
}


def _check_flags(output: dict) -> dict:
    policy = output.get("policy", {})
    stmts = [s for s in policy.get("Statement", []) if isinstance(s, dict)]
    actions = extract_actions(policy)
    actions_lower = {a.lower() for a in actions}

    wildcard_action = any(
        a == "*" or a.endswith(":*") for a in actions
    )
    wildcard_resource = any(
        s.get("Resource") == "*" or
        (isinstance(s.get("Resource"), list) and "*" in s.get("Resource", []))
        for s in stmts
        if s.get("Effect") == "Allow"
    )
    missing_condition = len(stmts) > 0 and not any("Condition" in s for s in stmts)
    missing_deny = not any(s.get("Effect") == "Deny" for s in stmts)
    privilege_escalation = bool(actions_lower & _ESCALATION_PATTERNS)
    missing_version = policy.get("Version") != "2012-10-17"
    empty_nist = not output.get("nist_controls")

    return {
        "wildcard_action": wildcard_action,
        "wildcard_resource": wildcard_resource,
        "missing_condition": missing_condition,
        "missing_deny": missing_deny,
        "privilege_escalation": privilege_escalation,
        "missing_version": missing_version,
        "empty_nist": empty_nist,
    }


def _build_warnings(flags: dict) -> list[str]:
    messages = {
        "wildcard_action":       "Wildcard action (*) grants unrestricted permissions — violates least-privilege (AC-6)",
        "wildcard_resource":     "Wildcard resource (*) on Allow statement — scope resource to specific ARNs",
        "missing_condition":     "No Condition block — consider adding MFA, IP, or region restrictions",
        "privilege_escalation":  "Privilege escalation risk — policy contains IAM/STS actions that can grant further access",
        "missing_version":       "Policy missing Version: 2012-10-17 — required for AWS evaluation",
        "empty_nist":            "No NIST SP 800-53 controls mapped — compliance traceability missing",
        "missing_deny":          "No explicit Deny statement — consider denying sensitive operations",
    }
    # missing_deny is advisory only — not always required
    return [messages[k] for k, v in flags.items() if v and k != "missing_deny"] + \
           ([messages["missing_deny"]] if flags.get("missing_deny") else [])


def _severity(flags: dict) -> str:
    if flags["wildcard_action"] or flags["privilege_escalation"]:
        return "HIGH"
    if flags["wildcard_resource"] or flags["missing_condition"] or flags["missing_version"]:
        return "MEDIUM"
    if flags["missing_deny"] or flags["empty_nist"]:
        return "LOW"
    return "PASS"


def validate_policy(output: dict) -> dict:
    """
    Validate a policy output dict returned by generate_policy().
    Returns the original dict with a 'validation' key added.

    The caller should treat severity HIGH or MEDIUM as requiring human review
    before the policy is used in any real environment.
    """
    if output.get("parse_error"):
        return {
            **output,
            "validation": {
                "severity": "HIGH",
                "warnings": ["Model output could not be parsed as JSON — policy is unusable"],
                "flags": {},
            },
        }

    flags = _check_flags(output)
    warnings = _build_warnings(flags)
    severity = _severity(flags)

    return {
        **output,
        "validation": {
            "severity": severity,
            "warnings": warnings,
            "flags": flags,
        },
    }


if __name__ == "__main__":
    import json

    # Smoke test — known-bad policy (wildcard action + no condition)
    bad = {
        "policy": {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": ["*"], "Resource": "*"}],
        },
        "nist_controls": [],
        "risk_notes": "",
    }
    result = validate_policy(bad)
    print(json.dumps(result["validation"], indent=2))
    assert result["validation"]["severity"] == "HIGH"

    # Known-good policy
    good = {
        "policy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:GetObject", "s3:ListBucket"],
                    "Resource": ["arn:aws:s3:::prod-invoices/*"],
                    "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
                }
            ],
        },
        "nist_controls": ["AC-3", "AC-6"],
        "risk_notes": "Least-privilege applied.",
    }
    result = validate_policy(good)
    print(json.dumps(result["validation"], indent=2))
    assert result["validation"]["severity"] in ("PASS", "LOW")

    print("\nAll assertions passed.")
