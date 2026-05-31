#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PUBLIC = ROOT / "public"
REPO = PUBLIC / "repo"
SOLOTV_REPO = PUBLIC / "solotv" / "repo"
SOLOTV_CONFIG = SRC / "solotv_build" / "build.json"
SECRET_MARKERS = ("auth_token=", "SOLOVISION_COOLIFY_API_TOKEN")
SOLOTV_SKIN_SHORTCUT_SKINS = (
    "skin.diggzflix2",
    "skin.auraflix",
    "skin.xenon",
    "skin.xenon2",
    "skin.arctic.horizon.2",
    "skin.eminence.2.mod",
)
SOLOTV_MAINMENU_LABELS = (
    "Movies",
    "TV Shows",
    "Live TV",
    "Sports",
    "Your Trakt",
    "Add-ons",
    "SoLoTV Setup",
    "Settings",
    "Exit",
)
EXPECTED_KIDS_TRAKT_LISTS = (
    ("tvgeniekodi", "trending-kids-movies", "movie"),
    ("kristaeglover", "kids", "mixed"),
    ("mrspacegoose", "kids-top-tv-shows", "show"),
)
KIDS_FRIENDLY_COLORS = ("FFFF7043", "FF00B8D4", "FF7E57C2", "FFFFCA28")


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


def verify_solotv_wizard_package() -> None:
    if not SOLOTV_CONFIG.exists() or not (SOLOTV_REPO / "addons.xml").exists():
        return

    config = json.loads(SOLOTV_CONFIG.read_text(encoding="utf-8"))
    wizard_sources = config.get("wizard_sources") or {}
    root = ET.parse(SOLOTV_REPO / "addons.xml").getroot()
    wizard = next(
        (
            addon
            for addon in root.findall("addon")
            if addon.attrib.get("id") == "plugin.program.chef21"
        ),
        None,
    )
    if wizard is None:
        fail("SoLoTV repo is missing plugin.program.chef21")

    addon_id = wizard.attrib["id"]
    version = wizard.attrib["version"]
    zip_path = SOLOTV_REPO / addon_id / f"{addon_id}-{version}.zip"
    if not zip_path.exists():
        fail(f"Missing SoLoTV wizard zip: {zip_path}")

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        uservar = archive.read(f"{addon_id}/uservar.py").decode(
            "utf-8", errors="replace"
        )
        addon_xml = archive.read(f"{addon_id}/addon.xml").decode(
            "utf-8", errors="replace"
        )
        downloader = archive.read(
            f"{addon_id}/resources/lib/modules/downloader.py"
        ).decode("utf-8", errors="replace")
        build_install = archive.read(
            f"{addon_id}/resources/lib/modules/build_install.py"
        ).decode("utf-8", errors="replace")
        for source_name, expected_url in wizard_sources.items():
            if expected_url and expected_url not in uservar:
                fail(
                    "SoLoTV wizard uservar.py does not point "
                    f"{source_name} at {expected_url}"
                )
        if "Buildtexts69/omegabuilds" in uservar:
            fail("SoLoTV wizard uservar.py still points at the upstream Diggz build list")
        if "plugin.program.solokodi.setup" not in uservar:
            fail("SoLoTV wizard uservar.py does not preserve SoLoKodi Setup during install")
        if "script.module.requests" in addon_xml:
            fail("SoLoTV wizard still declares an unnecessary requests dependency")
        try:
            internal_addon = ET.fromstring(addon_xml)
        except ET.ParseError as exc:
            fail(f"SoLoTV wizard addon.xml is not valid XML: {exc}")
        if internal_addon.attrib.get("version") != version:
            fail(
                "SoLoTV wizard zip addon.xml version "
                f"{internal_addon.attrib.get('version')} does not match catalog {version}"
            )
        if "import requests" in downloader:
            fail("SoLoTV wizard downloader still imports requests")
        if "response.raw.read" in downloader or "response.iter_content" in downloader:
            fail("SoLoTV wizard downloader still uses requests response streaming")
        if '"Accept-Encoding": "identity"' not in downloader:
            fail("SoLoTV wizard downloader does not request identity encoding")
        if "zipfile.is_zipfile" not in downloader:
            fail("SoLoTV wizard downloader does not validate the downloaded ZIP")
        if "from zipfile import ZipFile, is_zipfile" not in build_install:
            fail("SoLoTV wizard build installer does not import is_zipfile")
        if build_install.find("if not is_zipfile(zippath):") == -1:
            fail("SoLoTV wizard build installer does not validate before fresh_start")
        if (
            build_install.find("if not is_zipfile(zippath):")
            > build_install.find("fresh_start()")
        ):
            fail("SoLoTV wizard validates the ZIP after fresh_start instead of before")
        stale_pyc = [
            name
            for name in names
            if name.endswith(".pyc")
            and (
                "modules/downloader" in name
                or "modules/build_install" in name
                or "uservar" in name
            )
        ]
        if stale_pyc:
            fail(f"SoLoTV wizard contains stale patched-module bytecode: {stale_pyc[0]}")


