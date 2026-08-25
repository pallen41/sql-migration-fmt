import argparse
import pathlib
import sys

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
    args = parser.parse_args(argv)

    if not args.files:
        return _run_stdin(args.lenient, args.check)

    exit_code = 0
    for file_arg in args.files:
        path = pathlib.Path(file_arg)
        source = path.read_text()
        try:
            formatted = format_sql(source, lenient=args.lenient)
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


def _run_stdin(lenient: bool, check: bool) -> int:
    source = sys.stdin.read()
    try:
        formatted = format_sql(source, lenient=lenient)
    except FormatError as exc:
        print(f"sql-migration-fmt: {exc}", file=sys.stderr)
        return 1

    if check:
        return 0 if formatted == source else 1

    sys.stdout.write(formatted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
