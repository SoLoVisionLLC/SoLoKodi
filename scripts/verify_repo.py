#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PUBLIC = ROOT / "public"
REPO = PUBLIC / "repo"
SECRET_MARKERS = ("auth_token=", "SOLOVISION_COOLIFY_API_TOKEN")


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def verify_xml() -> ET.Element:
    path = REPO / "addons.xml"
    if not path.exists():
        fail("repo/addons.xml is missing")
    root = ET.parse(path).getroot()
    if root.tag != "addons":
        fail("repo/addons.xml root must be <addons>")
    addon_ids = [addon.attrib.get("id") for addon in root.findall("addon")]
    for expected in ("repository.solokodi", "plugin.program.solokodi.setup", "plugin.video.solokodi.kidsrd"):
        if expected not in addon_ids:
            fail(f"{expected} missing from addons.xml")
    expected_md5 = hashlib.md5(path.read_bytes()).hexdigest()
    actual_md5 = (REPO / "addons.xml.md5").read_text(encoding="utf-8").strip()
    if expected_md5 != actual_md5:
        fail("addons.xml.md5 does not match addons.xml")
    return root


def verify_zips(root: ET.Element) -> None:
    for addon in root.findall("addon"):
        addon_id = addon.attrib["id"]
        version = addon.attrib["version"]
        zip_path = REPO / addon_id / f"{addon_id}-{version}.zip"
        if not zip_path.exists():
            fail(f"Missing zip for {addon_id}")
        with zipfile.ZipFile(zip_path) as archive:
            expected = f"{addon_id}/addon.xml"
            if expected not in archive.namelist():
                fail(f"{zip_path} does not contain {expected}")
            if addon_id == "plugin.program.solokodi.setup":
                for profile in ("kids", "solotv"):
                    manifest_entry = f"{addon_id}/resources/builds/{profile}.json"
                    if manifest_entry not in archive.namelist():
                        fail(f"{zip_path} does not contain embedded build manifest {manifest_entry}")
    repo_addon = next(addon for addon in root.findall("addon") if addon.attrib["id"] == "repository.solokodi")
    repo_version = repo_addon.attrib["version"]
    public_repo_zip = ROOT / "public" / "solokodi" / f"repository.solokodi-{repo_version}.zip"
    if not public_repo_zip.exists():
        fail(f"public SoLoKodi repository ZIP is missing: {public_repo_zip.name}")
    legacy_root_zip = ROOT / "public" / f"repository.solokodi-{repo_version}.zip"
    if legacy_root_zip.exists():
        fail("legacy root-level repository ZIP should redirect, not exist as a file")

    for profile in ("kids", "solotv"):
        manifest_path = PUBLIC / "builds" / profile / "manifest.json"
        if not manifest_path.exists():
            fail(f"public/builds/{profile}/manifest.json is missing — run build_repo.py")
        embedded_manifest = SRC / "plugin.program.solokodi.setup" / "resources" / "builds" / f"{profile}.json"
        if not embedded_manifest.exists():
            fail(f"embedded build manifest {profile}.json is missing from setup add-on")


def verify_no_embedded_secrets() -> None:
    for path in ROOT.rglob("*"):
        if path.is_dir() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix in {".zip", ".png", ".jpg", ".jpeg", ".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path == Path(__file__).resolve():
            continue
        for marker in SECRET_MARKERS:
            if marker in text:
                fail(f"Potential embedded secret marker {marker!r} in {path}")


def main() -> int:
    root = verify_xml()
    verify_zips(root)
    verify_no_embedded_secrets()
    print("Repository verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
