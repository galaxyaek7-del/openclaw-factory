# Review: the five unimported GF-* n8n workflows (2026-10-22)

Read-only review. None of the five files was changed, imported or activated.
They remain `DEFINITION_NOT_ACTIVATED`, as `GF_OPS_README.md` records.

## Findings

| # | Finding | Severity | Evidence |
|---|---|---|---|
| 1 | All five use `n8n-nodes-base.executeCommand`. The installed n8n (2.25.7) excludes that node **by default**, so every one of them would fail to load or run if imported as written. | HIGH, blocks import | `@n8n/config/dist/configs/nodes.config.js:33`: `this.exclude = ['n8n-nodes-base.executeCommand', 'n8n-nodes-base.localFileTrigger']` |
| 2 | `GF-FOUNDER-APPROVAL-QUEUE` is an **unauthenticated** `GET` webhook (`/gf-approvals`, `responseMode: lastNode`). n8n is reachable from the internet through the ngrok tunnel, so once active, anyone holding the URL could read the founder approval queue. It would also put command execution behind a public URL. | HIGH, security | webhook node parameters; `N8N_EDITOR_BASE_URL` is an ngrok host |
| 3 | The commands run `python -m gf_ops.*`, and the `gf_ops/` package is **untracked**. These definitions only work on this one machine. | MEDIUM | `git status` shows `?? gf_ops/` |
| 4 | The commands hardcode `cd /d C:\openclaw-dasgboard`. | LOW | node parameters |

The README's own reasoning, that Execute Command avoids the `$env` trap, was
sound against the `$env` problem. It did not account for n8n 2.x also
excluding Execute Command by default.

## Recommendation (not applied; each needs a founder decision)

1. **Do not lift `NODES_EXCLUDE`.** Re-enabling Execute Command on an instance
   exposed through ngrok weakens a default security control.
2. Pick one of these routes instead:
   - **Schedule `gf_ops` outside n8n.** Use the existing `factory_loop.js`
     tick or a Windows scheduled task. These jobs are local Python; n8n adds
     nothing to them except a dependency.
   - **Or call `server.js` over HTTP**, the same pattern now fixed for
     Sales_Poll: an HTTP Header Auth credential (`GFinternalTokn01`) and
     `http://127.0.0.1:3000`, with `localhost` avoided because it resolves to
     IPv6 `::1`.
3. For the approval queue, either keep it local-only (no webhook), or require
   authentication on the webhook (n8n Header Auth) before activating it.
4. Commit `gf_ops/` before any of these definitions depends on it.
