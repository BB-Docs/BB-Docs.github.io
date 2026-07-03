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


# H1 headings too generic to use as a lesson title.
GENERIC_H1 = {
    "kabbalah class notes", "kabbalah lesson study guide", "study guide",
    "lesson notes", "kabbalah study notes", "class notes",
    "kabbalah study guide", "morning lesson", "morning lessons",
}


def decamel(s):
    """Split a run-together CamelCase token into words, only if it has no
    spaces (e.g. 'AdheringToTheFriends' -> 'Adhering To The Friends')."""
    if " " in s or not re.search(r"[a-z][A-Z]", s):
        return s
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    return s


def filename_topic(name):
    """Pull a human title out of a filename like
    'June27_2026 Afternoon Help From Above_MD.md' -> 'Help From Above'."""
    s = os.path.splitext(name)[0]
    # date token, tolerating a day-suffix letter (July3A) or -2 style repeat marker
    s = re.sub(r"(%s)\s*\d{1,2}[A-Za-z]?(-\d+)?[_ ]\d{4}" % MONTH_RE, " ", s, flags=re.I)
    s = re.sub(r"[_]+", " ", s)
    s = re.sub(r"\b(MD|Morning|Afternoon|Evening)\b", " ", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip(" -_")
    return s


def split_header(text):
    """Return (header_block, body) split on the first horizontal-rule `---`."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:]).lstrip("\n")
    return "", text


def parse_header(header):
    """Return (h1, meta_lines) with markdown emphasis stripped from meta."""
    h1 = None
    meta = []
    for raw in header.splitlines():
        t = raw.strip()
        if t.startswith("#"):
            if h1 is None:
                h1 = re.sub(r"^#+\s*", "", t).strip()
            continue
        s = raw.replace("*", "").strip().strip("_ ").strip()
        if s:
            meta.append(s)
    return h1, meta


def get_label(line):
    """Split 'Label: value' -> ('Label', 'value'); else (None, line)."""
    m = re.match(r"([A-Za-z][A-Za-z ]{1,20}):\s*(.*)", line)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, line)


def derive_date(header, name):
    """Prefer the date in the filename; else the latest date in the header."""
    m = re.search(r"(%s)\s*(\d{1,2}).*?(\d{4})" % MONTH_RE, name)
    if m:
        return "%s-%02d-%02d" % (m.group(3), MONTHS.index(m.group(1)) + 1,
                                 int(m.group(2)))
    dates = re.findall(r"(%s)\s+(\d{1,2}),?\s+(\d{4})" % MONTH_RE, header)
    if dates:
        ymd = max((int(y), MONTHS.index(mn) + 1, int(d)) for mn, d, y in dates)
        return "%04d-%02d-%02d" % ymd
    raise SystemExit("Could not derive a date from the filename or header.")


def derive_title(h1, meta, name):
    """Topic: line > first quoted phrase > non-generic H1 > filename topic."""
    for line in meta:
        lbl, val = get_label(line)
        if lbl and lbl.lower() == "topic" and val:
            return val
    for line in meta:
        q = re.search(r'"([^"]{3,})"', line)
        if q:
            return q.group(1).strip()
    if h1:
        c = re.sub(r"\s*[—-]\s*study guide$", "", h1, flags=re.IGNORECASE).strip()
        if c.lower() not in GENERIC_H1:
            return c
    ft = filename_topic(name)
    return ft or h1 or "Lesson"


def derive_subtitle(meta, title, post_date):
    """One-line subtitle from meta lines, minus the title and the post date."""
    y, mo, d = post_date.split("-")
    post_date_re = re.compile(
        r"%s\s+0?%d,?\s+%s" % (MONTHS[int(mo) - 1], int(d), y), re.IGNORECASE)
    parts = []
    for line in meta:
        lbl, val = get_label(line)
        if lbl and lbl.lower() == "topic":       # that's the title
            continue
        s = line
        m = re.match(r'article:\s*"[^"]*"\s*(.*)', s, re.IGNORECASE)
        if m:                                     # 'Article: "Title" by X' -> 'Article by X'
            tail = m.group(1).strip()
            if tail.lower().startswith("by "):
                s = "Article by " + tail[3:].strip()
            elif tail:
                s = tail.lstrip("|·- ").strip()
            else:
                s = ""
        s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)  # [text](url) -> text
        s = post_date_re.sub("", s)               # drop the date already in the post date
        s = re.sub(r"\s*\|\s*", " · ", s)
        s = re.sub(r"\s{2,}", " ", s).strip(" ·—-")
        if s and s.lower() != title.lower() and s not in parts:
            parts.append(s)
    sub = " · ".join(parts)
    if len(sub) > 170:                            # trim to a whole word, never mid-word
        sub = sub[:170].rsplit(" ", 1)[0].rstrip(" ·,—-") + "…"
    return sub


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    if len(s) > 70:                      # trim to whole words, never mid-word
        s = s[:70].rsplit("-", 1)[0]
    return s or "lesson"


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
    h1, meta = parse_header(header)
    name = os.path.basename(a.input)

    date = a.date or derive_date(header, name)
    title = a.title or decamel(derive_title(h1, meta, name))
    subtitle = a.subtitle if a.subtitle is not None else derive_subtitle(meta, title, date)

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
