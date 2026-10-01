"""Install a plain git pre-commit hook, for repos not using the pre-commit framework."""

import os
import pathlib
import shlex
import subprocess
import sys

# Lets uninstall and re-install recognize a hook this tool wrote, so it
# never clobbers one the user wrote by hand.
MARKER = "# installed by sql-migration-fmt"


class HookError(Exception):
    pass


def _git(*args: str, cwd=None) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True
        )
    except FileNotFoundError:
        raise HookError("git is not installed or not on PATH")
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.decode(errors="replace").strip()
        raise HookError(message or f"git {args[0]} failed")
    return result.stdout


def hooks_dir(cwd=None) -> pathlib.Path:
    # --git-path honors core.hooksPath and linked worktrees, which
    # joining ".git/hooks" by hand would not.
    out = _git("rev-parse", "--git-path", "hooks", cwd=cwd).decode().strip()
    return pathlib.Path(cwd or ".").joinpath(out)


def staged_sql_files(cwd=None) -> list:
    top = _git("rev-parse", "--show-toplevel", cwd=cwd).decode().strip()
    out = _git(
        "diff", "--cached", "--name-only", "-z", "--diff-filter=ACM", cwd=cwd
    )
    names = [n for n in out.decode().split("\0") if n.lower().endswith(".sql")]
    return [pathlib.Path(top) / n for n in names]


def hook_script() -> str:
    # Pin the interpreter that installed the hook so it still works when
    # the console script isn't on PATH inside git's environment.
    command = f"{shlex.quote(sys.executable)} -m sql_migration_fmt.cli --check --staged"
    return f"#!/bin/sh\n{MARKER}\nexec {command}\n"


def install(directory: pathlib.Path, force: bool = False) -> pathlib.Path:
    target = directory / "pre-commit"
    if target.exists() and not force and MARKER not in target.read_text():
        raise HookError(
            f"{target} already exists and was not installed by sql-migration-fmt; "
            "use --force to replace it"
        )
    directory.mkdir(parents=True, exist_ok=True)
    target.write_text(hook_script())
    target.chmod(target.stat().st_mode | 0o111)
    return target


def uninstall(directory: pathlib.Path) -> bool:
    target = directory / "pre-commit"
    if not target.exists():
        return False
    if MARKER not in target.read_text():
        raise HookError(f"{target} was not installed by sql-migration-fmt; leaving it alone")
    os.remove(target)
    return True
