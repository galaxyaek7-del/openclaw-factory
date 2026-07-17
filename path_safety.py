#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — shared safe-output-path confinement.

Standing-charter continuous-improvement follow-up (verified via the
zero-assumption production audit, Section C): book_generator.py and
cover_designer_v2.py each independently reimplemented the same
"sanitize a caller-supplied filename, then confine the result inside a
specific directory" pattern (Constitution section 4: sanitize filenames,
prevent path traversal). Both copies were individually correct, but a
future security-relevant fix to one would not have propagated to the
other — a real fix-drift risk, not a hypothetical one. One
implementation now; every caller shares it.

As a real side effect of unifying (not just a refactor): cover_designer_v2.py's
own version only sanitized the fallback (title-derived) filename, not a
caller-supplied `output` value beyond os.path.basename() — it was
already traversal-safe (basename + the commonpath check below still
catch that), but did not strip potentially problematic filesystem
characters from an explicit `output` the way book_generator.py's version
already did. This closes that gap too.
"""

import os
import re


def sanitize_filename_component(text, fallback="file", max_length=80):
    """Unicode-aware (keeps letters, including Arabic, via \\w): collapses
    every run of characters that isn't a word character or hyphen into a
    single underscore. Truncated to max_length — real filesystems have
    real path-length limits, and no legitimate title needs an 80+
    character filename stem."""
    text = re.sub(r'[^\w\-]+', '_', str(text or ''), flags=re.UNICODE).strip('_').lower()
    text = text[:max_length].strip('_')
    return text or fallback


def confine_to_directory(directory, candidate_name, fallback_stem, ext):
    """Returns (out_path, filename): both guaranteed to resolve inside
    `directory`. `candidate_name`'s own path components (any ../ or C:\\
    the caller supplied) are always dropped via os.path.basename before
    sanitization ever sees them; `fallback_stem` (typically a title) is
    used when candidate_name is empty. Raises ValueError in the
    should-be-unreachable case that the sanitized result still doesn't
    resolve inside `directory` — fails loud rather than silently
    trusting the sanitization above."""
    fallback_name = sanitize_filename_component(fallback_stem)
    if candidate_name:
        base = os.path.basename(str(candidate_name))
        name, _ext = os.path.splitext(base)
        name = sanitize_filename_component(name, fallback=fallback_name)
    else:
        name = fallback_name
    filename = f"{name}{ext}"

    directory_real = os.path.realpath(directory)
    out_path = os.path.realpath(os.path.join(directory_real, filename))
    if os.path.commonpath([out_path, directory_real]) != directory_real:
        raise ValueError("مسار ملف الإخراج غير آمن")
    return out_path, filename
