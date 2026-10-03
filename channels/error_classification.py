"""Universal Distribution Fabric — Error Classification

Centralized error taxonomy for all platform adapters.
Classifies errors into actionable categories.
"""

import re
from typing import Dict, Optional

from channels.adapter_contract import ErrorClass


AUTH_PATTERNS = [
    re.compile(r"unauthorized", re.I),
    re.compile(r"invalid.*(token|key|credential)", re.I),
    re.compile(r"401", re.I),
    re.compile(r"authentication failed", re.I),
    re.compile(r"access denied", re.I),
]

ACCOUNT_PATTERNS = [
    re.compile(r"account.*(not found|disabled|suspended|closed)", re.I),
    re.compile(r"not.*(verified|active|enabled)", re.I),
    re.compile(r"payment method.*not.*connected", re.I),
    re.compile(r"onboarding.*incomplete", re.I),
    re.compile(r"transaction_checkout_not_enabled", re.I),
]

VALIDATION_PATTERNS = [
    re.compile(r"invalid.*(parameter|field|value|request)", re.I),
    re.compile(r"validation.*error", re.I),
    re.compile(r"missing.*(required|field)", re.I),
    re.compile(r"400", re.I),
    re.compile(r"422", re.I),
]

RATE_LIMIT_PATTERNS = [
    re.compile(r"rate.?limit", re.I),
    re.compile(r"429", re.I),
    re.compile(r"too many requests", re.I),
    re.compile(r"throttl", re.I),
]

TIMEOUT_PATTERNS = [
    re.compile(r"timed?\s*out", re.I),
    re.compile(r"timeout", re.I),
    re.compile(r"deadline exceeded", re.I),
]

NETWORK_PATTERNS = [
    re.compile(r"connection.*(refused|reset|error|failed)", re.I),
    re.compile(r"network.*(error|unreachable)", re.I),
    re.compile(r"dns.*(error|failed|resolution)", re.I),
    re.compile(r"ssl.*(error|certificate)", re.I),
]

DUPLICATE_PATTERNS = [
    re.compile(r"duplicate", re.I),
    re.compile(r"already.*(exists|created|published)", re.I),
    re.compile(r"conflict", re.I),
]

POLICY_BLOCK_PATTERNS = [
    re.compile(r"policy.*violation", re.I),
    re.compile(r"content.*violation", re.I),
    re.compile(r"terms.*of.*service", re.I),
    re.compile(r"prohibited", re.I),
]

PAYMENT_BLOCK_PATTERNS = [
    re.compile(r"payment.*fail", re.I),
    re.compile(r"insufficient.*funds", re.I),
    re.compile(r"card.*declined", re.I),
    re.compile(r"checkout.*not.*enabled", re.I),
]


def classify_error(error: Exception) -> ErrorClass:
    msg = str(error)
    for pattern in AUTH_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.AUTH_ERROR
    for pattern in ACCOUNT_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.ACCOUNT_ERROR
    for pattern in PAYMENT_BLOCK_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.PAYMENT_BLOCK
    for pattern in RATE_LIMIT_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.RATE_LIMIT
    for pattern in TIMEOUT_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.TIMEOUT
    for pattern in NETWORK_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.NETWORK_ERROR
    for pattern in DUPLICATE_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.DUPLICATE
    for pattern in VALIDATION_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.VALIDATION_ERROR
    for pattern in POLICY_BLOCK_PATTERNS:
        if pattern.search(msg):
            return ErrorClass.POLICY_BLOCK
    return ErrorClass.UNKNOWN_ERROR


def is_retryable(error_class: ErrorClass) -> bool:
    return error_class in {
        ErrorClass.RATE_LIMIT,
        ErrorClass.TIMEOUT,
        ErrorClass.NETWORK_ERROR,
        ErrorClass.PLATFORM_ERROR,
    }


def error_summary(error: Exception, platform: str = None) -> Dict:
    ec = classify_error(error)
    return {
        "error_class": ec.value,
        "platform": platform or "unknown",
        "retryable": is_retryable(ec),
        "message": str(error)[:200],
    }
