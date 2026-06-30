#!/usr/bin/env python3
"""
query.py — Search the content manifest to resolve a plain-English request to data-cms keys.

The AI content-update skill uses this to find the right item(s) to edit without loading
the entire manifest. Filters are ANDed together; matching is case-insensitive.

Usage:
  python3 tools/cms/query.py --page index.html
  python3 tools/cms/query.py --section about-us --type h2
  python3 tools/cms/query.py --contains "maximum value"
  python3 tools/cms/query.py --pages          # list all pages + item counts

Inputs:  optional --page, --section, --type (h1..h6/text/image/cta), --contains, --attr.
Outputs: matching rows as JSON (key, page, section, type, attr, value). No side effects.
"""
import os, sys, json, argparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MANIFEST = os.path.join(ROOT, "content", "manifest.json")


def main():
    ap = argparse.ArgumentParser(description="Search the Breakmedia content manifest.")
    ap.add_argument("--page", help="filter by page relpath substring, e.g. 'index.html' or 'work/indosole'")
    ap.add_argument("--section", help="filter by section id, e.g. 'about-us'")
    ap.add_argument("--type", dest="ctype", help="filter by content type: h1..h6/text/image/cta")
    ap.add_argument("--attr", help="filter by attribute: src/alt/href")
    ap.add_argument("--contains", help="filter by substring of the current value")
    ap.add_argument("--pages", action="store_true", help="list pages and item counts, then exit")
    args = ap.parse_args()

    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    items = manifest["items"]

    if args.pages:
        counts = {}
        for it in items:
            counts[it["page"]] = counts.get(it["page"], 0) + 1
        for page in sorted(counts):
            print(f"{counts[page]:>4}  {page}")
        return

    def keep(it):
        if args.page and args.page.lower() not in it["page"].lower():
            return False
        if args.section and args.section.lower() != (it.get("section") or "").lower():
            return False
        if args.ctype and args.ctype.lower() != (it.get("ctype") or "").lower():
            return False
        if args.attr and args.attr.lower() != (it.get("attr") or "").lower():
            return False
        if args.contains and args.contains.lower() not in (it.get("value") or "").lower():
            return False
        return True

    hits = [it for it in items if keep(it)]
    print(json.dumps(hits, indent=2, ensure_ascii=False))
    print(f"\n# {len(hits)} match(es)", file=sys.stderr)


if __name__ == "__main__":
    main()
