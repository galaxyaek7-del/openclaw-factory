# Accessibility quick-check: Galaxy Forge public pages (customer_site/)

Automated triage of a few machine-checkable criteria. Not an audit, not a certification, and not evidence of WCAG, ADA or European Accessibility Act compliance.

Pages checked: 118. Pages with errors: 0. Errors: 0. Warnings: 22.

## By issue

| Issue | Pages | Occurrences |
|---|---|---|
| form field labelled only by placeholder text (WCAG 1.3.1) | 5 | 11 |
| unlabelled field kept out of the tab order (WCAG 1.3.1) | 4 | 5 |
| page has no h1 (WCAG 1.3.1) | 3 | 3 |
| heading level skipped (WCAG 1.3.1) | 3 | 3 |

## Findings

| Page | Line | Severity | WCAG | Issue | Element |
|---|---|---|---|---|---|
| contact.html | 95 | warning | 1.3.1 | unlabelled field kept out of the tab order (a spam trap?) is still announced by screen readers; add aria-hidden="true" | input[text] |
| eu-ai-act-compliance-toolkit.html | 143 | warning | 1.3.1 | form field labelled only by placeholder text | input[text] |
| eu-ai-act-compliance-toolkit.html | 144 | warning | 1.3.1 | form field labelled only by placeholder text | input[email] |
| guide-etsy-suspension-appeal.html | 90 | warning | 1.3.1 | form field labelled only by placeholder text | input[text] |
| guide-etsy-suspension-appeal.html | 91 | warning | 1.3.1 | form field labelled only by placeholder text | input[email] |
| history.html | 86 | warning | 1.3.1 | page has no h1 |  |
| index.html | 394 | warning | 1.3.1 | unlabelled field kept out of the tab order (a spam trap?) is still announced by screen readers; add aria-hidden="true" | input[text] |
| index.html | 417 | warning | 1.3.1 | form field labelled only by placeholder text | input[text] |
| index.html | 470 | warning | 1.3.1 | unlabelled field kept out of the tab order (a spam trap?) is still announced by screen readers; add aria-hidden="true" | input[text] |
| index.html | 495 | warning | 1.3.1 | heading level skipped (h4 after h2) |  |
| interest.html | 92 | warning | 1.3.1 | unlabelled field kept out of the tab order (a spam trap?) is still announced by screen readers; add aria-hidden="true" | input[text] |
| login.html | 103 | warning | 1.3.1 | page has no h1 |  |
| login.html | 107 | warning | 1.3.1 | unlabelled field kept out of the tab order (a spam trap?) is still announced by screen readers; add aria-hidden="true" | input[text] |
| service-verified-lead-lists.html | 67 | warning | 1.3.1 | form field labelled only by placeholder text | input[text] |
| service-verified-lead-lists.html | 68 | warning | 1.3.1 | form field labelled only by placeholder text | input[email] |
| service-verified-lead-lists.html | 70 | warning | 1.3.1 | form field labelled only by placeholder text | textarea |
| solutions.html | 143 | warning | 1.3.1 | heading level skipped (h4 after h1) |  |
| status.html | 136 | warning | 1.3.1 | page has no h1 |  |
| status.html | 138 | warning | 1.3.1 | form field labelled only by placeholder text | input[text] |
| status.html | 163 | warning | 1.3.1 | heading level skipped (h4 after h2) |  |
| status.html | 171 | warning | 1.3.1 | form field labelled only by placeholder text | input[text] |
| status.html | 192 | warning | 1.3.1 | form field labelled only by placeholder text | textarea |

## Not checked (needs a person)

- keyboard access and visible focus (2.1.1, 2.4.7)
- colour contrast (1.4.3, 1.4.11)
- whether alt text describes the image (1.1.1)
- captions and audio description (1.2.x)
- focus order and reading order (2.4.3, 1.3.2)
- error identification in forms (3.3.1)
- behaviour with a screen reader
- content added by scripts after load
