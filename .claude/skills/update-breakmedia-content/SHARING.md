# Sharing `update-breakmedia-content`

This is a **project skill** for the `breakmedia-static` repo. It is coupled to that repo:
it drives the Python tools in `tools/cms/` and reads `content/manifest.json`. It is not a
standalone, generic skill — it only works against the Breakmedia static site checkout.

## The simplest way to share it (recommended)
Commit it with the repo. Anyone who clones `breakmedia-static` and opens the folder in
Claude Code automatically has the skill available — no install step.

```
git add .claude/ tools/ content/ .gitignore
git commit -m "Add update-breakmedia-content skill + content CMS tooling"
git push
```

## Installing the bundle by hand (for a teammate not yet on the repo)
The shareable zip (`update-breakmedia-content.zip`) mirrors the repo layout. To use it,
unzip it **at the root of a `breakmedia-static` checkout** so the pieces land in place:

```
breakmedia-static/
  .claude/skills/update-breakmedia-content/SKILL.md   <- the skill
  tools/cms/*.py                                        <- the tools it calls
  content/manifest.json                                <- regenerate with build_manifest.py if missing
```

Then in that folder: `python3 tools/cms/build_manifest.py` (ensures the manifest matches the
current HTML) and open Claude Code there. Requirements: Python 3 (standard library only).

## What's in the bundle
- `.claude/skills/update-breakmedia-content/SKILL.md` + this guide
- `tools/cms/` — annotate, build_manifest, query, apply_edit, clean_urls, README

The bundle does **not** include the site HTML or `content/manifest.json` (those live in the
repo). Run `build_manifest.py` after placing the tools to (re)generate the manifest.

Deploy is handled outside the repo: committing to `main` auto-deploys to breakmedia.net, so
the skill always asks for confirmation before it commits.
