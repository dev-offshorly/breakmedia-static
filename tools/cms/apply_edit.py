#!/usr/bin/env python3
"""
apply_edit.py — Deterministic, surgical content edit for the Breakmedia static site.

The AI content-update skill calls this instead of hand-editing HTML, so every change
is precise and reviewable. It locates the element carrying data-cms="<key>" and either
replaces its inner text or one attribute (src/alt/href), touching nothing else in the
file, then updates the cached value in content/manifest.json.

Usage:
  python3 tools/cms/apply_edit.py --key home.about-us.h2.1 --text "NEW HEADING"
  python3 tools/cms/apply_edit.py --key home.capabilities.image.3 --attr src --value "app/uploads/2024/new.png"

Inputs:  --key (required); exactly one of --text (inner text) or --attr/--value (attribute).
Outputs: writes the page in place (preserving exact line endings), prints a before/after
         summary, and refreshes the manifest entry. Exits non-zero on any error.
Side effects: modifies one HTML file and content/manifest.json.
"""
import sys, os, re, json, argparse, html
from html.parser import HTMLParser

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MANIFEST = os.path.join(ROOT, "content", "manifest.json")


def _line_starts(raw):
    offs = [0]
    for i, ch in enumerate(raw):
        if ch == "\n":
            offs.append(i + 1)
    return offs


class _Locator(HTMLParser):
    """Find the element with data-cms==key; record its start-tag span and inner-content span."""

    def __init__(self, raw, key):
        super().__init__(convert_charrefs=True)
        self.raw = raw
        self.key = key
        self.line_starts = _line_starts(raw)
        self.depth = 0
        self.target = None          # {tag, start, starttag_end, depth}
        self.starttag_span = None   # (start, end) of "<tag ...>"
        self.inner_span = None      # (start, end) of inner content (None,None if void/self-closed)

    def _abs(self):
        ln, col = self.getpos()
        return self.line_starts[ln - 1] + col

    def handle_starttag(self, tag, attrs):
        ad = {k: (v or "") for k, v in attrs}
        if self.target is None and ad.get("data-cms") == self.key:
            start = self._abs()
            stt = self.get_starttag_text() or ""
            self.starttag_span = (start, start + len(stt))
            self.target = {"tag": tag, "depth": self.depth, "inner_start": start + len(stt)}
        self.depth += 1

    def handle_startendtag(self, tag, attrs):
        ad = {k: (v or "") for k, v in attrs}
        if self.target is None and ad.get("data-cms") == self.key:
            start = self._abs()
            stt = self.get_starttag_text() or ""
            self.starttag_span = (start, start + len(stt))
            self.target = {"tag": tag, "depth": self.depth, "inner_start": None}  # void/self-closed

    def handle_endtag(self, tag):
        self.depth -= 1
        if self.target and self.inner_span is None and tag == self.target["tag"] \
                and self.depth == self.target["depth"] and self.target["inner_start"] is not None:
            self.inner_span = (self.target["inner_start"], self._abs())


def _load_raw(path):
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def _save_raw(path, raw):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(raw)


def _replace_attr(starttag, attr, new_value):
    """Return a start tag with attr set to new_value (escaped); insert the attr if missing."""
    esc = html.escape(new_value, quote=True)
    pat = re.compile(r'(\s%s\s*=\s*)(".*?"|\'.*?\'|[^\s>]+)' % re.escape(attr), re.IGNORECASE)
    if pat.search(starttag):
        return pat.sub(lambda m: f'{m.group(1)}"{esc}"', starttag, count=1)
    # attr absent: inject right after the tag name
    return re.sub(r'^(<\w+)', lambda m: f'{m.group(1)} {attr}="{esc}"', starttag, count=1)


def main():
    ap = argparse.ArgumentParser(description="Surgically edit one content item by data-cms key.")
    ap.add_argument("--key", required=True)
    ap.add_argument("--text", help="new inner text (HTML-escaped)")
    ap.add_argument("--attr", help="attribute to edit, e.g. src/alt/href")
    ap.add_argument("--value", help="new attribute value")
    args = ap.parse_args()

    if not args.key or (args.text is None) == (args.attr is None):
        sys.exit("ERROR: provide --key and exactly one of --text OR (--attr with --value).")
    if args.attr is not None and args.value is None:
        sys.exit("ERROR: --attr requires --value.")

    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    rows = [it for it in manifest["items"] if it["key"] == args.key]
    if not rows:
        sys.exit(f"ERROR: key not found in manifest: {args.key}")
    page = rows[0]["page"]
    path = os.path.join(ROOT, page)
    raw = _load_raw(path)

    loc = _Locator(raw, args.key)
    loc.feed(raw)
    loc.close()
    if not loc.starttag_span:
        sys.exit(f"ERROR: data-cms anchor not found in {page}: {args.key}")

    if args.text is not None:
        if not loc.inner_span:
            sys.exit(f"ERROR: {args.key} is a void/self-closed element; use --attr instead.")
        s, e = loc.inner_span
        before = raw[s:e]
        new_raw = raw[:s] + html.escape(args.text, quote=False) + raw[e:]
        target_attr = None
        new_value = args.text
        print(f"text  {args.key}\n  - {before.strip()[:120]}\n  + {args.text[:120]}")
    else:
        s, e = loc.starttag_span
        starttag = raw[s:e]
        new_tag = _replace_attr(starttag, args.attr, args.value)
        new_raw = raw[:s] + new_tag + raw[e:]
        target_attr, new_value = args.attr, args.value
        print(f"attr  {args.key} [{args.attr}]\n  + {args.value}")

    _save_raw(path, new_raw)

    # refresh manifest cached value(s)
    for it in manifest["items"]:
        if it["key"] == args.key and it.get("attr") == target_attr:
            it["value"] = new_value
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"updated {page} and manifest. Re-run build_manifest.py --check to validate.")


if __name__ == "__main__":
    main()
