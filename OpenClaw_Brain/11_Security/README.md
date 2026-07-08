# 11 — Security

## OPENCLAW_OS_CONSTITUTION.md's Security section (verbatim principles)

Zero Trust. Least Privilege. Encrypted secrets. Continuous monitoring. Backups. Recovery plans. Version control. Prompt Injection protection. Malware protection. No technology enters production without validation.

## What's actually practiced today (real, not aspirational)

- **Secrets:** `GROQ_KEY` lives only in `.env`, never committed (`.gitignore` excludes it). CLAUDE.md: "no cloud."
- **Guarded imports everywhere:** every optional dependency (`niche_validator_v2`, `cover_designer_v2`, `arabic_reshaper`, `inspectors`, `profit_oracle`, `pypdf`, `PIL`) is wrapped in `try/except`, degrading gracefully rather than crashing the whole pipeline on a missing package.
- **Path-traversal safety:** `_resolve_safe_output_path()` in `book_generator.py` confines every generated file to `books/` via `os.path.commonpath`, regardless of what filename a caller supplies.
- **GitHub token handling protocol** (established and repeated across every push this project has done):
  1. Never persist a token to disk. `git remote set-url` with the token embedded is *transient* — used immediately, then reverted.
  2. Verify the token first: `curl -H "Authorization: token $TOKEN" https://api.github.com/user`.
  3. Push.
  4. Immediately `git remote set-url origin <clean-url>` (no token) and `grep` `.git/config` to confirm nothing remains.
  5. **Always tell the user** that pasting a token in chat is itself an exposure they should remediate (rotate/revoke) — no amount of careful local handling undoes that.
- **Fail closed, not fail open:** `inspectors.py`'s `final_inspection()` treats its own exceptions as a rejection, never a silent approval — the one place in this codebase where "guard and degrade gracefully" would be the *wrong* pattern (a broken quality gate must never quietly become "everything passes").

## Not yet built

Prompt injection protection, malware protection, and continuous monitoring are named in the supreme law but have no dedicated component — Groq's outputs are parsed defensively (placeholder detection, encoding fixes) but not screened for injection attempts specifically. Worth flagging as a real gap, not silently claiming as done.
