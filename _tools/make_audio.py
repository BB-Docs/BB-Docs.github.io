#!/usr/bin/env python3
"""Turn a lesson post into narration text and synthesize an MP3 with edge-tts.

  make_audio.py <post.md> <out.mp3>

Extracts readable prose from the Markdown (flattening tables, dropping the
callout/IAL syntax), applies a small Hebrew-term pronunciation dictionary so
the transliterated words aren't mangled, then narrates with a calm neural voice.
"""
import asyncio
import re
import sys

import edge_tts

VOICE = "en-US-AndrewNeural"
RATE = "-8%"            # a touch slower, for study pacing

# Respellings so an English neural voice says the recurring terms sensibly.
# Whole-word, case-insensitive. Extend freely — this is a best-effort starter.
PRONUNCIATION = {
    "Kelim": "Keleem", "Kli": "Klee", "Klipot": "Kleepote", "Klipa": "Kleepah",
    "Klipah": "Kleepah", "Kedusha": "Kedoosha", "Masach": "Masakh",
    "Dvekut": "Dvekoot", "Aravut": "Aravoot", "Arvut": "Arvoot",
    "Lishma": "Leeshma", "Zohar": "Zohar", "Rabash": "Rabaash",
    "Laitman": "Laetman", "Adam": "Ah dahm",
    "Baal HaSulam": "Baal Ha Sulaam", "Chesed": "Hesed", "Hesed": "Hesed",
    "Tzimtzum": "Tzimtzoom", "Partzuf": "Partzoof", "Sefirot": "Sefeerote",
    "Malchut": "Malhoot", "Chochma": "Hohma", "Bina": "Beena",
    "Gmar Tikkun": "Gmar Tikoon", "Tikkun": "Tikoon", "Shechina": "Shehina",
    "Nukva": "Nookva", "Yetzer HaRa": "Yetzer Hara", "Kabbalah": "Kabala",
    "Baal HaSulam's": "Baal Ha Sulam's",
}


def markdown_to_speech(md):
    out = []
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            out.append("")
            continue
        if re.match(r'^\{:', line.strip()):          # kramdown IAL line
            continue
        if re.match(r'^\|[\s:-]+\|?\s*$', line):      # table separator row
            continue
        if line.lstrip().startswith('|'):             # table row -> "cell, cell."
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            cells = [c for c in cells if c]
            if cells:
                out.append(", ".join(cells) + ".")
            continue
        line = re.sub(r'^\s{0,3}#{1,6}\s*', '', line)             # headings
        line = re.sub(r'^\s*[-*+]\s+', '', line)                  # bullets
        line = re.sub(r'^\s*\d+\.\s+', '', line)                  # numbered
        line = re.sub(r'^\s*>\s?', '', line)                      # blockquote
        line = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', line)      # links
        line = re.sub(r'[*_`#>]', '', line)                       # emphasis/code
        out.append(line.strip())
    text = "\n".join(out)
    text = re.sub(r'\n{2,}', ".\n", text)             # paragraph breaks -> sentence stop
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\.\s*\.', '.', text)
    return text.strip()


def apply_pronunciation(text):
    for term, say in sorted(PRONUNCIATION.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(r'\b' + re.escape(term) + r'\b', say, text, flags=re.IGNORECASE)
    return text


def post_to_text(path):
    raw = open(path, encoding="utf-8").read()
    fm = raw[:raw.index("---", 3) + 3] if raw.startswith("---") else ""
    title = re.search(r'title:\s*"?(.*?)"?\s*$', fm, re.M)
    body = raw.split("---", 2)[2] if raw.startswith("---") else raw
    spoken = markdown_to_speech(body)
    lead = (title.group(1) + ".\n\n") if title else ""
    return apply_pronunciation(lead + spoken)


def chunk(text, maxlen=1400):
    """Split into <=maxlen pieces on paragraph, then sentence, boundaries.
    edge-tts silently truncates long single requests, so we synthesize in
    pieces and concatenate (edge-tts MP3 frames concat cleanly)."""
    pieces, buf = [], ""
    for para in re.split(r'\n+', text):
        para = para.strip()
        if not para:
            continue
        units = re.split(r'(?<=[.!?])\s+', para) if len(para) > maxlen else [para]
        for u in units:
            if len(buf) + len(u) + 1 > maxlen and buf:
                pieces.append(buf.strip()); buf = ""
            buf += (" " if buf else "") + u
    if buf.strip():
        pieces.append(buf.strip())
    return pieces


async def synth(text, out):
    audio = bytearray()
    pieces = chunk(text)
    for i, piece in enumerate(pieces):
        for attempt in range(3):
            try:
                got = bytearray()
                async for m in edge_tts.Communicate(piece, VOICE, rate=RATE).stream():
                    if m["type"] == "audio":
                        got += m["data"]
                if not got:
                    raise RuntimeError("empty audio")
                audio += got
                break
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"chunk {i+1}/{len(pieces)} failed: {e}")
                await asyncio.sleep(1.5)
    with open(out, "wb") as f:
        f.write(audio)
    return len(pieces)


def main():
    post, out = sys.argv[1], sys.argv[2]
    text = post_to_text(post)
    words = len(text.split())
    n = asyncio.run(synth(text, out))
    print(f"{out}  ({words} words, {n} chunks)")


if __name__ == "__main__":
    main()
