#!/usr/bin/env python3
"""
build_manifest.py — Annotate every page and (re)generate content/manifest.json.

Walks the site, runs the annotate() pass on each real page (injecting stable
data-cms anchors in place), collects every editable item, and writes a single
manifest the AI content-update skill reads. Idempotent and re-runnable.

Usage: python3 tools/cms/build_manifest.py [--check]
  default : annotate pages in place + write content/manifest.json
  --check : dry-run, report counts only (no file writes)
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from annotate import annotate

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKIP = ("/.git", "/wp-json", "/feed", "/comments", "/wp/", "/node_modules", "/tools", "/.claude")

def find_pages():
    pages = []
    for dp, dn, fn in os.walk(ROOT):
        if any(s in dp for s in SKIP):
            continue
        if "index.html" in fn:
            pages.append(os.path.relpath(os.path.join(dp, "index.html"), ROOT))
    return sorted(pages)

def main():
    check = "--check" in sys.argv
    pages = find_pages()
    items, per_page = [], {}
    for rel in pages:
        entries = annotate(ROOT, rel, write=not check)
        per_page[rel] = len(entries)
        items.extend(entries)
    manifest = {
        "site": "breakmedia.net",
        "generated_by": "tools/cms/build_manifest.py",
        "page_count": len(pages),
        "item_count": len(items),
        "items": items,
    }
    if not check:
        os.makedirs(os.path.join(ROOT, "content"), exist_ok=True)
        out = os.path.join(ROOT, "content", "manifest.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out}")
    print(f"pages: {len(pages)}  items: {len(items)}")
    for rel in pages:
        print(f"  {per_page[rel]:>4}  {rel}")

if __name__ == "__main__":
    main()
