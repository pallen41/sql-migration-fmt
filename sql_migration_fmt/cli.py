import argparse
import pathlib
import sys

from . import config, hook
from .formatter import format_sql
from .tokenizer import FormatError


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sql-migration-fmt",
        description="Normalize the formatting of SQL migration files.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="SQL files to format in place. Omit to read from stdin and write to stdout.",
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="Auto-fix ambiguous input instead of failing: expand tabs, normalize "
        "CRLF to LF, and add a missing semicolon at the end of the file.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Don't write anything; exit with status 1 if a file isn't already formatted.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help=f"Path to a keyword-casing config file. Defaults to searching upward "
        f"from each input file (or the current directory, for stdin) for a "
        f"{config.CONFIG_FILENAME} file.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Also process the .sql files staged in the current git repository.",
    )
    parser.add_argument(
        "--install-hook",
        action="store_true",
        help="Install a git pre-commit hook that runs --check on staged .sql files.",
    )
    parser.add_argument(
        "--uninstall-hook",
        action="store_true",
        help="Remove the pre-commit hook installed by --install-hook.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --install-hook, replace an existing pre-commit hook.",
    )
    args = parser.parse_args(argv)

    if args.install_hook or args.uninstall_hook:
        return _manage_hook(args)

    if args.staged:
        try:
            args.files = list(args.files) + hook.staged_sql_files()
        except hook.HookError as exc:
            print(f"sql-migration-fmt: {exc}", file=sys.stderr)
            return 1
        if not args.files:
            return 0

    if args.config:
        try:
            explicit_overrides = config.load_keyword_overrides(pathlib.Path(args.config))
        except OSError as exc:
            print(f"sql-migration-fmt: {exc}", file=sys.stderr)
            return 1
    else:
        explicit_overrides = None

    if not args.files:
        overrides = explicit_overrides
        if overrides is None:
            found = config.find_config(pathlib.Path.cwd())
            overrides = config.load_keyword_overrides(found) if found else {}
        return _run_stdin(args.lenient, args.check, overrides)

    exit_code = 0
    for file_arg in args.files:
        path = pathlib.Path(file_arg)
        source = path.read_text()

        overrides = explicit_overrides
        if overrides is None:
            found = config.find_config(path)
            overrides = config.load_keyword_overrides(found) if found else {}

        try:
            formatted = format_sql(source, lenient=args.lenient, keyword_case=overrides)
        except FormatError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        if args.check:
            if formatted != source:
                print(f"{path}: would reformat", file=sys.stderr)
                exit_code = 1
            continue

        if formatted != source:
            path.write_text(formatted)
            print(f"{path}: formatted")

    return exit_code


def _manage_hook(args) -> int:
    if args.install_hook and args.uninstall_hook:
        print("sql-migration-fmt: choose one of --install-hook or --uninstall-hook", file=sys.stderr)
        return 2
    try:
        directory = hook.hooks_dir()
        if args.install_hook:
            print(f"installed {hook.install(directory, force=args.force)}")
        elif hook.uninstall(directory):
            print(f"removed {directory / 'pre-commit'}")
        else:
            print("no pre-commit hook to remove")
    except (hook.HookError, OSError) as exc:
        print(f"sql-migration-fmt: {exc}", file=sys.stderr)
        return 1
    return 0


def _run_stdin(lenient: bool, check: bool, keyword_case=None) -> int:
    source = sys.stdin.read()
    try:
        formatted = format_sql(source, lenient=lenient, keyword_case=keyword_case)
    except FormatError as exc:
        print(f"sql-migration-fmt: {exc}", file=sys.stderr)
        return 1

    if check:
        return 0 if formatted == source else 1

    sys.stdout.write(formatted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
