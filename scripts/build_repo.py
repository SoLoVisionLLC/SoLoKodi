#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PUBLIC = ROOT / "public"
REPO = PUBLIC / "repo"
BUILDS_SRC = SRC / "builds"
BUILDS_PUBLIC = PUBLIC / "builds"
SETUP_RESOURCES = SRC / "plugin.program.solokodi.setup" / "resources" / "builds"


def addon_metadata(addon_dir: Path) -> tuple[str, str, str]:
    tree = ET.parse(addon_dir / "addon.xml")
    root = tree.getroot()
    name = root.attrib.get("name", root.attrib["id"])
    return root.attrib["id"], root.attrib["version"], name


def zip_addon(addon_dir: Path) -> Path:
    addon_id, version, _name = addon_metadata(addon_dir)
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


def solokodi_addon_versions(addon_dirs: list[Path]) -> dict[str, dict[str, str]]:
    versions: dict[str, dict[str, str]] = {}
    for addon_dir in addon_dirs:
        addon_id, version, name = addon_metadata(addon_dir)
        if addon_id == "repository.solokodi":
            continue
        versions[addon_id] = {"version": version, "name": name}
    return versions


def generate_build_manifest(build_path: Path, addon_dirs: list[Path]) -> dict:
    build = json.loads(build_path.read_text(encoding="utf-8"))
    repo_dir = SRC / build["repository_id"]
    repo_id, repo_version, repo_name = addon_metadata(repo_dir)
    solokodi_versions = solokodi_addon_versions(addon_dirs)

    manifest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build": {
            "id": build["id"],
            "name": build["name"],
            "version": build["version"],
            "description": build["description"],
        },
        "repository": {
            "id": repo_id,
            "version": repo_version,
            "name": repo_name,
            "url": build["repo_url"],
        },
        "manifest_url": build["manifest_url"],
        "website": build["website"],
        "skin": build["skin"],
        "content_addons": build["content_addons"],
        "solokodi_addons": [],
        "wizard_steps": build["wizard_steps"],
    }

    for addon in build["solokodi_addons"]:
        meta = solokodi_versions.get(addon["id"], {})
        manifest["solokodi_addons"].append(
            {
                **addon,
                "version": meta.get("version", "0.0.0"),
            }
        )

    setup_meta = solokodi_versions.get("plugin.program.solokodi.setup", {})
    manifest["setup_addon"] = {
        "id": "plugin.program.solokodi.setup",
        "version": setup_meta.get("version", "0.0.0"),
        "name": setup_meta.get("name", "SoLoKodi Kids Setup"),
    }

    return manifest


def write_build_manifests(build_path: Path, manifest: dict) -> None:
    profile_id = manifest["build"]["id"]
    public_path = BUILDS_PUBLIC / profile_id / "manifest.json"
    embedded_path = SETUP_RESOURCES / f"{profile_id}.json"

    public_path.parent.mkdir(parents=True, exist_ok=True)
    embedded_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    public_path.write_text(payload, encoding="utf-8")
    embedded_path.write_text(payload, encoding="utf-8")


def main() -> int:
    REPO.mkdir(parents=True, exist_ok=True)
    addon_dirs = [path for path in SRC.iterdir() if (path / "addon.xml").exists()]
    if not addon_dirs:
        raise SystemExit("No add-ons found under src/")

    for addon_dir in addon_dirs:
        zip_addon(addon_dir)

    addons_xml = build_addons_xml(addon_dirs)
    addons_xml_path = REPO / "addons.xml"
    addons_xml_path.write_text(addons_xml, encoding="utf-8", newline="\n")
    md5 = hashlib.md5(addons_xml_path.read_bytes()).hexdigest()
    (REPO / "addons.xml.md5").write_text(md5, encoding="utf-8")

    for build_path in sorted(BUILDS_SRC.glob("*.json")):
        manifest = generate_build_manifest(build_path, addon_dirs)
        write_build_manifests(build_path, manifest)
        print(
            "Built manifest for {0} v{1}".format(
                manifest["build"]["name"], manifest["build"]["version"]
            )
        )

    repo_dir = SRC / "repository.solokodi"
    repo_id, repo_version, _repo_name = addon_metadata(repo_dir)
    repo_zip = REPO / repo_id / f"{repo_id}-{repo_version}.zip"
    public_repo_dir = PUBLIC / "solokodi"
    public_repo_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_zip, public_repo_dir / repo_zip.name)
    legacy_root_zip = PUBLIC / repo_zip.name
    if legacy_root_zip.exists():
        legacy_root_zip.unlink()
    print(f"Built {len(addon_dirs)} add-ons into {REPO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
