#!/usr/bin/env node
/* Pre-flight wrapper (Phase 4, 2026-10-16) around scripts/scan_for_secrets.py,
 * the scanner CI already runs. That scanner covers TRACKED files only, so this
 * also applies its exact patterns (scan_file) to untracked, non-ignored files,
 * where new work lives before it is committed. Read-only.
 * Exit 0 = CLEAN, 1 = possible secret found or the scan could not run. */
'use strict';
const { spawnSync } = require('child_process');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const py = process.env.PYTHON || 'python';
const opts = { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 64 * 1024 * 1024 };

const tracked = spawnSync(py, ['scripts/scan_for_secrets.py'], opts);
console.log((tracked.stdout || '').trim());

const untrackedCode = [
  'import importlib.util, subprocess, sys',
  "spec = importlib.util.spec_from_file_location('s', 'scripts/scan_for_secrets.py')",
  'm = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)',
  "files = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], capture_output=True, text=True, check=True).stdout.splitlines()",
  'hits = []',
  'for p in files:',
  '    if any(part in p for part in m.EXCLUDE_PATH_PARTS) or p == ".env" or p.startswith(".env."): continue',
  '    try: text = open(p, encoding="utf-8").read()',
  '    except (OSError, UnicodeDecodeError): continue',
  '    hits.extend(m.scan_file(p, text))',
  'for p, n, label, prev in hits: print("possible secret (%s) at %s:%d (%s)" % (label, p, n, prev))',
  'print("untracked files scanned: %d, findings: %d" % (len(files), len(hits)))',
  'sys.exit(1 if hits else 0)',
].join('\n');
const untracked = spawnSync(py, ['-c', untrackedCode], opts);
console.log((untracked.stdout || '').trim());
if (untracked.status !== 0 && untracked.stderr) console.log(untracked.stderr.split('\n').slice(-3).join('\n'));

const clean = tracked.status === 0 && untracked.status === 0;
console.log(clean ? 'SECRETS: CLEAN' : 'SECRETS: FINDINGS (see above)');
process.exit(clean ? 0 : 1);
