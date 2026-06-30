#!/usr/bin/env python3
"""
annotate.py — Surgical content-manifest annotator for the Breakmedia static site.

Why surgical: a full HTML re-serialization (e.g. BeautifulSoup str(soup)) reorders
attributes, rewrites void tags and changes casing/whitespace, producing huge diffs
and risking subtle breakage. Instead this uses a streaming HTMLParser to locate each
editable element's start tag by byte position and inject ONLY ` data-cms="<key>"`
into the original source — every other byte is left identical.

For each page it:
  - scopes to the main #content subtree (falls back to <body> if absent),
  - tags editable elements (h1-6, p, blockquote, img, CTA links) with a stable
    key  <page>.<section>.<type>.<n>,
  - captures the current text value (or src/alt for images) for the manifest.

Idempotent: an element that already carries data-cms keeps its key and is not
re-inserted, so re-runs are stable.

Public API: annotate(root, relpath, write=False) -> list[dict] manifest entries.
"""
import sys, os, re, json
from html.parser import HTMLParser

HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
TEXT_TAGS = HEADINGS | {"p", "blockquote"}
VOID = {"img", "br", "hr", "meta", "link", "input", "source"}
SKIP_SECTION_ID = re.compile(r"-js($|-)|polyfill|wp-embed|sage/")  # script-tag ids, never content


def page_slug(rel):
    """Map a page relpath to a manifest namespace, e.g. 'work/indosole/index.html' -> 'work.indosole'."""
    rel = rel.replace("index.html", "").strip("/")
    return "home" if rel == "" else rel.replace("/", ".")


def _is_cta(attrs):
    """True if an <a>'s class list looks like a button/CTA (so we treat its label as editable)."""
    cls = attrs.get("class", "")
    return bool(re.search(r"\b(button|btn|cta|uk-button)\b", cls))


class _Annotator(HTMLParser):
    """Streaming parser that records data-cms insertions and manifest entries.

    Inputs: raw page source + page slug. Output: self.insertions (pos, text) and
    self.entries (manifest rows). No file I/O here — the caller applies insertions.
    """

    def __init__(self, raw, slug, has_content):
        super().__init__(convert_charrefs=True)
        self.raw = raw
        self.slug = slug
        self.has_content = has_content
        self.line_starts = self._index_lines(raw)
        self.stack = []          # open elements: {tag, id, key, buf, ...}
        self.counters = {}       # (section, ctype) -> running n
        self.insertions = []     # (abs_pos, " data-cms=\"...\"")
        self.entries = []        # manifest rows
        self.relpath = ""

    @staticmethod
    def _index_lines(raw):
        # Line starts indexed on '\n' only, to match HTMLParser.getpos() line counting.
        # (A lone '\r' is treated as ordinary line content, so CRLF positions stay correct.)
        offs = [0]
        for i, ch in enumerate(raw):
            if ch == "\n":
                offs.append(i + 1)
        return offs

    def _abs(self):
        ln, col = self.getpos()
        return self.line_starts[ln - 1] + col

    def _in_content(self):
        """Are we inside the editable region? (#content subtree, or anywhere if no #content)."""
        if not self.has_content:
            return True
        return any(f["id"] == "content" for f in self.stack)

    def _nearest_section(self):
        for f in reversed(self.stack):
            sid = f["id"]
            if sid and not SKIP_SECTION_ID.search(sid):
                return sid
        return "content"

    def _key_for(self, ctype, existing=None):
        if existing:
            return existing
        sec = self._nearest_section()
        ck = (sec, ctype)
        self.counters[ck] = self.counters.get(ck, 0) + 1
        return f"{self.slug}.{sec}.{ctype}.{self.counters[ck]}"

    def _schedule_attr(self, tag, key):
        """Queue an insertion of ` data-cms="key"` right after `<tag`."""
        pos = self._abs() + 1 + len(tag)  # after '<' + tag name
        self.insertions.append((pos, f' data-cms="{key}"'))

    def _record(self, key, ctype, attr, value, section, tag):
        self.entries.append({
            "key": key, "page": self.relpath, "type": ("attr" if attr else "text"),
            "attr": attr, "value": value, "section": section, "tag": tag, "ctype": ctype,
        })

    # --- HTMLParser hooks ---
    def handle_starttag(self, tag, attrs):
        ad = {k: (v or "") for k, v in attrs}
        editable, ctype, existing = False, None, ad.get("data-cms")
        if self._in_content():
            if tag == "img":
                src = ad.get("src", "")
                if not (src.endswith(".svg") and "logo" in src):
                    editable, ctype = True, "image"
            elif tag in TEXT_TAGS:
                editable, ctype = True, (tag if tag in HEADINGS else "text")
            elif tag == "a" and _is_cta(ad):
                editable, ctype = True, "cta"

        key = None
        if editable:
            key = self._key_for(ctype, existing)
            if not existing:
                self._schedule_attr(tag, key)
            section = self._nearest_section()
            if tag == "img":  # void: capture attrs now, no text buffer
                self._record(key, ctype, "src", ad.get("src", ""), section, tag)
                if ad.get("alt"):
                    self._record(key, ctype, "alt", ad.get("alt", ""), section, tag)

        if tag not in VOID:
            self.stack.append({
                "tag": tag, "id": ad.get("id", ""),
                "key": key if (editable and tag != "img") else None,
                "ctype": ctype if editable else None,
                "section": self._nearest_section() if editable else None,
                "buf": [] if (editable and tag != "img") else None,
            })

    def handle_startendtag(self, tag, attrs):
        # self-closing form (e.g. <img ... />): handle as a void start tag
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        for f in self.stack:
            if f["buf"] is not None:
                f["buf"].append(data)

    def handle_endtag(self, tag):
        # pop to the matching open tag (tolerant of minor nesting slips)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                frame = self.stack[i]
                del self.stack[i:]
                if frame["key"] and frame["buf"] is not None:
                    value = re.sub(r"\s+", " ", "".join(frame["buf"])).strip()
                    if value:
                        self._record(frame["key"], frame["ctype"], None, value,
                                     frame["section"], frame["tag"])
                return


def annotate(root, relpath, write=False):
    """Annotate one page. Inputs: site root, page relpath, write flag.
    Returns manifest entries; if write=True, injects data-cms into the file in place."""
    path = os.path.join(root, relpath)
    # newline="" preserves the file's exact (mixed CRLF/LF) line endings — no normalization.
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        raw = f.read()
    has_content = bool(re.search(r"""id=['"]content['"]""", raw))
    p = _Annotator(raw, page_slug(relpath), has_content)
    p.relpath = relpath
    p.feed(raw)
    p.close()
    if write and p.insertions:
        out = raw
        for pos, text in sorted(p.insertions, key=lambda x: x[0], reverse=True):
            out = out[:pos] + text + out[pos:]
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(out)
    return p.entries


if __name__ == "__main__":
    root, rel = sys.argv[1], sys.argv[2]
    entries = annotate(root, rel, write="--write" in sys.argv)
    print(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"\n# {len(entries)} items on {rel}", file=sys.stderr)
