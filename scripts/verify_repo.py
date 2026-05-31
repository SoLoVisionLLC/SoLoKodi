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
SOLOKIDS_TV_CONFIG = SRC / "solokids_tv_build" / "build.json"
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
SOLOKIDS_TV_MAINMENU_LABELS = (
    "Kids Movies",
    "Kids TV",
    "Live Kids TV",
    "Search",
    "Add-ons",
    "SoLoKids TV Setup",
    "Settings",
    "Exit",
)
KIDS_FRIENDLY_COLORS = ("FFFF7043", "FF00B8D4", "FF7E57C2", "FFFFCA28")
STREAMING_BUILDS = (
    {
        "profile": "solotv",
        "config": SOLOTV_CONFIG,
        "public_dir": PUBLIC / "solotv",
        "zip_prefix": "solotv",
        "labels": SOLOTV_MAINMENU_LABELS,
        "allow_trakt_menu": True,
    },
    {
        "profile": "solokids-tv",
        "config": SOLOKIDS_TV_CONFIG,
        "public_dir": PUBLIC / "solokids-tv",
        "zip_prefix": "solokids-tv",
        "labels": SOLOKIDS_TV_MAINMENU_LABELS,
        "allow_trakt_menu": False,
    },
)


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
                for profile in ("kids", "solotv", "solokids-tv"):
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

    for profile in ("kids", "solotv", "solokids-tv"):
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
    solokids_path = SRC / "builds" / "solokids-tv.json"

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

    solokids = json.loads(solokids_path.read_text(encoding="utf-8"))
    solokids_step_ids = [step["id"] for step in solokids.get("wizard_steps", [])]
    if "realdebrid" not in solokids_step_ids:
        fail("SoLoKids TV setup steps are missing required Real-Debrid setup")
    if "trakt" in solokids_step_ids:
        fail("SoLoKids TV must not add a Trakt setup step")
    if solokids_step_ids.index("realdebrid") > solokids_step_ids.index("launch_wizard"):
        fail("SoLoKids TV Real-Debrid setup must run before launching the Build Wizard")


def verify_kids_branding_without_trakt_lists() -> None:
    kids_path = SRC / "builds" / "kids.json"
    kids = json.loads(kids_path.read_text(encoding="utf-8"))
    if "family_trakt_lists" in kids:
        fail("Kids build must not define family Trakt playlist menus")

    step_ids = [step["id"] for step in kids.get("wizard_steps", [])]
    if "trakt" in step_ids:
        fail("Kids setup wizard must not add a Trakt playlist step")

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


def verify_solokids_tv_profile_and_art() -> None:
    build_path = SRC / "builds" / "solokids-tv.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    if build.get("build_type") != "streaming":
        fail("SoLoKids TV must be a streaming build profile")
    if not build.get("requires_debrid"):
        fail("SoLoKids TV must require Real-Debrid")
    if "family_trakt_lists" in build:
        fail("SoLoKids TV must not define family Trakt playlist menus")

    config = build.get("streaming_repo") or {}
    for key in ("build_list_url", "notify_url", "videos_url", "changelog_dir"):
        if "/solokids-tv/" not in config.get(key, ""):
            fail(f"SoLoKids TV streaming config {key} must point at /solokids-tv/")

    card = SRC / "plugin.program.solokodi.setup" / "resources" / "media" / "cards" / build.get("card_image", "")
    if not card.exists() or card.stat().st_size < 100_000:
        fail("SoLoKids TV card artwork is missing or too small")

    public_card = PUBLIC / "solokids-tv" / "cards" / build.get("card_image", "")
    if not public_card.exists() or public_card.stat().st_size < 100_000:
        fail("Published SoLoKids TV card artwork is missing or too small")

    overrides_dir = SRC / "solokids_tv_build" / "overrides"
    expected_overrides = (
        "addons/plugin.program.chef21/resources/icon.png",
        "addons/plugin.program.chef21/resources/skins/Default/media/background.png",
        "addons/resource.images.skinbackgrounds.xenon/resources/Diggz/diggz.png",
    )
    for rel in expected_overrides:
        path = overrides_dir / rel
        if not path.exists() or path.stat().st_size < 20_000:
            fail(f"SoLoKids TV image override is missing or too small: {rel}")


