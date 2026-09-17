import argparse
import pathlib
import sys

from . import config
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
    args = parser.parse_args(argv)

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
