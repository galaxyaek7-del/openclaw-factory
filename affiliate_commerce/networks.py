#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate Commerce — network URL builders (ADR-149, 2026-07-30).

The smallest real, honest slice the founder's directive asked for: real
Amazon Associates URL construction, honestly reporting an unconfigured
tag rather than fabricating one. No other network is wired -- the
directive named exactly one real program to start with.
"""

import os

AMAZON_ASSOCIATE_TAG_ENV = "AMAZON_ASSOCIATE_TAG"


def amazon_associate_tag_configured():
    """Real, honest check -- never assumes a tag exists. The founder's
    own real Amazon Associates account (created outside this codebase,
    per the directive's own instruction) is the only source of a real
    tag; nothing here invents one."""
    return bool(os.environ.get(AMAZON_ASSOCIATE_TAG_ENV))


def build_amazon_url(asin, tag=None):
    """Real Amazon product URL, with a real Associates tag appended only
    when one is actually configured. Honestly omits the tag (rather than
    substituting a placeholder) when none exists yet -- a link with no
    tag still works as a real product link, it just earns no real
    commission until the founder's real account is live."""
    tag = tag if tag is not None else os.environ.get(AMAZON_ASSOCIATE_TAG_ENV)
    base = f"https://www.amazon.com/dp/{asin}"
    if tag:
        return f"{base}?tag={tag}"
    return base


def network_status():
    """Real, honest status for Mission Control -- never a fabricated
    'connected' state."""
    configured = amazon_associate_tag_configured()
    return {
        "network": "amazon_associates",
        "tag_configured": configured,
        "reason": None if configured else "AMAZON_ASSOCIATE_TAG غير مُعدّ -- ينتظر حساب Amazon Associates حقيقي للمؤسس (لا يمكن لهذا النظام إنشاء الحساب)",
    }
