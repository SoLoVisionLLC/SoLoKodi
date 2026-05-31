#!/usr/bin/env python3
"""
Mirror the Xenon/Omega add-on catalog to public/solotv/repo/ with SoLoTV branding.

Downloads each package listed in upstream addons.xml, patches metadata inside ZIPs,
writes a SoLo-branded addons.xml, and excludes upstream Diggz repository add-ons.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SOLOTV_REPO = ROOT / "public" / "solotv" / "repo"
UPSTREAM_ADDONS_XML = (
    "https://raw.githubusercontent.com/nebulous42069/Omega/main/omega/zips/addons.xml"
)
UPSTREAM_ZIPS_BASE = (
    "https://raw.githubusercontent.com/nebulous42069/Omega/main/omega/zips/"
)
GITHUB_TREE_URL = "https://api.github.com/repos/nebulous42069/Omega/git/trees/main?recursive=1"

# Do not ship competing Diggz repository add-ons inside SoLoTV repo.
EXCLUDE_ADDON_IDS = frozenset({"repository.diggz", "repository.diggz22"})

# Display-text rebranding (never rewrite add-on id attributes).
TEXT_REPLACEMENTS = (
    (re.compile(r"\bDiggz Xenon 2\b", re.I), "SoLoTV Xenon 2"),
    (re.compile(r"\bDiggz Xenon\b", re.I), "SoLoTV Xenon"),
    (re.compile(r"\bDiggzFlix 2\b", re.I), "SoLoTV Flix 2"),
    (re.compile(r"\bDiggzFlix\b", re.I), "SoLoTV Flix"),
    (re.compile(r"\bDiggz Kidz\b", re.I), "SoLoTV Kids Skin"),
    (re.compile(r"\bDiggz 4K Wallpapers\b", re.I), "SoLoTV 4K Wallpapers"),
    (re.compile(r"\bDiggz TV Guide Lite\b", re.I), "SoLoTV Guide Lite"),
    (re.compile(r"\bDiggz Simple Clean\b", re.I), "SoLoTV Simple Clean"),
    (re.compile(r"\bDiggz Skin Switcher\b", re.I), "SoLoTV Skin Switcher"),
    (re.compile(r"\bDiggz Repository\b", re.I), "SoLoTV Repository"),
    (re.compile(r"\bChef Omega Wizard\b", re.I), "SoLoTV Build Wizard"),
    (re.compile(r"\bChef Wizard\b", re.I), "SoLoTV Build Wizard"),
    (re.compile(r"\bChef Omega\b", re.I), "SoLoTV Build Wizard"),
    (re.compile(r"\bDiggz\b"), "SoLoTV"),
    (re.compile(r"\bDIGGZ\b"), "SoLoVision"),
)

PATCH_INSIDE_ZIP_SUFFIXES = (
    ".xml",
    ".txt",
    ".md",
    ".properties",
    ".ini",
    ".json",
    ".lang",
    ".po",
)
PATCH_INSIDE_ZIP_NAMES = ("addon.xml",)


def fetch_bytes(url: str, timeout: int = 180) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return response.read()


def fetch_text(url: str, timeout: int = 120) -> str:
    return fetch_bytes(url, timeout=timeout).decode("utf-8", errors="ignore")


def rebrand_text(value: str) -> str:
    for pattern, replacement in TEXT_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    return value


def load_upstream_addons_xml() -> ET.Element:
    raw = fetch_text(UPSTREAM_ADDONS_XML)
    return ET.fromstring(raw)


def list_catalog_addons(root: ET.Element) -> list[tuple[str, str]]:
    items = []
    for addon in root.findall("addon"):
        addon_id = addon.get("id")
        version = addon.get("version")
        if not addon_id or not version:
            continue
        if addon_id in EXCLUDE_ADDON_IDS:
            continue
        items.append((addon_id, version))
    return items


def build_zip_index() -> dict[str, list[tuple[str, str]]]:
    """Map addon_id -> [(version, github_path), ...] sorted by version."""
    import json

    payload = json.loads(fetch_text(GITHUB_TREE_URL, timeout=180))
    index: dict[str, list[tuple[str, str]]] = {}
    prefix = "omega/zips/"
    for entry in payload.get("tree", []):
        path = entry.get("path", "")
        if not path.startswith(prefix) or not path.endswith(".zip"):
            continue
        rel = path[len(prefix) :]
        parts = rel.split("/")
        if len(parts) != 2:
            continue
        addon_id, zip_name = parts
        if not zip_name.startswith(addon_id + "-") or not zip_name.endswith(".zip"):
            continue
        version = zip_name[len(addon_id) + 1 : -4]
        index.setdefault(addon_id, []).append((version, path))

    def version_key(pair: tuple[str, str]) -> tuple:
        version = pair[0]
        chunks = []
        for piece in re.split(r"[.\-]", version):
            chunks.append(int(piece) if piece.isdigit() else piece)
        return tuple(chunks)

    for addon_id in index:
        index[addon_id].sort(key=version_key)
    return index


def url_exists(url: str) -> bool:
    request = Request(url, method="HEAD")
    try:
        with urlopen(request, timeout=30) as response:
            return response.status < 400
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def resolve_zip_path(
    addon_id: str,
    version: str,
    zip_index: dict[str, list[tuple[str, str]]],
) -> str | None:
    direct_path = f"omega/zips/{addon_id}/{addon_id}-{version}.zip"
    direct_url = (
        "https://raw.githubusercontent.com/nebulous42069/Omega/main/" + direct_path
    )
    if url_exists(direct_url):
        return direct_path

    candidates = zip_index.get(addon_id) or []
    for candidate_version, path in reversed(candidates):
        if candidate_version == version:
            return path
    if candidates:
        return candidates[-1][1]
    return None


def rebrand_addon_xml_content(content: str, addon_id: str) -> str:
    if addon_id == "plugin.program.chef21":
        content = re.sub(
            r'name="[^"]*"',
            'name="SoLoTV Build Wizard"',
            content,
            count=1,
        )
    content = re.sub(
        r'provider-name="Diggz"',
        'provider-name="SoLoVision"',
        content,
        flags=re.I,
    )
    content = re.sub(
        r"(<summary[^>]*>)(.*?)(</summary>)",
        lambda match: match.group(1) + rebrand_text(match.group(2)) + match.group(3),
        content,
        flags=re.S | re.I,
    )
    content = re.sub(
        r"(<description[^>]*>)(.*?)(</description>)",
        lambda match: match.group(1) + rebrand_text(match.group(2)) + match.group(3),
        content,
        flags=re.S | re.I,
    )
    content = re.sub(
        r'(<addon[^>]*name=")([^"]*)(")',
        lambda match: match.group(1) + rebrand_text(match.group(2)) + match.group(3),
        content,
        count=1,
    )
    return rebrand_text(content)


def should_patch_zip_member(name: str) -> bool:
    lower = name.lower()
    if lower.endswith(PATCH_INSIDE_ZIP_SUFFIXES):
        return True
    return any(part in lower for part in PATCH_INSIDE_ZIP_NAMES)


def _is_downloader_bytecode(name: str) -> bool:
    lower = name.lower()
    return "modules/downloader" in lower and lower.endswith(".pyc")


def patch_wizard_downloader_code(name: str, data: bytes) -> bytes:
    """Make chef21's build downloader robust to missing Content-Length.

    Upstream falls back to ``response.read(chunksize)`` when the response has no
    Content-Length, but a ``requests.Response`` has no ``read`` (it crashes on
    CDN cache misses that stream with chunked transfer-encoding).
    ``response.raw.read`` is the urllib3 reader and works in both cases.
    """
    if name.lower().endswith("modules/downloader.py"):
        return data.replace(b"response.read(", b"response.raw.read(")
    return data


def patch_zip_contents(zip_bytes: bytes, addon_id: str) -> bytes:
    input_buffer = io.BytesIO(zip_bytes)
    output_buffer = io.BytesIO()
    is_wizard = addon_id == "plugin.program.chef21"
    with zipfile.ZipFile(input_buffer, "r") as source:
        with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                # Drop stale downloader bytecode so our patched .py is used.
                if is_wizard and _is_downloader_bytecode(item.filename):
                    continue
                data = source.read(item.filename)
                if is_wizard:
                    data = patch_wizard_downloader_code(item.filename, data)
                if should_patch_zip_member(item.filename):
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        target.writestr(item, data)
                        continue
                    text = rebrand_addon_xml_content(text, addon_id) if item.filename.endswith(
                        "addon.xml"
                    ) else rebrand_text(text)
                    data = text.encode("utf-8")
                target.writestr(item, data)
    return output_buffer.getvalue()


def rebrand_catalog_xml(root: ET.Element) -> ET.Element:
    for node in list(root.findall("addon")):
        if node.get("id") in EXCLUDE_ADDON_IDS:
            root.remove(node)

    for addon in root.findall("addon"):
        name = addon.get("name")
        if name:
            addon.set("name", rebrand_text(name))
        provider = addon.get("provider-name")
        if provider and re.search(r"diggz", provider, re.I):
            addon.set("provider-name", rebrand_text(provider))

        for tag in ("summary", "description", "disclaimer", "news"):
            for node in addon.findall(tag):
                if node.text:
                    node.text = rebrand_text(node.text)
                for key, value in list(node.attrib.items()):
                    if value:
                        node.set(key, rebrand_text(value))

        if addon.get("id") == "plugin.program.chef21":
            addon.set("name", "SoLoTV Build Wizard")
            addon.set("provider-name", "SoLoVision")

    return root


def write_addons_xml(root: ET.Element) -> None:
    xml_bytes = ET.tostring(root, encoding="utf-8")
    declaration = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    addons_path = PUBLIC_SOLOTV_REPO / "addons.xml"
    addons_path.write_bytes(declaration + xml_bytes)
    md5 = hashlib.md5(addons_path.read_bytes()).hexdigest()
    (PUBLIC_SOLOTV_REPO / "addons.xml.md5").write_text(md5, encoding="utf-8")


def mirror_packages(
    catalog: list[tuple[str, str]],
    zip_index: dict[str, list[tuple[str, str]]],
    skip_existing: bool = True,
) -> tuple[int, int, list[str]]:
    ok = 0
    failed = []
    for index, (addon_id, version) in enumerate(catalog, start=1):
        github_path = resolve_zip_path(addon_id, version, zip_index)
        if not github_path:
            failed.append(f"{addon_id}-{version} (no zip on upstream)")
            continue

        out_dir = PUBLIC_SOLOTV_REPO / addon_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{addon_id}-{version}.zip"
        if skip_existing and out_path.exists() and out_path.stat().st_size > 1000:
            ok += 1
            print(f"[{index}/{len(catalog)}] skip {out_path.name}")
            continue

        url = f"https://raw.githubusercontent.com/nebulous42069/Omega/main/{github_path}"
        print(f"[{index}/{len(catalog)}] {addon_id}-{version}")
        try:
            raw = fetch_bytes(url)
            patched = patch_zip_contents(raw, addon_id)
            out_path.write_bytes(patched)
            ok += 1
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            failed.append(f"{addon_id}-{version} ({exc})")

    return ok, len(catalog), failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Mirror SoLoTV streaming catalog")
    parser.add_argument(
        "--xml-only",
        action="store_true",
        help="Only regenerate addons.xml (no ZIP downloads)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download ZIPs even if they already exist",
    )
    args = parser.parse_args()

    PUBLIC_SOLOTV_REPO.mkdir(parents=True, exist_ok=True)
    print("Loading upstream catalog...")
    root = load_upstream_addons_xml()
    catalog = list_catalog_addons(root)
    root = rebrand_catalog_xml(root)
    write_addons_xml(root)
    print(f"Wrote addons.xml ({len(catalog)} add-ons, excluded Diggz repos)")

    if args.xml_only:
        return 0

    print("Indexing upstream ZIP paths...")
    zip_index = build_zip_index()
    ok, total, failed = mirror_packages(
        catalog,
        zip_index,
        skip_existing=not args.force,
    )
    print(f"Mirrored {ok}/{total} packages to {PUBLIC_SOLOTV_REPO}")
    if failed:
        print("Failures:", file=sys.stderr)
        for line in failed:
            print(f"  - {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
