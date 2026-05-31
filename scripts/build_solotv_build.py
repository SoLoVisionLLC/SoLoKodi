#!/usr/bin/env python3
"""
Build the SoLoTV Kodi build from the Diggz foundation, rebranded as SoLoVision.

Pipeline:
  1. Download the upstream foundation build zip(s) (cached in work/).
  2. Rebrand text files (Diggz -> SoLoTV / SoLoVision) and apply file overrides
     from src/solotv_build/overrides/ (for images and other binary assets).
  3. Repackage into public/solotv/builds/solotv-<version>-<kodi>.zip.
  4. Publish our own build list (builds.xml) plus the wizard's notify/videos/
     changelog text files so the SoLoTV Build Wizard points only at us.

Large zips are generated at (docker) build time and are not committed to git.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

WIZARD_USERVAR = "addons/plugin.program.chef21/uservar.py"

# Reuse the branding rules already used to rebrand the SoLoTV catalog.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mirror_solotv_repo import TEXT_REPLACEMENTS, PATCH_INSIDE_ZIP_SUFFIXES  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "solotv_build" / "build.json"
OVERRIDES_DIR = ROOT / "src" / "solotv_build" / "overrides"
CARD_SOURCE = (
    ROOT
    / "src"
    / "plugin.program.solokodi.setup"
    / "resources"
    / "media"
    / "cards"
    / "solotv.png"
)
WORK = ROOT / "work" / "solotv_build"
PUBLIC_SOLOTV = ROOT / "public" / "solotv"
PUBLIC_BUILDS = PUBLIC_SOLOTV / "builds"
PUBLIC_CARDS = PUBLIC_SOLOTV / "cards"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _source_urls(source: dict) -> list[str]:
    if source.get("urls"):
        return list(source["urls"])
    if source.get("url"):
        return [source["url"]]
    return []


def _download_one(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    with urlopen(url, timeout=600) as response, open(dest, "wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)
            read += len(chunk)
            if total:
                pct = int(read / total * 100)
                print(f"\r  {pct:3d}%  {read // (1024 * 1024)}/{total // (1024 * 1024)} MB", end="")
    print(f"\r  downloaded {dest.name} ({dest.stat().st_size // (1024 * 1024)} MB)")


def download(urls: list[str], dest: Path, force: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        print(f"  cached {dest.name} ({dest.stat().st_size // (1024 * 1024)} MB)")
        return
    last_error: Exception | None = None
    for url in urls:
        try:
            _download_one(url, dest)
            return
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            last_error = exc
            print(f"\n  failed: {exc}")
            if dest.exists():
                dest.unlink()
    raise SystemExit(f"All download mirrors failed for {dest.name}: {last_error}")


def rebrand_bytes(name: str, data: bytes) -> bytes:
    if Path(name).suffix.lower() not in PATCH_INSIDE_ZIP_SUFFIXES:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    for pattern, replacement in TEXT_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text.encode("utf-8")


def repoint_uservar(data: bytes, wizard_sources: dict) -> bytes:
    """Rewrite the bundled wizard's uservar.py to read from SoLoVision URLs."""
    if not wizard_sources:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    for var_name, url in wizard_sources.items():
        if not url:
            continue
        pattern = r"(?m)^(\s*{0}\s*=\s*).*$".format(re.escape(var_name))
        text = re.sub(pattern, r"\g<1>'{0}'".format(url), text, count=1)
    return text.encode("utf-8")


def _skip_member(name: str) -> bool:
    """Drop stale compiled caches of the wizard's uservar so our edit wins."""
    lower = name.lower()
    return "plugin.program.chef21" in lower and "uservar" in lower and lower.endswith(".pyc")


def load_overrides() -> dict[str, bytes]:
    overrides: dict[str, bytes] = {}
    if not OVERRIDES_DIR.exists():
        return overrides
    for path in OVERRIDES_DIR.rglob("*"):
        if path.is_file() and path.name != "README.md":
            rel = path.relative_to(OVERRIDES_DIR).as_posix()
            overrides[rel] = path.read_bytes()
    return overrides


def inspect_build(src_zip: Path) -> None:
    """Print branded paths and the largest images to seed overrides."""
    keywords = ("diggz", "xenon", "chef")
    branded = []
    images = []
    with zipfile.ZipFile(src_zip) as archive:
        for item in archive.infolist():
            lower = item.filename.lower()
            if any(word in lower for word in keywords):
                branded.append(item.filename)
            if lower.endswith((".png", ".jpg", ".jpeg", ".gif")):
                images.append((item.file_size, item.filename))
    print(f"\n=== Branded paths (diggz/xenon/chef) in {src_zip.name}: {len(branded)} ===")
    for name in sorted(branded)[:80]:
        print(f"  {name}")
    print(f"\n=== Largest images in {src_zip.name} ===")
    for size, name in sorted(images, reverse=True)[:40]:
        print(f"  {size // 1024:6d} KB  {name}")


