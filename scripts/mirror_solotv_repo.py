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
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "solotv_build" / "build.json"
PUBLIC_SOLOTV_REPO = ROOT / "public" / "solotv" / "repo"
SOLOTV_WIZARD_VERSION = "502.1"
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

PATCHED_WIZARD_DOWNLOADER = r'''import os
import sys
import zipfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ICON = ADDON.getAddonInfo('icon')

class Downloader:
    def __init__(self, url):
        self.url = url
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Referer": "https://github.com/",
            "Connection": "close",
        }

    def _open(self):
        request = Request(self.url, headers=self.headers)
        return urlopen(request, timeout=120)

    def get_length(self, response):
        length = response.headers.get('Content-Length')
        return int(length) if length else None

    def download_build(self, name, zippath):
        dp = xbmcgui.DialogProgress()
        cancelled = False
        chunksize = 1000000
        size = 0
        length = None

        try:
            response = self._open()
        except (HTTPError, URLError, OSError) as exc:
            xbmcgui.Dialog().ok(ADDON_NAME, 'Download failed: {0}'.format(exc))
            raise

        with response:
            length = self.get_length(response)
            if length is not None:
                length2 = int(length / 1000000)
                dp.create(f'{name} - {length2}MB', 'Downloading your build...')
            else:
                length2 = 'Unknown Size'
                dp.create(f'{name} - {length2}', 'Downloading your build...')

            dp.update(0, 'Downloading your build...')
            with open(zippath, 'wb') as f:
                while True:
                    chunk = response.read(chunksize)
                    if not chunk:
                        break
                    size += len(chunk)
                    size2 = int(size / 1000000)
                    f.write(chunk)
                    if length:
                        perc = int(size / length * 100)
                        dp.update(perc, f'Downloading your build...\n{size2}/{length2} MB')
                    else:
                        dp.update(50, f'Downloading your build...\n{size2} MB')
                    if dp.iscanceled():
                        cancelled = True
                        break

        if cancelled is True:
            dp.close()
            if os.path.exists(zippath):
                os.unlink(zippath)
            dialog = xbmcgui.Dialog()
            dialog.notification(ADDON_NAME, 'Download Cancelled', icon=ICON)
            sys.exit()

        if length is not None and size != length:
            dp.close()
            if os.path.exists(zippath):
                os.unlink(zippath)
            xbmcgui.Dialog().ok(
                ADDON_NAME,
                'Download incomplete: {0}/{1} bytes'.format(size, length),
            )
            raise IOError('Downloaded build was incomplete')

        if not zipfile.is_zipfile(zippath):
            dp.close()
            if os.path.exists(zippath):
                os.unlink(zippath)
            xbmcgui.Dialog().ok(ADDON_NAME, 'Downloaded build is not a valid ZIP file.')
            raise zipfile.BadZipFile('Downloaded build is not a valid ZIP file')

        if length is not None:
            dp.update(100, f'Downloading your build...Done!\n{int(size/1000000)}/{length2} MB')
        else:
            dp.update(100, f'Downloading your build...Done!\n{int(size/1000000)} MB')

        xbmc.sleep(500)
        dp.close()
'''


def fetch_bytes(url: str, timeout: int = 180) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return response.read()


def fetch_text(url: str, timeout: int = 120) -> str:
    return fetch_bytes(url, timeout=timeout).decode("utf-8", errors="ignore")


def rebrand_text(value: str) -> str:
    for pattern, replacement in TEXT_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    return value


