#!/usr/bin/env python3
"""Convert MkDocs-style lesson markdown into Jekyll posts.

- Strips the leading H1 + meta header block (folded into front matter).
- Optionally demotes body headings by one level (so the page has a single H1).
- Converts `!!! type "Title"` admonitions into kramdown blockquotes with a
  `{: .callout .callout-type}` IAL so they render as styled callout boxes.
"""
import re
import sys


def strip_header(text):
    """Drop everything up to and including the first horizontal-rule `---`."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            return "\n".join(lines[i + 1:]).lstrip("\n")
    return text


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
        atype = m.group(1).lower()
        title = m.group(2)
        i += 1
        # Collect indented (4-space) body lines, allowing blank lines.
        body = []
        while i < len(lines) and (lines[i].strip() == "" or lines[i].startswith("    ")):
            body.append(lines[i][4:] if lines[i].startswith("    ") else "")
            i += 1
        # Trim leading/trailing blank lines in body.
        while body and body[0] == "":
            body.pop(0)
        while body and body[-1] == "":
            body.pop()
        # Emit as a blockquote with optional bold title, then the IAL.
        out.append("")
        quoted = []
        if title:
            quoted.append("**" + title + "**")
            quoted.append("")
        quoted.extend(body)
        for bl in quoted:
            out.append(">" if bl == "" else "> " + bl)
        out.append("{: .callout .callout-%s}" % atype)
        out.append("")
    return "\n".join(out)


def main():
    inp, outp, title, subtitle, date, demote = sys.argv[1:7]
    with open(inp, encoding="utf-8") as f:
        text = f.read()
    body = strip_header(text)
    if demote == "1":
        body = demote_headings(body)
    body = convert_admonitions(body)
    fm = (
        "---\n"
        'title: "%s"\n'
        'subtitle: "%s"\n'
        "date: %s\n"
        "---\n\n" % (title, subtitle, date)
    )
    with open(outp, "w", encoding="utf-8") as f:
        f.write(fm + body.strip() + "\n")
    print("wrote", outp)


if __name__ == "__main__":
    main()
