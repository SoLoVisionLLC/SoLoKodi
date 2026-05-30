#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PUBLIC = ROOT / "public"
REPO = PUBLIC / "repo"


def addon_metadata(addon_dir: Path) -> tuple[str, str]:
    tree = ET.parse(addon_dir / "addon.xml")
    root = tree.getroot()
    return root.attrib["id"], root.attrib["version"]


def zip_addon(addon_dir: Path) -> Path:
    addon_id, version = addon_metadata(addon_dir)
    out_dir = REPO / addon_id
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{addon_id}-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(addon_dir.rglob("*")):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.is_file():
                archive.write(path, path.relative_to(addon_dir.parent))
    return zip_path


def build_addons_xml(addon_dirs: list[Path]) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
    for addon_dir in sorted(addon_dirs):
        text = (addon_dir / "addon.xml").read_text(encoding="utf-8").strip()
        declaration_end = text.find("?>")
        if declaration_end != -1:
            text = text[declaration_end + 2 :].strip()
        parts.append(text)
    parts.append("</addons>")
    return "\n".join(parts) + "\n"


def main() -> int:
    REPO.mkdir(parents=True, exist_ok=True)
    addon_dirs = [path for path in SRC.iterdir() if (path / "addon.xml").exists()]
    if not addon_dirs:
        raise SystemExit("No add-ons found under src/")

    for addon_dir in addon_dirs:
        zip_addon(addon_dir)

    addons_xml = build_addons_xml(addon_dirs)
    (REPO / "addons.xml").write_text(addons_xml, encoding="utf-8")
    md5 = hashlib.md5(addons_xml.encode("utf-8")).hexdigest()
    (REPO / "addons.xml.md5").write_text(md5, encoding="utf-8")

    repo_dir = SRC / "repository.solokodi"
    repo_id, repo_version = addon_metadata(repo_dir)
    repo_zip = REPO / repo_id / f"{repo_id}-{repo_version}.zip"
    shutil.copy2(repo_zip, PUBLIC / repo_zip.name)
    print(f"Built {len(addon_dirs)} add-ons into {REPO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
