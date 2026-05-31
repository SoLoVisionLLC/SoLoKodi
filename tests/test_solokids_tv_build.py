import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_build_script():
    script_path = ROOT / "scripts" / "build_solotv_build.py"
    spec = importlib.util.spec_from_file_location("build_solotv_build", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SoLoKidsTvBuildTests(unittest.TestCase):
    def test_solokids_tv_profile_is_streaming_clone_without_trakt_lists(self):
        build_path = ROOT / "src" / "builds" / "solokids-tv.json"
        self.assertTrue(build_path.exists(), "SoLoKids TV build profile is missing")

        build = json.loads(build_path.read_text(encoding="utf-8"))
        self.assertEqual(build["id"], "solokids-tv")
        self.assertEqual(build["name"], "SoLoKids TV")
        self.assertEqual(build["build_type"], "streaming")
        self.assertTrue(build["requires_debrid"])
        self.assertNotIn("family_trakt_lists", build)

        step_ids = [step["id"] for step in build["wizard_steps"]]
        self.assertIn("realdebrid", step_ids)
        self.assertNotIn("trakt", step_ids)
        self.assertLess(step_ids.index("realdebrid"), step_ids.index("launch_wizard"))

        streaming_repo = build["streaming_repo"]
        self.assertIn("/solokids-tv/", streaming_repo["build_list_url"])
        self.assertIn("SoLoKids TV", streaming_repo["wizard_label"])
        self.assertIn("SoLoKids TV", streaming_repo["recommended_build_hint"])

    def test_build_script_has_solokids_tv_context_with_no_trakt_menu_actions(self):
        build_script = load_build_script()
        context = build_script.load_build_context("solokids-tv")

        self.assertEqual(context.config["id"], "solokids-tv")
        self.assertEqual(context.output_prefix, "solokids-tv")
        self.assertEqual(context.public_dir, ROOT / "public" / "solokids-tv")

        labels = [section["label"] for section in context.menu_sections]
        self.assertIn("Kids Movies", labels)
        self.assertIn("Kids TV", labels)
        self.assertIn("SoLoKids TV Setup", labels)
        self.assertNotIn("Your Trakt", labels)

        all_actions = [section["action"] for section in context.menu_sections]
        for entries in context.submenus.values():
            all_actions.extend(action for _label, action in entries)

        joined_actions = "\n".join(all_actions).lower()
        self.assertNotIn("trakt", joined_actions)


if __name__ == "__main__":
    unittest.main()
