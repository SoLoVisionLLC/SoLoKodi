import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETUP_ADDON = ROOT / "src" / "plugin.program.solokodi.setup"


class SetupTraktAuthTests(unittest.TestCase):
    def test_trakt_setup_uses_device_oauth_flow(self):
        setup_code = (SETUP_ADDON / "resources" / "lib" / "setup.py").read_text(encoding="utf-8")
        wizard_code = (SETUP_ADDON / "resources" / "lib" / "wizard.py").read_text(encoding="utf-8")

        self.assertIn("def connect_trakt", setup_code)
        self.assertIn("oauth/device/code", setup_code)
        self.assertIn("oauth/device/token", setup_code)
        self.assertIn("connect_trakt()", wizard_code)
        self.assertNotIn("Enter your Trakt API token", wizard_code)

    def test_trakt_settings_are_refreshable_oauth_credentials(self):
        settings = (SETUP_ADDON / "resources" / "settings.xml").read_text(encoding="utf-8")
        status_code = (SETUP_ADDON / "resources" / "lib" / "status.py").read_text(encoding="utf-8")

        for setting_id in (
            "trakt_access_token",
            "trakt_refresh_token",
            "trakt_expires_at",
            "trakt_username",
        ):
            self.assertIn(f'id="{setting_id}"', settings)

        self.assertIn('getSetting("trakt_access_token")', status_code)
        self.assertIn('"Trakt account"', status_code)

    def test_solotv_wizard_labels_describe_authorization(self):
        build = json.loads((ROOT / "src" / "builds" / "solotv.json").read_text(encoding="utf-8"))
        trakt_steps = [step for step in build["wizard_steps"] if step["id"] == "trakt"]

        self.assertEqual(1, len(trakt_steps))
        self.assertIn("Authorize Trakt", trakt_steps[0]["label"])
        self.assertNotIn("API token", trakt_steps[0]["label"])


if __name__ == "__main__":
    unittest.main()
