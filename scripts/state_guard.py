#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — state-write safeguard (FG incident 2026-09-28).
Enforces READ -> VALIDATE -> WRITE ATOMICALLY -> VERIFY -> LOG
for all state/queue JSON files. Prevents overwrite-without-read,
write-before-read, schema mismatch, state loss, untracked temp files.
"""
import json
import os
import tempfile

STATE_DIR = 'C:\\openclaw-dasgboard\\data'


def guarded_update(path, mutate, schema_keys=None, backup=True):
    """Read existing file (fail if unreadable JSON), apply mutate(dict)->dict,
    validate required keys, write atomically via temp+rename, re-read to
    verify, append a line to data/state_write_log.jsonl. Returns new dict."""
    if not os.path.exists(path):
        raise FileNotFoundError('refusing blind create; create explicitly: ' + path)
    with open(path, 'r', encoding='utf-8') as fh:
        raw = fh.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError('refusing to overwrite invalid JSON (%s): %s' % (path, e))
    if backup:
        with open(path + '.bak', 'w', encoding='utf-8') as fh:
            fh.write(raw)
    new = mutate(dict(data) if isinstance(data, dict) else list(data))
    if schema_keys:
        missing = [k for k in schema_keys if k not in new]
        if missing:
            raise ValueError('schema mismatch, missing keys %s in %s' % (missing, path))
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(new, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    with open(path, 'r', encoding='utf-8') as fh:
        verify = json.load(fh)
    assert json.dumps(verify, sort_keys=True) == json.dumps(new, sort_keys=True), 'verify failed'
    with open(os.path.join(STATE_DIR, 'state_write_log.jsonl'), 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({'path': path, 'ok': True}) + '\n')
    return new