def process_source(
    source: dict,
    version: str,
    overrides: dict[str, bytes],
    wizard_sources: dict,
    force: bool,
) -> str:
    kodi = source["kodi"]
    src_zip = WORK / f"foundation-{kodi}.zip"
    download(_source_urls(source), src_zip, force=force)

    out_name = f"solotv-{version}-{kodi}.zip"
    out_path = PUBLIC_BUILDS / out_name
    PUBLIC_BUILDS.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    print(f"  rebranding -> {out_name}")
    applied = 0
    with zipfile.ZipFile(src_zip) as zin, zipfile.ZipFile(
        out_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            rel = item.filename
            if _skip_member(rel):
                continue
            data = zin.read(rel)
            if rel in overrides:
                data = overrides[rel]
                applied += 1
            elif rel == WIZARD_USERVAR:
                data = repoint_uservar(rebrand_bytes(rel, data), wizard_sources)
            else:
                data = rebrand_bytes(rel, data)
            zout.writestr(item, data)
    print(f"  wrote {out_name} ({out_path.stat().st_size // (1024 * 1024)} MB, {applied} overrides applied)")
    return out_name


def write_build_list(config: dict, produced: list[tuple[str, str]]) -> None:
    base = config["base_url"].rstrip("/")
    parts = ["<builds>", ""]
    for kodi, out_name in produced:
        parts += [
            "<build>",
            f"<name>{config['name']}</name>",
            f"<version>{config['version']}</version>",
            f"<kodi>{kodi}</kodi>",
            f"<url>{base}/{out_name}</url>",
            f"<icon>{config['icon']}</icon>",
            f"<fanart>{config['fanart']}</fanart>",
            f"<description>{config['description']}</description>",
            "</build>",
            "",
        ]
    parts.append("</builds>")
    PUBLIC_SOLOTV.mkdir(parents=True, exist_ok=True)
    (PUBLIC_SOLOTV / "builds.xml").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"  wrote builds.xml ({len(produced)} build(s))")


def write_wizard_text_files(config: dict) -> None:
    PUBLIC_SOLOTV.mkdir(parents=True, exist_ok=True)
    # Notification shown in the wizard (blank = no nag). Format: [COLOR ...]msg[/COLOR]
    (PUBLIC_SOLOTV / "notify.txt").write_text("", encoding="utf-8")
    # Optional promo videos list (none).
    (PUBLIC_SOLOTV / "videos.txt").write_text("", encoding="utf-8")
    # Changelog the wizard can display.
    changelog = (
        f"{config['name']} v{config['version']}\n"
        "- SoLoVision-branded build, maintained in the SoLoKodi repo.\n"
    )
    (PUBLIC_SOLOTV / "changelog.txt").write_text(changelog, encoding="utf-8")
    print("  wrote notify.txt, videos.txt, changelog.txt")


def publish_card_icon() -> None:
    if CARD_SOURCE.exists():
        PUBLIC_CARDS.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CARD_SOURCE, PUBLIC_CARDS / "solotv.png")
        print("  published cards/solotv.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the rebranded SoLoTV build.")
    parser.add_argument("kodi", nargs="?", help="Only build this Kodi target (e.g. K21).")
    parser.add_argument("--force", action="store_true", help="Re-download foundation zips.")
    parser.add_argument("--inspect", action="store_true", help="List branded paths/images and exit.")
    parser.add_argument(
        "--xml-only",
        action="store_true",
        help="Only (re)write builds.xml + wizard text files (no download/repackage).",
    )
    args = parser.parse_args()

    config = load_config()
    sources = config["sources"]
    if args.kodi:
        sources = [s for s in sources if s["kodi"].lower() == args.kodi.lower()]
        if not sources:
            print(f"No source for Kodi target {args.kodi!r}")
            return 1

    if args.inspect:
        for source in sources:
            src_zip = WORK / f"foundation-{source['kodi']}.zip"
            download(_source_urls(source), src_zip, force=args.force)
            inspect_build(src_zip)
        return 0

    if args.xml_only:
        produced = [
            (s["kodi"], f"solotv-{config['version']}-{s['kodi']}.zip") for s in sources
        ]
        write_build_list(config, produced)
        write_wizard_text_files(config)
        publish_card_icon()
        return 0

    overrides = load_overrides()
    print(f"Loaded {len(overrides)} override file(s) from {OVERRIDES_DIR}")
    wizard_sources = config.get("wizard_sources") or {}

    produced: list[tuple[str, str]] = []
    for source in sources:
        print(f"\n[{source['kodi']}] building from foundation...")
        out_name = process_source(
            source, config["version"], overrides, wizard_sources, args.force
        )
        produced.append((source["kodi"], out_name))

    write_build_list(config, produced)
    write_wizard_text_files(config)
    publish_card_icon()
    print(f"\nDone. Published {len(produced)} SoLoTV build(s) to {PUBLIC_BUILDS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