def verify_no_family_trakt_playlist_menus() -> None:
    addon_dir = SRC / "plugin.video.solokodi.kidsrd"
    files = (
        addon_dir / "resources" / "settings.xml",
        addon_dir / "resources" / "lib" / "constants.py",
        addon_dir / "resources" / "lib" / "router.py",
        SRC / "plugin.program.solokodi.setup" / "resources" / "lib" / "menu_layout.py",
        SRC / "plugin.program.solokodi.setup" / "resources" / "lib" / "nimbus_layout.py",
        ROOT / "scripts" / "write_kids_menu.py",
    )
    forbidden = (
        "Family Trakt",
        "family_trakt_lists",
        "trakt_lists",
        "trakt_list",
        "FAMILY_TRAKT_LISTS",
        "trakt_api_token",
    )
    for path in files:
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                fail(f"Family Trakt playlist marker {marker!r} remains in {path}")
    if (addon_dir / "resources" / "lib" / "trakt_client.py").exists():
        fail("KidsRD must not ship a Trakt client for family playlist menus")


def _streaming_build_targets(streaming: dict) -> list[Path]:
    config_path = streaming["config"]
    if not config_path.exists():
        return []
    config = json.loads(config_path.read_text(encoding="utf-8"))
    version = config["version"]
    targets = []
    for source in config.get("sources", []):
        kodi = source.get("kodi")
        if kodi:
            targets.append(
                streaming["public_dir"]
                / "builds"
                / f"{streaming['zip_prefix']}-{version}-{kodi}.zip"
            )
    return targets


def verify_streaming_skin_menus() -> None:
    for streaming in STREAMING_BUILDS:
        for zip_path in _streaming_build_targets(streaming):
            if not zip_path.exists():
                fail(f"Missing generated {streaming['profile']} build zip: {zip_path}")
            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())
                for skin_id in SOLOTV_SKIN_SHORTCUT_SKINS:
                    entry = (
                        "userdata/addon_data/script.skinshortcuts/"
                        f"{skin_id}-mainmenu.DATA.xml"
                    )
                    if entry not in names:
                        fail(f"{zip_path.name} is missing {skin_id} main menu shortcuts")
                    content = archive.read(entry)
                    labels = {
                        (node.text or "").strip()
                        for node in ET.fromstring(content).findall("./shortcut/label")
                    }
                    missing = [label for label in streaming["labels"] if label not in labels]
                    if missing:
                        fail(
                            f"{zip_path.name} {skin_id} main menu is missing "
                            f"{', '.join(missing)}"
                        )
                    if not streaming["allow_trakt_menu"]:
                        lowered = content.decode("utf-8", errors="replace").lower()
                        if "trakt" in lowered:
                            fail(f"{zip_path.name} {skin_id} contains a Trakt menu action")


def verify_streaming_build_versions() -> None:
    for streaming in STREAMING_BUILDS:
        expected = {path.name for path in _streaming_build_targets(streaming)}
        build_dir = streaming["public_dir"] / "builds"
        if not expected or not build_dir.exists():
            continue
        stale = sorted(
            path.name
            for path in build_dir.glob(f"{streaming['zip_prefix']}-*.zip")
            if path.name not in expected
        )
        if stale:
            fail(f"Stale {streaming['profile']} build zip remains published: {stale[0]}")


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
    verify_kids_branding_without_trakt_lists()
    verify_solokids_tv_profile_and_art()
    verify_no_family_trakt_playlist_menus()
    verify_streaming_skin_menus()
    verify_streaming_build_versions()
    verify_no_embedded_secrets()
    print("Repository verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
