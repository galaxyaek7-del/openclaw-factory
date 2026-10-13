# Telegraph API — content format (verified 2026-10-12)

`createPage` and `editPage` **no longer accept an HTML string**. Sending HTML — even
`<p>x</p>` — returns `CONTENT_FORMAT_INVALID`.

They require a **JSON node list** whose children are **plain strings**.

```python
import json, requests

nodes = [
    {"tag": "p", "children": ["plain text renders"]},
    {"tag": "h3", "children": ["a heading renders"]},
]
requests.post("https://api.telegra.ph/createPage", data={
    "access_token": token,
    "title": "My Title",
    "content": json.dumps(nodes),      # <- the JSON node list, not HTML
    "author_name": "Galaxy Forge",
}, timeout=90)
```

## Error map (all observed live on 2026-10-12)

| You send | Telegraph replies | Meaning |
|---|---|---|
| HTML string (`<p>x</p>`) | `CONTENT_FORMAT_INVALID` | format no longer supported |
| plain text, no tags | `CONTENT_FORMAT_INVALID` | still needs the node list |
| node list, children as `{"type":"text","text":...}` | `CONTENT_TEXT_REQUIRED` | typed children rejected; use plain strings |
| **node list, children as plain strings** | **ok** | the only accepted shape |
| node list containing an `a` child | page created, **anchor silently stripped** | see below |

## Two separate problems that are easy to conflate

1. **Content format** — your own bug. Fixed by sending the node list above.
   Applies to every page you own.
2. **`PAGE_ACCESS_DENIED` on `editPage`** — the page belongs to a *different*
   access token. Not a format problem, not fixable from here. Only affects pages
   created before the current token existed.

Do not report (2) as a general "Telegraph writes are blocked". Writes work fine.

## Anchors are stripped

Telegraph's renderer drops `{"type": "a", "text": ..., "href": ...}` children —
**including internal `telegra.ph` hrefs**. The page is created, the link is not.
A `CONTENT_TEXT_REQUIRED` error on a link-only paragraph means the same thing:
the link node carries no renderable text on its own.

**Workaround in use:** put the full URL as its own paragraph of plain text. It
renders, is copy-pasteable, and costs no clicks that a broken anchor would have.
Trade-off accepted knowingly: a visible URL gets copied far less often than a
clickable one.

## Verifying a publication

`createPage` returning `ok` is **not** proof the content rendered. Always
re-fetch the public URL and check for the actual strings you intended to publish.

```python
h = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=45).text
assert "your-product-url" in h
```