def verify_setup_credential_steps() -> None:
    settings_path = SRC / "plugin.program.solokodi.setup" / "resources" / "settings.xml"
    wizard_path = SRC / "plugin.program.solokodi.setup" / "resources" / "lib" / "wizard.py"
    status_path = SRC / "plugin.program.solokodi.setup" / "resources" / "lib" / "status.py"
    setup_path = SRC / "plugin.program.solokodi.setup" / "resources" / "lib" / "setup.py"
    solotv_path = SRC / "builds" / "solotv.json"

    settings = settings_path.read_text(encoding="utf-8")
    for setting_id in ("trakt_api_token", "tmdb_api_key"):
        if f'id="{setting_id}"' not in settings:
            fail(f"Setup settings are missing {setting_id}")

    wizard = wizard_path.read_text(encoding="utf-8")
    status_code = status_path.read_text(encoding="utf-8")
    setup_code = setup_path.read_text(encoding="utf-8")
    for step_id in ("trakt", "tmdb"):
        if f'"{step_id}"' not in wizard:
            fail(f"Setup wizard does not handle {step_id} credentials")
        if f'"{step_id}"' not in status_code:
            fail(f"Setup status does not track {step_id} credentials")
    if "save_trakt_api_token" not in setup_code:
        fail("Setup module is missing save_trakt_api_token")
    if "save_tmdb_api_key" not in setup_code:
        fail("Setup module is missing save_tmdb_api_key")

    solotv = json.loads(solotv_path.read_text(encoding="utf-8"))
    step_ids = [step["id"] for step in solotv.get("wizard_steps", [])]
    for step_id in ("trakt", "tmdb"):
        if step_id not in step_ids:
            fail(f"SoLoTV setup steps are missing optional {step_id}")
    if step_ids.index("trakt") > step_ids.index("launch_wizard"):
        fail("SoLoTV Trakt step must run before launching the Build Wizard")
    if step_ids.index("tmdb") > step_ids.index("launch_wizard"):
        fail("SoLoTV TMDb step must run before launching the Build Wizard")


def verify_kids_trakt_lists_and_branding() -> None:
    kids_path = SRC / "builds" / "kids.json"
    kids = json.loads(kids_path.read_text(encoding="utf-8"))
    lists = kids.get("family_trakt_lists") or []
    seen = set()
    for entry in lists:
        key = (entry.get("user"), entry.get("slug"), entry.get("media_type"))
        if key in seen:
            fail(f"Kids Trakt list is duplicated: {entry.get('user')}/{entry.get('slug')}")
        seen.add(key)
    for expected in EXPECTED_KIDS_TRAKT_LISTS:
        if expected not in seen:
            fail(
                "Kids build is missing Trakt list "
                f"{expected[0]}/{expected[1]} ({expected[2]})"
            )

    step_ids = [step["id"] for step in kids.get("wizard_steps", [])]
    if "trakt" not in step_ids:
        fail("Kids setup wizard is missing the optional Trakt API token step")
    if "tmdb" in step_ids and step_ids.index("trakt") > step_ids.index("tmdb"):
        fail("Kids Trakt step should run before TMDb so KidsRD has list credentials")

    branding = kids.get("branding") or {}
    accent = branding.get("accent_color") or ""
    skin_colors = [value for setting, value in (kids.get("skin") or {}).get("colors", [])]
    if accent not in KIDS_FRIENDLY_COLORS:
        fail("Kids build branding accent is not in the approved kid-friendly palette")
    if not skin_colors or any(color not in KIDS_FRIENDLY_COLORS for color in skin_colors):
        fail("Kids skin colors are not in the approved kid-friendly palette")

    card = SRC / "plugin.program.solokodi.setup" / "resources" / "media" / "cards" / kids.get("card_image", "")
    if not card.exists() or card.stat().st_size < 100_000:
        fail("Kids build card artwork is missing or too small")


