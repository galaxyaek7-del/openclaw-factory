"""Prove the factory_loop lock tests are NOT vacuous.

A test that cannot detect the bug it was written for is worse than no test: it
reports safety while covering nothing. This script proves the lock tests are
load-bearing by reverting factory_loop.js to the old, broken
unlink-then-exclusive-create reclaim in a THROWAWAY COPY of the repo and
confirming the suite then FAILS.

Portable on purpose: it is runnable on the Linux CI as well as Windows, and it
never touches the real working tree or the real lock file.

Usage:
    python scripts/mutation_check.py [runs]
Exit code 0 means the mutant was detected (tests are not weakened).
Exit code 1 means the mutant survived -- the tests are vacuous.
"""
import os
import shutil
import subprocess
import sys
import tempfile

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 5

OLD_RECLAIM = '''    try {
      fs.unlinkSync(lockFile);
    } catch (unlinkErr) {
      if (unlinkErr.code === 'ENOENT') {
        exitFn(0);
        return false;
      }
      throw unlinkErr;
    }
    fs.writeFileSync(lockFile, String(process.pid), { flag: 'wx' });
    return true;
'''


def build_mutant(dst):
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns(
        '.git', 'node_modules', '__pycache__', '.factory_loop.lock', '*.pyc'))
    path = os.path.join(dst, 'factory_loop.js')
    src = open(path, encoding='utf-8').read()
    start = src.find('const stolenAs')
    end = src.find('  } catch (err) {', start)
    if start == -1 or end == -1:
        raise SystemExit('could not locate the reclaim block in factory_loop.js; '
                         'the fix may have been rewritten -- re-verify by hand')
    open(path, 'w', encoding='utf-8', newline='').write(
        src[:start] + OLD_RECLAIM + src[end:])
    return path


def main():
    root = tempfile.mkdtemp(prefix='lock-mutant-')
    dst = os.path.join(root, 'repo')
    try:
        build_mutant(dst)
        print('mutant built in %s (old blind unlink-then-create reclaim)' % dst)

        detected = 0
        for i in range(1, RUNS + 1):
            r = subprocess.run(['node', '--test', 'tests/test_factory_loop_lock.js'],
                               cwd=dst, capture_output=True, text=True, timeout=900)
            # Judge by exit code, never by grepping TAP text. An earlier version
            # of this script looked for 'not ok'/'FAILED' and reported the mutant
            # as surviving on a run that `node --test` in fact failed -- the
            # verifier was wrong, not the test.
            if r.returncode != 0:
                detected += 1
        print('MUTANT DETECTED in %d/%d runs' % (detected, RUNS))
        if detected == 0:
            print('FAIL: the mutant survived -- the lock tests are VACUOUS.')
            return 1
        print('PASS: the lock tests still detect the original race, so they are not weakened.')
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())