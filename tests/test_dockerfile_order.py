import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DockerfileOrderTests(unittest.TestCase):
    def test_repository_verification_runs_after_streaming_build_zips_exist(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        verify_index = dockerfile.index("python3 scripts/verify_repo.py")
        solotv_index = dockerfile.index("python3 scripts/build_solotv_build.py ${SOLOTV_TARGETS}")
        solokids_index = dockerfile.index(
            "python3 scripts/build_solotv_build.py --profile solokids-tv ${SOLOKIDS_TV_TARGETS}"
        )

        self.assertLess(solotv_index, verify_index)
        self.assertLess(solokids_index, verify_index)


if __name__ == "__main__":
    unittest.main()
