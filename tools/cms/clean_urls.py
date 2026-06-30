#!/usr/bin/env python3
"""
clean_urls.py — Replace stale local-dev host references with the production host.

The static site was crawled from the local dev environment, so absolute URLs (canonical,
og:url, favicons, search action, oembed params) still point at `breakmedia.lndo.site`.
Replacing just the host string fixes every encoding at once — plain (`https://host/`),
JSON-escaped (`https:\\/\\/host\\/`) and URL-encoded (`https%3A%2F%2Fhost%2F`) — because
only the host segment changes and the surrounding slashes/escaping stay valid.

Surgical: literal byte replacement with exact line endings preserved; idempotent.

Usage:
  python3 tools/cms/clean_urls.py            # rewrite all *.html pages
  python3 tools/cms/clean_urls.py --check    # report counts only, no writes

Inputs:  optional --check. Side effects: edits *.html files in place (unless --check).
"""
import os, sys, glob

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OLD_HOST = "breakmedia.lndo.site"
NEW_HOST = "breakmedia.net"


def html_pages():
    return sorted(p for p in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)
                  if "/.git/" not in p and "/node_modules/" not in p)


def main():
    check = "--check" in sys.argv
    total, touched = 0, 0
    for path in html_pages():
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            raw = f.read()
        n = raw.count(OLD_HOST)
        if not n:
            continue
        total += n
        touched += 1
        rel = os.path.relpath(path, ROOT)
        print(f"{'would fix' if check else 'fixed'} {n:>3}  {rel}")
        if not check:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(raw.replace(OLD_HOST, NEW_HOST))
    print(f"\n{total} reference(s) across {touched} file(s){' (dry-run)' if check else ''}")


if __name__ == "__main__":
    main()