def load_wizard_sources() -> dict[str, str]:
    if not CONFIG.exists():
        return {}
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return {
        key: str(value)
        for key, value in (config.get("wizard_sources") or {}).items()
        if value
    }


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
            r'(<addon\b[^>]*\sversion=")[^"]*(")',
            r'\g<1>{0}\2'.format(SOLOTV_WIZARD_VERSION),
            content,
            count=1,
        )
        content = re.sub(
            r"\s*<import\s+addon=\"script\.module\.requests\"[^>]*/>\s*",
            "\n",
            content,
            flags=re.I,
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


def _is_stale_wizard_bytecode(name: str) -> bool:
    lower = name.lower()
    if not lower.endswith(".pyc"):
        return False
    return (
        "modules/downloader" in lower
        or "modules/build_install" in lower
        or "uservar" in lower
    )


def patch_wizard_downloader_code(name: str, data: bytes) -> bytes:
    if name.lower().endswith("modules/downloader.py"):
        return PATCHED_WIZARD_DOWNLOADER.encode("utf-8")
    return data


def patch_wizard_build_install_code(name: str, data: bytes) -> bytes:
    if not name.lower().endswith("modules/build_install.py"):
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data

    text = text.replace(
        "from zipfile import ZipFile",
        "from zipfile import ZipFile, is_zipfile",
        1,
    )
    marker = "    download_build(name, url)\n    save_backup_restore('backup')"
    replacement = (
        "    download_build(name, url)\n"
        "    if not is_zipfile(zippath):\n"
        "        if os.path.exists(zippath):\n"
        "            os.unlink(zippath)\n"
        "        dialog.ok(addon_name, 'Downloaded build is not a valid ZIP file.')\n"
        "        return\n"
        "    save_backup_restore('backup')"
    )
    if marker in text and "if not is_zipfile(zippath):" not in text:
        text = text.replace(marker, replacement, 1)
    return text.encode("utf-8")


def patch_wizard_uservar_code(
    name: str,
    data: bytes,
    wizard_sources: dict[str, str],
) -> bytes:
    if not wizard_sources or not name.lower().endswith("/uservar.py"):
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data

    for var_name, url in wizard_sources.items():
        pattern = r"(?m)^(\s*{0}\s*=\s*).*$".format(re.escape(var_name))
        text = re.sub(pattern, r"\g<1>'{0}'".format(url), text, count=1)
    return text.encode("utf-8")


def patch_zip_contents(
    zip_bytes: bytes,
    addon_id: str,
    wizard_sources: dict[str, str],
) -> bytes:
    input_buffer = io.BytesIO(zip_bytes)
    output_buffer = io.BytesIO()
    is_wizard = addon_id == "plugin.program.chef21"
    with zipfile.ZipFile(input_buffer, "r") as source:
        with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                # Drop stale bytecode so our patched Python sources are used.
                if is_wizard and _is_stale_wizard_bytecode(item.filename):
                    continue
                data = source.read(item.filename)
                if is_wizard:
                    data = patch_wizard_downloader_code(item.filename, data)
                    data = patch_wizard_build_install_code(item.filename, data)
                    data = patch_wizard_uservar_code(
                        item.filename,
                        data,
                        wizard_sources,
                    )
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
            addon.set("version", SOLOTV_WIZARD_VERSION)
            requires = addon.find("requires")
            if requires is not None:
                for child in list(requires):
                    if child.attrib.get("addon") == "script.module.requests":
                        requires.remove(child)

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
    wizard_sources: dict[str, str],
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
        package_version = (
            SOLOTV_WIZARD_VERSION if addon_id == "plugin.program.chef21" else version
        )
        out_path = out_dir / f"{addon_id}-{package_version}.zip"
        if skip_existing and out_path.exists() and out_path.stat().st_size > 1000:
            ok += 1
            print(f"[{index}/{len(catalog)}] skip {out_path.name}")
            continue

        url = f"https://raw.githubusercontent.com/nebulous42069/Omega/main/{github_path}"
        print(f"[{index}/{len(catalog)}] {addon_id}-{version}")
        try:
            raw = fetch_bytes(url)
            patched = patch_zip_contents(raw, addon_id, wizard_sources)
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
    wizard_sources = load_wizard_sources()
    ok, total, failed = mirror_packages(
        catalog,
        zip_index,
        wizard_sources,
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
