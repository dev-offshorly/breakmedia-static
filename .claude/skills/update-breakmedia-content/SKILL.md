---
name: update-breakmedia-content
description: >-
  Update content on the Breakmedia static website (breakmedia.net) through plain-English
  requests — change headings, paragraphs, button labels, images, or alt text on any page,
  then deploy. Use whenever someone wants to edit, change, reword, replace, or swap text or
  images on the Break Media site, the homepage, a service page (creative, crm, seo, strategy,
  media, media-consultancy, market-research, digital-design), or a work/case-study page.
---

# Update Breakmedia site content

This skill edits the static site safely through a **content manifest**: every editable
element on every page carries a stable `data-cms="<key>"` anchor, and `content/manifest.json`
maps each key to its page, section, type, and current value. You resolve a request to a key,
apply a surgical edit, validate, and deploy.

**Golden rule: never hand-edit the HTML.** Always go through `tools/cms/apply_edit.py`. Hand
edits reorder attributes, drop the `data-cms` anchors, or break the byte-for-byte cleanliness
the deploy relies on. The tools change *only* the targeted text/attribute.

All commands run from the repo root (`breakmedia-static/`). Tools need Python 3 + `beautifulsoup4`
(only `build_manifest`/`annotate` use bs4; `query`/`apply_edit` are stdlib-only).

## Workflow

### 1. Make sure the manifest is current
If HTML may have changed outside this tooling (e.g. a fresh content crawl), regenerate first:
```
python3 tools/cms/build_manifest.py            # re-annotates pages + rewrites content/manifest.json
```
Otherwise skip — the manifest is already in sync.

### 2. Find the target item(s)
Use `query.py` to turn the request into one or more `data-cms` keys. Filters are ANDed,
matching is case-insensitive.
```
python3 tools/cms/query.py --pages                       # list pages + counts
python3 tools/cms/query.py --page index.html --section about-us
python3 tools/cms/query.py --contains "maximum value"    # find by current wording
python3 tools/cms/query.py --page work/indosole --type image
```
Page namespaces: home = `index.html`; services = `creative/`, `crm/`, `seo/`, `strategy/`,
`media/`, `media-consultancy/`, `market-research/`, `digital-design/`; case studies =
`work/<name>/`. Home sections include `signposts`, `values-approach`, `how-we-work`,
`about-us`, `capabilities`, `contact-us`.

**If the match is ambiguous, stop and confirm with the user** — show the candidate keys with
their current values and ask which one (or which page) they mean. Do not guess.

### 3. Apply the edit
One item per call. Exactly one of `--text` (inner text) or `--attr/--value` (an attribute).
```
# text:
python3 tools/cms/apply_edit.py --key home.about-us.h2.1 --text "ABOUT THE TEAM."
# attribute (image, link, alt):
python3 tools/cms/apply_edit.py --key home.capabilities.image.3 --attr src --value "app/uploads/2024/06/new-icon.svg"
python3 tools/cms/apply_edit.py --key home.values-approach.image.1 --attr alt --value "Our new tagline"
```
Notes:
- **Text edits replace the element's entire inner content.** If the element wraps inline
  markup you must keep (e.g. `<p><strong>…</strong></p>`), tell the user the markup will be
  replaced by plain text, or re-include it in `--text`.
- **Responsive images come in variant sets** — a section often has desktop/tablet/mobile
  `image.1/2/3` pointing at different files. To swap "the image", update **all** variants in
  that section (query by `--section … --type image`), each to its size-appropriate file.
- **New image files**: place the asset under `app/uploads/<year>/<month>/…` (mirror the
  existing convention), then point `--attr src` at that relative path. Update `--attr alt` too.

### 4. Validate
```
python3 tools/cms/build_manifest.py --check     # re-parses every page; item count must stay 780 (or the known total)
git diff --stat                                  # only the intended file(s) changed
```
Sanity-check the diff is the change you intended and nothing else:
```
git diff <page> | grep -E '^[+-]' | grep -v '^[+-][+-]'
```
If a structure looks broken, revert with `git restore <page>` and `python3 tools/cms/build_manifest.py`.

### 5. Confirm with the user — REQUIRED, always
**Committing to `main` deploys to the live site (breakmedia.net) automatically.** So you must
get explicit confirmation before every commit. This gate is mandatory — never skip it, never
auto-commit, even if the user's original request sounded like "just do it".

1. Present a clear **before → after** summary for each item changed, e.g.:
   `home.values-approach.h2.1 (index.html):  "BREAKING …" → "CHANGING …"`
2. Show the verified diff (`git diff --stat` plus the changed lines from step 4).
3. State plainly: *"Committing this to main will publish it live to breakmedia.net. Proceed?"*
4. **Ask the user a yes/no confirmation question and STOP.** Use the AskUserQuestion tool with
   options like **"Yes, commit & deploy"** / **"No, don't commit"** (and optionally "Let me adjust").
5. Only continue to step 6 on an explicit **yes**. On **no**: do not commit. Offer to adjust the
   wording, make further edits, or revert with `git restore <page>` +
   `python3 tools/cms/build_manifest.py`.

### 6. Commit & deploy (only after a "yes")

First establish **who the commit is attributed to** — this skill is shared, so it must not
assume any one person's identity:
1. If `git config user.name` and `git config user.email` are already set in this repo/session,
   show them and ask the user to confirm "commit as <name> <email>?".
2. Otherwise, **ask the user for their GitHub handle** (and email if they want a specific one),
   and use it for the commit author. Default the email to GitHub's noreply form.

```
# Ask once, then reuse for the session. Example using a provided handle:
HANDLE="<their-github-handle>"
git add -A
git -c user.name="$HANDLE" -c user.email="$HANDLE@users.noreply.github.com" \
    commit -m "content: <what changed, e.g. update homepage About heading>"
git push origin main                             # commit to main → CI/CD auto-deploys to breakmedia.net
```
Keep one logical content change per commit so it is easy to review and roll back. After pushing,
tell the user the deploy is running and the change will be live shortly.

## Guardrails
- **Never commit without explicit user confirmation (step 5).** A commit to `main` publishes
  live to breakmedia.net, so confirmation is non-negotiable on every change.
- Never edit `*.html` by hand or with sed/Write — only via `apply_edit.py`.
- Never touch files under `app/themes/`, `app/plugins/`, `wp/`, `wp-json/` — those are theme
  assets and crawl artifacts, not content.
- The `data-cms` attributes are inert (no styling/behaviour). Do not remove them.
- If asked to add a brand-new section or page (not edit existing content), that is out of
  scope for this skill — it edits existing annotated elements. Flag it to the user.

## How the system was built (reference)
- `tools/cms/annotate.py` — surgically injects `data-cms` anchors by byte position (no HTML
  re-serialization), preserving exact bytes and line endings.
- `tools/cms/build_manifest.py` — runs annotation across all pages and writes the manifest.
- `tools/cms/query.py` — searches the manifest (read-only).
- `tools/cms/apply_edit.py` — the only writer of content; edits one item and syncs the manifest.
- `content/manifest.json` — the content index (key → page/section/type/value).
