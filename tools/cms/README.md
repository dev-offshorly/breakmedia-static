# Breakmedia content CMS (static site)

A lightweight "headless CMS over static HTML" for **breakmedia.net**. It lets content be
updated through plain-English AI prompts (via the `update-breakmedia-content` skill) without a
WordPress backend, and deploys to AWS Lightsail through CI/CD.

## How it works

Every editable element on every page carries a stable `data-cms="<key>"` anchor. A single
`content/manifest.json` maps each key to its page, section, content type, and current value.
Edits are made **surgically** — only the targeted text or attribute changes, every other byte
(including mixed CRLF/LF line endings) is preserved — so diffs are tiny and reviewable.

Key shape: `<page>.<section>.<type>.<n>`
- page: `home` (index.html), a service slug (`creative`, `crm`, `seo`, `strategy`, `media`,
  `media-consultancy`, `market-research`, `digital-design`), or `work.<name>`
- section: the nearest section id (e.g. `about-us`, `capabilities`, `signposts`)
- type: `h1`..`h6`, `text` (p/blockquote), `image`, `cta`
- n: 1-based counter within that section+type

## Tools (run from repo root, Python 3)

| Command | Purpose |
|---|---|
| `python3 tools/cms/build_manifest.py` | Annotate all pages + (re)write `content/manifest.json`. Idempotent. |
| `python3 tools/cms/build_manifest.py --check` | Dry-run validation (no writes); used by CI. |
| `python3 tools/cms/query.py --pages` | List pages + item counts. |
| `python3 tools/cms/query.py --section about-us --type h2` | Find keys (filters ANDed, case-insensitive). |
| `python3 tools/cms/apply_edit.py --key K --text "…"` | Replace an element's inner text. |
| `python3 tools/cms/apply_edit.py --key K --attr src --value "…"` | Replace an attribute (src/alt/href). |
| `python3 tools/cms/clean_urls.py` | Replace stale `breakmedia.lndo.site` host refs with `breakmedia.net`. |

All tools use only the Python 3 standard library (`html.parser`, `json`) — no third-party
dependencies to install.

## Editing content

Use the **`update-breakmedia-content`** skill (in `.claude/skills/`) — it drives the full workflow:
find the key, apply the edit, validate, show the diff, commit, and deploy. Never hand-edit the
HTML: that reorders attributes or drops the `data-cms` anchors the system relies on.

## Deploy (CI/CD)

Deployment is already wired up **outside this repo**: a commit to `main` on GitHub triggers an
automatic deploy of the site to AWS Lightsail (breakmedia.net). There is nothing to configure
here — just commit to `main`.

Because every commit to `main` publishes live, the `update-breakmedia-content` skill **always
asks for explicit confirmation before committing** (see the skill's step 5). Keep one logical
content change per commit so it is easy to review and roll back.

## Re-crawling

If the site is re-crawled (new HTML), re-run `python3 tools/cms/build_manifest.py` to
re-annotate and regenerate the manifest. Existing `data-cms` keys are reused where present.
