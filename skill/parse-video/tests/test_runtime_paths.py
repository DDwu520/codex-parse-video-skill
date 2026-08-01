from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class RuntimePathTests(unittest.TestCase):
    def test_windows_child_environment_keeps_runtime_keys_and_drops_secrets(self) -> None:
        import runtime_paths

        environment = runtime_paths.safe_child_environment(
            Path("C:/Temp/isolated home"),
            Path("C:/Temp/job"),
            platform_name="windows",
            environ={
                "SystemRoot": "C:/Windows",
                "COMSPEC": "C:/Windows/System32/cmd.exe",
                "PATH": "C:/Windows/System32",
                "PATHEXT": ".EXE;.CMD",
                "hTtP_pRoXy": "http://secret.invalid",
                "PARSE_VIDEO_PASSWORD": "secret",
            },
        )

        self.assertEqual(environment["SystemRoot"], "C:/Windows")
        self.assertEqual(environment["TEMP"], "C:/Temp/job")
        self.assertEqual(environment["USERPROFILE"], "C:/Temp/isolated home")
        self.assertFalse(any("proxy" in key.casefold() for key in environment))
        self.assertNotIn("PARSE_VIDEO_PASSWORD", environment)

    def test_windows_uses_known_folders_and_custom_codex_home(self) -> None:
        import runtime_paths

        paths = runtime_paths.resolve_runtime_paths(
            platform_name="windows",
            architecture="amd64",
            home=Path("C:/Users/张 三"),
            environ={"CODEX_HOME": "D:/Codex Home"},
            temp_dir=Path("C:/Users/张 三/AppData/Local/Temp"),
            known_folders={
                "desktop": Path("D:/OneDrive/桌面"),
                "documents": Path("D:/OneDrive/文档"),
            },
            skill_dir=SKILL_DIR,
        )

        self.assertEqual(paths.codex_home, Path("D:/Codex Home"))
        self.assertEqual(paths.download_root, Path("D:/OneDrive/桌面/下载视频"))
        self.assertEqual(
            paths.evidence_root,
            Path("D:/OneDrive/文档/Parse Video/证据包"),
        )
        self.assertEqual(
            paths.parser_binary,
            SKILL_DIR / "runtime" / "windows-x64" / "parse-video.exe",
        )
        self.assertEqual(
            paths.temp_root,
            Path("C:/Users/张 三/AppData/Local/Temp/codex-parse-video"),
        )

    def test_macos_defaults_are_user_relative_not_hardcoded(self) -> None:
        import runtime_paths

        home = Path("/Users/another-user")
        paths = runtime_paths.resolve_runtime_paths(
            platform_name="macos",
            architecture="arm64",
            home=home,
            environ={},
            temp_dir=Path("/private/tmp"),
            skill_dir=SKILL_DIR,
        )

        self.assertEqual(paths.codex_home, home / ".codex")
        self.assertEqual(paths.download_root, home / "Desktop" / "下载视频")
        self.assertEqual(
            paths.evidence_root,
            home / "Documents" / "Parse Video" / "证据包",
        )
        self.assertEqual(
            paths.parser_binary,
            SKILL_DIR / "runtime" / "macos-arm64" / "parse-video",
        )
        for value in (
            paths.codex_home,
            paths.desktop,
            paths.documents,
            paths.download_root,
            paths.evidence_root,
            paths.isolated_home,
        ):
            self.assertNotIn("/Users/dd", str(value))

    def test_unsupported_platform_or_architecture_is_rejected(self) -> None:
        import runtime_paths

        with self.assertRaisesRegex(RuntimeError, "不支持的系统"):
            runtime_paths.resolve_runtime_paths(
                platform_name="linux",
                architecture="x64",
                home=Path("/home/user"),
                environ={},
                temp_dir=Path(tempfile.gettempdir()),
                skill_dir=SKILL_DIR,
            )

        with self.assertRaisesRegex(RuntimeError, "不支持的架构"):
            runtime_paths.resolve_runtime_paths(
                platform_name="windows",
                architecture="arm64",
                home=Path("C:/Users/user"),
                environ={},
                temp_dir=Path("C:/Temp"),
                known_folders={
                    "desktop": Path("C:/Users/user/Desktop"),
                    "documents": Path("C:/Users/user/Documents"),
                },
                skill_dir=SKILL_DIR,
            )


if __name__ == "__main__":
    unittest.main()
