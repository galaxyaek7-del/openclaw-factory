# Editing files another session has changed

Two agents work in this checkout at once (risk R11). A file with someone
else's uncommitted edits is shared state: losing it loses work that exists
nowhere else. This procedure applies to every such file.

## Before editing

1. `git diff --stat <file>`: if it shows changes you did not make, the file is shared.
2. Copy the file to the scratchpad before the first edit (`cp <file> <scratchpad>/<name>.bak`).

## Editing

3. Prefer the Edit tool for small changes.
4. A scripted edit must read the whole file, transform it in memory, check that every
   anchor occurs exactly once, and only then write: to `<file>.tmp`, followed by
   `os.replace`. Never open the destination for writing before the transform has succeeded.
   `open(dst, "w").write(transform(data))` truncates `dst` first; if `transform` raises,
   the file is left empty.
5. Match the file's line endings. Working copies here are often CRLF while the
   repository stores LF, so an anchor written with `\n` silently fails to match.

## Committing

6. Commit only your own hunks: build the blob from `git show HEAD:<file>` plus your
   change, add it with `git update-index --cacheinfo` in a temporary index,
   `git commit-tree`, `git update-ref`, then `git reset --mixed`. The working copy,
   including the other session's edits, is untouched.
7. Run the tests against a clean worktree of the new commit before pushing.

## If a shared file is damaged

8. Stop. OpenCode keeps a git snapshot of the working tree:
   `S=~/.local/share/opencode/snapshot/<project>/<worktree>`;
   `GIT_INDEX_FILE=$S/index git --git-dir=$S ls-files -s -- <file>` gives the blob of the
   last snapshot, and `git --git-dir=$S cat-file -p <blob>` its exact bytes
   (`core.autocrlf=false`, so line endings are preserved). Check the snapshot time against
   the file's last modification before trusting it, and compare the restored file's
   `git diff --stat` with the one taken before the damage.
9. Record the event in `data/incident_memory.jsonl` (`incident_memory.py`).

Origin: incident of 2026-10-29, `lib/ceo_command_center.js` truncated by step 4's
anti-pattern and restored byte-exact from the snapshot.
