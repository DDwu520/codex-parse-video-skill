from __future__ import annotations

import json
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "tools" / "build_macos_package.py"


def write_macho(path: Path, cpu_type: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<IIIIIIII", 0xFEEDFACF, cpu_type, 0, 2, 0, 0, 0, 0))
    path.chmod(0o755)


@unittest.skipUnless(sys.platform == "darwin", "macOS 包装测试仅在 macOS 运行。")
class BuildMacOSPackageCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_context = tempfile.TemporaryDirectory(prefix="parse-video-macos-package-")
        self.root = Path(self.temp_context.name)
        self.output = self.root / "dist"

    def tearDown(self) -> None:
        self.temp_context.cleanup()

    def build(self, target: str, cpu_type: int) -> Path:
        binary = self.root / target / "parse-video"
        helper = self.root / target / "helper" / "parse-video-helper"
        write_macho(binary, cpu_type)
        write_macho(helper, cpu_type)
        (helper.parent / "_internal").mkdir()
        (helper.parent / "_internal" / "python-runtime.txt").write_text(
            "runtime", encoding="utf-8"
        )
        python_license = self.root / "licenses" / "PYTHON-LICENSE.txt"
        pyinstaller_license = self.root / "licenses" / "PYINSTALLER-COPYING.txt"
        python_license.parent.mkdir(parents=True, exist_ok=True)
        python_license.write_text("Python license", encoding="utf-8")
        pyinstaller_license.write_text("PyInstaller license", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--target",
                target,
                "--binary",
                str(binary),
                "--helper-bundle",
                str(helper.parent),
                "--python-license",
                str(python_license),
                "--pyinstaller-license",
                str(pyinstaller_license),
                "--output-dir",
                str(self.output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return Path(completed.stdout.strip())

    def test_builds_self_contained_arm64_candidate_with_verified_manifest(self) -> None:
        archive = self.build("macos-arm64", 0x0100000C)
        self.assertEqual(
            archive.name,
            "parse-video-v1.0.0-rc.3-macos-arm64.zip",
        )

        with zipfile.ZipFile(archive) as bundle:
            root = "parse-video-v1.0.0-rc.3-macos-arm64"
            names = set(bundle.namelist())
            self.assertIn(f"{root}/install.command", names)
            self.assertIn(f"{root}/verify.command", names)
            self.assertIn(f"{root}/skill/parse-video/run.sh", names)
            self.assertIn(f"{root}/licenses/CPYTHON-LICENSE.txt", names)
            self.assertIn(f"{root}/licenses/PYINSTALLER-COPYING.txt", names)
            self.assertIn(
                f"{root}/skill/parse-video/runtime/macos-arm64/parse-video",
                names,
            )
            self.assertIn(
                f"{root}/skill/parse-video/runtime/macos-arm64/helper/parse-video-helper",
                names,
            )
            self.assertNotIn(f"{root}/skill/parse-video/tests/", names)
            mode = bundle.getinfo(f"{root}/install.command").external_attr >> 16
            self.assertTrue(mode & stat.S_IXUSR)
            manifest = json.loads(bundle.read(f"{root}/manifest.json"))
            self.assertEqual(manifest["target"], "macos-arm64")
            self.assertEqual(manifest["status"], "candidate")
            self.assertEqual(manifest["python_helper"]["builder"], "PyInstaller")
            self.assertGreater(len(manifest["files"]), 10)

    def test_rejects_binary_for_the_wrong_architecture(self) -> None:
        binary = self.root / "parse-video"
        helper = self.root / "helper" / "parse-video-helper"
        write_macho(binary, 0x01000007)
        write_macho(helper, 0x01000007)
        python_license = self.root / "PYTHON-LICENSE.txt"
        pyinstaller_license = self.root / "PYINSTALLER-COPYING.txt"
        python_license.write_text("Python license", encoding="utf-8")
        pyinstaller_license.write_text("PyInstaller license", encoding="utf-8")

        completed = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--target",
                "macos-arm64",
                "--binary",
                str(binary),
                "--helper-bundle",
                str(helper.parent),
                "--python-license",
                str(python_license),
                "--pyinstaller-license",
                str(pyinstaller_license),
                "--output-dir",
                str(self.output),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("架构不匹配", completed.stderr)


if __name__ == "__main__":
    unittest.main()
