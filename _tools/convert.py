#!/usr/bin/env python3
"""Convert an MkDocs-style lesson markdown file into a Jekyll post.

Fully automatic: derives title, subtitle, date, slug, and whether to demote
headings from the file's own header block. Prints the path of the post written.

Usage:
    convert.py <input.md> [--posts-dir DIR] [--title T] [--date YYYY-MM-DD] [--subtitle S]

The optional flags override the auto-derived values if you ever need to.
"""
import argparse
import os
import re
import sys

MONTHS = ("January February March April May June July August September "
          "October November December").split()
MONTH_RE = "|".join(MONTHS)


def split_header(text):
    """Return (header_block, body) split on the first horizontal-rule `---`."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:]).lstrip("\n")
    # No rule: treat a leading H1 + following non-blank lines as the header.
    return "", text


def derive_date(header, fallback_name):
    """Find 'Month DD, YYYY' in the header; fall back to date in filename."""
    m = re.search(r"\b(%s)\s+(\d{1,2}),?\s+(\d{4})\b" % MONTH_RE, header)
    if m:
        mon = MONTHS.index(m.group(1)) + 1
        return "%s-%02d-%02d" % (m.group(3), mon, int(m.group(2)))
    # Filename like June27_2026 or June26-2_2026
    m = re.search(r"\b(%s)\s*(\d{1,2}).*?(\d{4})" % MONTH_RE, fallback_name)
    if m:
        mon = MONTHS.index(m.group(1)) + 1
        return "%s-%02d-%02d" % (m.group(3), mon, int(m.group(2)))
    raise SystemExit("Could not derive a date from the header or filename.")


def derive_title(header):
    """Prefer the first quoted article title; else the cleaned H1."""
    q = re.search(r'"([^"]{3,})"', header)
    if q:
        return q.group(1).strip()
    h1 = re.search(r"^#\s+(.+)$", header, re.MULTILINE)
    if h1:
        # Drop trailing " — Study Guide" style suffixes.
        return re.sub(r"\s*[—-]\s*(study guide|.*lesson.*)$", "", h1.group(1),
                      flags=re.IGNORECASE).strip()
    raise SystemExit("Could not derive a title from the header.")


def derive_subtitle(header, title):
    """Build a clean one-line subtitle from the descriptive meta lines."""
    date_re = re.compile(r"\s*(%s)\s+\d{1,2},?\s+\d{4}" % MONTH_RE)
    cleaned = []
    for raw in header.splitlines():
        s = raw.strip().strip("*_ ")
        if not s or s.startswith("#"):
            continue
        # An 'Article: "Title" by/| ...' line -> keep only the attribution.
        m = re.match(r'article:\s*"[^"]*"\s*(.*)', s, re.IGNORECASE)
        if m:
            tail = m.group(1).strip()
            if tail.lower().startswith("by "):
                s = "Article by " + tail[3:].strip()
            elif tail:
                s = tail.lstrip("|·- ").strip()
            else:
                s = ""
        # Drop any embedded date, normalise separators, tidy edges.
        s = date_re.sub("", s)
        s = re.sub(r"\s*\|\s*", " · ", s)
        s = s.strip(" ·—-")
        # Skip empties, the bare title, and duplicates.
        if s and s.lower() != title.lower() and s not in cleaned:
            cleaned.append(s)
    return (" · ".join(cleaned))[:160]


def slugify(title):
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-{2,}", "-", s)[:60] or "lesson"


def demote_headings(text):
    out = []
    for ln in text.splitlines():
        m = re.match(r"^(#{1,6})(\s+)", ln)
        if m and len(m.group(1)) < 6:
            ln = "#" + ln
        out.append(ln)
    return "\n".join(out)


ADMON = re.compile(r'^!!!\s+(\w+)(?:\s+"([^"]*)")?\s*$')


def convert_admonitions(text):
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        m = ADMON.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        atype, title = m.group(1).lower(), m.group(2)
        i += 1
        body = []
        while i < len(lines) and (lines[i].strip() == "" or lines[i].startswith("    ")):
            body.append(lines[i][4:] if lines[i].startswith("    ") else "")
            i += 1
        while body and body[0] == "":
            body.pop(0)
        while body and body[-1] == "":
            body.pop()
        out.append("")
        quoted = ([title and "**" + title + "**", ""] if title else []) + body
        for bl in [q for q in quoted if q is not None]:
            out.append(">" if bl == "" else "> " + bl)
        out.append("{: .callout .callout-%s}" % atype)
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--posts-dir", default="_posts")
    ap.add_argument("--title")
    ap.add_argument("--date")
    ap.add_argument("--subtitle")
    a = ap.parse_args()

    with open(a.input, encoding="utf-8") as f:
        text = f.read()
    header, body = split_header(text)
    name = os.path.basename(a.input)

    date = a.date or derive_date(header, name)
    title = a.title or derive_title(header)
    subtitle = a.subtitle or derive_subtitle(header, title)

    # Demote only if the body still has level-1 headings (keeps a single page H1).
    if re.search(r"^#\s+", body, re.MULTILINE):
        body = demote_headings(body)
    body = convert_admonitions(body)

    out_path = os.path.join(a.posts_dir, "%s-%s.md" % (date, slugify(title)))
    fm = ('---\ntitle: "%s"\nsubtitle: "%s"\ndate: %s\n---\n\n'
          % (title.replace('"', "'"), subtitle.replace('"', "'"), date))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(fm + body.strip() + "\n")
    print(out_path)


if __name__ == "__main__":
    main()
