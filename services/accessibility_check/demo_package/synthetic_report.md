# Accessibility quick-check: synthetic shop page

Automated triage of a few machine-checkable criteria. Not an audit, not a certification, and not evidence of WCAG, ADA or European Accessibility Act compliance.

Pages checked: 1. Pages with errors: 1. Errors: 7. Warnings: 4.

## By issue

| Issue | Pages | Occurrences |
|---|---|---|
| page language missing (WCAG 3.1.1) | 1 | 1 |
| page title missing or empty (WCAG 2.4.2) | 1 | 1 |
| zoom disabled or limited in the viewport tag (WCAG 1.4.4) | 1 | 1 |
| page has no h1 (WCAG 1.3.1) | 1 | 1 |
| image without an alt attribute (WCAG 1.1.1) | 1 | 1 |
| heading level skipped (WCAG 1.3.1) | 1 | 1 |
| link with no text or accessible name (WCAG 2.4.4) | 1 | 1 |
| form field with no label (WCAG 1.3.1) | 1 | 1 |
| form field labelled only by placeholder text (WCAG 1.3.1) | 1 | 1 |
| unlabelled field kept out of the tab order (WCAG 1.3.1) | 1 | 1 |
| button with no text or accessible name (WCAG 4.1.2) | 1 | 1 |

## Findings

| Page | Line | Severity | WCAG | Issue | Element |
|---|---|---|---|---|---|
| synthetic_page.html | 1 | error | 3.1.1 | page language missing (no lang on <html>) |  |
| synthetic_page.html | 1 | error | 2.4.2 | page title missing or empty |  |
| synthetic_page.html | 4 | error | 1.4.4 | zoom disabled or limited in the viewport tag | width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no |
| synthetic_page.html | 7 | warning | 1.3.1 | page has no h1 |  |
| synthetic_page.html | 8 | error | 1.1.1 | image without an alt attribute | hero.jpg |
| synthetic_page.html | 9 | warning | 1.3.1 | heading level skipped (h4 after h2) |  |
| synthetic_page.html | 10 | error | 2.4.4 | link with no text or accessible name |  |
| synthetic_page.html | 12 | error | 1.3.1 | form field with no label | input[email] |
| synthetic_page.html | 13 | warning | 1.3.1 | form field labelled only by placeholder text | input[text] |
| synthetic_page.html | 14 | warning | 1.3.1 | unlabelled field kept out of the tab order (a spam trap?) is still announced by screen readers; add aria-hidden="true" | input[text] |
| synthetic_page.html | 15 | error | 4.1.2 | button with no text or accessible name |  |

## Not checked (needs a person)

- keyboard access and visible focus (2.1.1, 2.4.7)
- colour contrast (1.4.3, 1.4.11)
- whether alt text describes the image (1.1.1)
- captions and audio description (1.2.x)
- focus order and reading order (2.4.3, 1.3.2)
- error identification in forms (3.3.1)
- behaviour with a screen reader
- content added by scripts after load
