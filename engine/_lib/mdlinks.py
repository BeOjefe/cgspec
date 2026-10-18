"""Markdown link extraction: inline, angle-bracket, reference-style and HTML href targets."""

from __future__ import annotations

import re

INLINE_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*(<[^>\n]*>|(?:[^()\s]|\([^()\s]*\))+)(?:\s+[\"'][^\"']*[\"'])?\s*\)")
REF_USE = re.compile(r"(?<![\]\\])\[([^\]\n]+)\]\[([^\]\n]*)\]")
REF_DEF = re.compile(r"^\s{0,3}\[(?!\^)([^\]\n]+)\]:\s*(<[^>\n]*>|\S+)", re.M)
HREF = re.compile(r"<a\s[^>]*href=[\"']([^\"']+)[\"']", re.I)
CODE_SPAN = re.compile(r"`[^`\n]*`")
FENCE = re.compile(r"^```.*?^```", re.S | re.M)


def link_targets(text: str) -> list[str]:
    text = CODE_SPAN.sub("", FENCE.sub("", text))
    defs = {m.group(1).lower(): m.group(2) for m in REF_DEF.finditer(text)}
    targets = [m.group(1) for m in INLINE_LINK.finditer(text)] + HREF.findall(text)
    for label, ref in REF_USE.findall(text):
        key = (ref or label).lower()
        if key in defs:
            targets.append(defs[key])
    targets += [t for t in defs.values()]
    return [t[1:-1] if t.startswith("<") and t.endswith(">") else t for t in targets]
