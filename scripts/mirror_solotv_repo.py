#!/usr/bin/env python3
"""Generate SoLoTV-branded addons.xml (catalog metadata) for repository.solotv."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SOLOTV_REPO = ROOT / "public" / "solotv" / "repo"
UPSTREAM_ADDONS_XML = (
    "https://raw.githubusercontent.com/nebulous42069/Omega/main/omega/zips/addons.xml"
)

TEXT_REPLACEMENTS = (
    (re.compile(r"\bDiggz\b"), "SoLoTV"),
    (re.compile(r"\bChef Omega Wizard\b", re.I), "SoLoTV Build Wizard"),
    (re.compile(r"\bChef Omega\b", re.I), "SoLoTV Build Wizard"),
)


def fetch(url: str) -> str:
    with urlopen(url, timeout=120) as response:
        return response.read().decode("utf-8", errors="ignore")


def rebrand_text(value: str) -> str:
    for pattern, replacement in TEXT_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    return value


def rebrand_addons_xml(content: str) -> str:
    def rewrite_addon_block(block: str) -> str:
        if 'id="plugin.program.chef21"' not in block and 'provider-name="Diggz"' not in block:
            if not re.search(r'id="plugin\.program\.[^"]+"[^>]*name="[^"]*Diggz', block):
                return block

        block = re.sub(
            r'(<addon[^>]*name=")([^"]*)(")',
            lambda match: match.group(1) + rebrand_text(match.group(2)) + match.group(3),
            block,
            count=1,
        )
        block = re.sub(
            r"(<summary[^>]*>)(.*?)(</summary>)",
            lambda match: match.group(1) + rebrand_text(match.group(2)) + match.group(3),
            block,
            flags=re.S | re.I,
        )
        block = re.sub(
            r"(<description[^>]*>)(.*?)(</description>)",
            lambda match: match.group(1) + rebrand_text(match.group(2)) + match.group(3),
            block,
            flags=re.S | re.I,
        )
        block = block.replace('provider-name="Diggz"', 'provider-name="SoLoVision"')
        return block

    parts = []
    last = 0
    for match in re.finditer(r"<addon\s", content):
        if match.start() > last:
            parts.append(content[last : match.start()])
        end = content.find("</addon>", match.start())
        if end == -1:
            parts.append(content[match.start() :])
            break
        end += len("</addon>")
        block = content[match.start() : end]
        parts.append(rewrite_addon_block(block))
        last = end
    parts.append(content[last:])
    return "".join(parts)


def main() -> int:
    PUBLIC_SOLOTV_REPO.mkdir(parents=True, exist_ok=True)
    print("Fetching upstream catalog...")
    upstream = fetch(UPSTREAM_ADDONS_XML)
    rebranded = rebrand_addons_xml(upstream)
    addons_path = PUBLIC_SOLOTV_REPO / "addons.xml"
    addons_path.write_text(rebranded, encoding="utf-8", newline="\n")
    md5 = hashlib.md5(addons_path.read_bytes()).hexdigest()
    (PUBLIC_SOLOTV_REPO / "addons.xml.md5").write_text(md5, encoding="utf-8")
    print(f"Wrote {addons_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
