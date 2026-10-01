import os
import pathlib
import stat
import tempfile
import unittest

from sql_migration_fmt import hook


class InstallTest(unittest.TestCase):
    def test_writes_executable_script_with_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = hook.install(pathlib.Path(tmp) / "hooks")
            text = target.read_text()
            self.assertTrue(text.startswith("#!/bin/sh\n"))
            self.assertIn(hook.MARKER, text)
            self.assertIn("--check --staged", text)
            self.assertTrue(target.stat().st_mode & stat.S_IXUSR)

    def test_reinstall_over_own_hook_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            hook.install(directory)
            hook.install(directory)

    def test_refuses_to_replace_foreign_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            (directory / "pre-commit").write_text("#!/bin/sh\necho mine\n")
            with self.assertRaises(hook.HookError):
                hook.install(directory)
            self.assertEqual((directory / "pre-commit").read_text(), "#!/bin/sh\necho mine\n")

    def test_force_replaces_foreign_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            (directory / "pre-commit").write_text("#!/bin/sh\necho mine\n")
            hook.install(directory, force=True)
            self.assertIn(hook.MARKER, (directory / "pre-commit").read_text())


class UninstallTest(unittest.TestCase):
    def test_removes_own_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            hook.install(directory)
            self.assertTrue(hook.uninstall(directory))
            self.assertFalse(os.path.exists(directory / "pre-commit"))

    def test_missing_hook_reports_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(hook.uninstall(pathlib.Path(tmp)))

    def test_leaves_foreign_hook_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            (directory / "pre-commit").write_text("#!/bin/sh\necho mine\n")
            with self.assertRaises(hook.HookError):
                hook.uninstall(directory)
            self.assertTrue((directory / "pre-commit").exists())


if __name__ == "__main__":
    unittest.main()