def verify_kidsrd_trakt_support() -> None:
    addon_dir = SRC / "plugin.video.solokodi.kidsrd"
    addon_xml = (addon_dir / "addon.xml").read_text(encoding="utf-8")
    settings = (addon_dir / "resources" / "settings.xml").read_text(encoding="utf-8")
    constants = (addon_dir / "resources" / "lib" / "constants.py").read_text(encoding="utf-8")
    router = (addon_dir / "resources" / "lib" / "router.py").read_text(encoding="utf-8")
    trakt_client = addon_dir / "resources" / "lib" / "trakt_client.py"

    if 'version="0.2.4"' not in addon_xml:
        fail("KidsRD add-on version must be bumped for Trakt list support")
    if 'id="trakt_api_token"' not in settings:
        fail("KidsRD settings are missing trakt_api_token")
    if not trakt_client.exists():
        fail("KidsRD is missing a Trakt API client")
    for user, slug, media_type in EXPECTED_KIDS_TRAKT_LISTS:
        if user not in constants or slug not in constants or media_type not in constants:
            fail(f"KidsRD constants are missing Trakt list {user}/{slug}")
    if "show_trakt_list" not in router or 'action == "trakt_list"' not in router:
        fail("KidsRD router does not expose Trakt family lists")


def _solotv_build_targets() -> list[Path]:
    if not SOLOTV_CONFIG.exists():
        return []
    config = json.loads(SOLOTV_CONFIG.read_text(encoding="utf-8"))
    version = config["version"]
    targets = []
    for source in config.get("sources", []):
        kodi = source.get("kodi")
        if kodi:
            targets.append(PUBLIC / "solotv" / "builds" / f"solotv-{version}-{kodi}.zip")
    return targets


def verify_solotv_skin_menus() -> None:
    for zip_path in _solotv_build_targets():
        if not zip_path.exists():
            fail(f"Missing generated SoLoTV build zip: {zip_path}")
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            for skin_id in SOLOTV_SKIN_SHORTCUT_SKINS:
                entry = (
                    "userdata/addon_data/script.skinshortcuts/"
                    f"{skin_id}-mainmenu.DATA.xml"
                )
                if entry not in names:
                    fail(f"{zip_path.name} is missing {skin_id} main menu shortcuts")
                labels = {
                    (node.text or "").strip()
                    for node in ET.fromstring(archive.read(entry)).findall("./shortcut/label")
                }
                missing = [label for label in SOLOTV_MAINMENU_LABELS if label not in labels]
                if missing:
                    fail(
                        f"{zip_path.name} {skin_id} main menu is missing "
                        f"{', '.join(missing)}"
                    )


def verify_solotv_build_versions() -> None:
    expected = {path.name for path in _solotv_build_targets()}
    build_dir = PUBLIC / "solotv" / "builds"
    if not expected or not build_dir.exists():
        return
    stale = sorted(
        path.name for path in build_dir.glob("solotv-*.zip") if path.name not in expected
    )
    if stale:
        fail(f"Stale SoLoTV build zip remains published: {stale[0]}")


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
    verify_solotv_wizard_package()
    verify_setup_credential_steps()
    verify_kids_trakt_lists_and_branding()
    verify_kidsrd_trakt_support()
    verify_solotv_skin_menus()
    verify_solotv_build_versions()
    verify_no_embedded_secrets()
    print("Repository verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
