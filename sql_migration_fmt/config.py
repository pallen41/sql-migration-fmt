"""Loads per-project overrides for keyword casing.

Teams that write `select` lowercase everywhere, or use dialect-specific
words the built-in keyword list doesn't know about, can drop a config
file next to their migrations instead of fighting the default casing.
"""

import configparser
import pathlib
from typing import Dict, Optional

CONFIG_FILENAME = ".sql-migration-fmt.cfg"


def find_config(start: pathlib.Path) -> Optional[pathlib.Path]:
    """Walk upward from `start` looking for a config file.

    `start` may be a file or a directory; the search begins in its
    containing directory (or itself, if it's already a directory) and
    stops at the filesystem root.
    """
    current = start if start.is_dir() else start.parent
    current = current.resolve()
    while True:
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_keyword_overrides(path: pathlib.Path) -> Dict[str, str]:
    """Parse a config file's [keywords] section into an override map.

    Keys are matched case-insensitively against tokens; values are used
    verbatim as the rendered casing, so `select = select` keeps SELECT
    lowercase and `jsonb_path = JSONB_PATH` adds a dialect word the
    built-in keyword list doesn't otherwise recognize.
    """
    parser = configparser.ConfigParser()
    read_files = parser.read(path, encoding="utf-8")
    if not read_files:
        raise FileNotFoundError(f"config file not found: {path}")

    overrides: Dict[str, str] = {}
    if parser.has_section("keywords"):
        for key, value in parser.items("keywords"):
            value = value.strip()
            if not value:
                continue
            overrides[key.upper()] = value
    return overrides
