import pathlib
import tempfile
import unittest

from sql_migration_fmt import config
from sql_migration_fmt.formatter import format_sql


class LoadKeywordOverridesTest(unittest.TestCase):
    def test_overrides_built_in_keyword_casing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / ".sql-migration-fmt.cfg"
            cfg.write_text("[keywords]\nselect = select\nfrom = from\n")
            overrides = config.load_keyword_overrides(cfg)
            self.assertEqual(overrides, {"SELECT": "select", "FROM": "from"})

    def test_adds_word_not_in_built_in_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / ".sql-migration-fmt.cfg"
            cfg.write_text("[keywords]\njsonb_path = JSONB_PATH\n")
            overrides = config.load_keyword_overrides(cfg)
            self.assertEqual(overrides, {"JSONB_PATH": "JSONB_PATH"})

    def test_missing_keywords_section_gives_empty_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / ".sql-migration-fmt.cfg"
            cfg.write_text("[other]\nunrelated = 1\n")
            self.assertEqual(config.load_keyword_overrides(cfg), {})

    def test_blank_value_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / ".sql-migration-fmt.cfg"
            cfg.write_text("[keywords]\nselect =\n")
            self.assertEqual(config.load_keyword_overrides(cfg), {})

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = pathlib.Path(tmp) / "nope.cfg"
            with self.assertRaises(FileNotFoundError):
                config.load_keyword_overrides(missing)


class FindConfigTest(unittest.TestCase):
    def test_finds_config_in_starting_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cfg = root / config.CONFIG_FILENAME
            cfg.write_text("[keywords]\n")
            self.assertEqual(config.find_config(root), cfg)

    def test_walks_up_to_find_config_in_ancestor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cfg = root / config.CONFIG_FILENAME
            cfg.write_text("[keywords]\n")
            nested = root / "migrations" / "2024"
            nested.mkdir(parents=True)
            self.assertEqual(config.find_config(nested), cfg)

    def test_accepts_a_file_path_and_searches_its_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            cfg = root / config.CONFIG_FILENAME
            cfg.write_text("[keywords]\n")
            sql_file = root / "0001_init.sql"
            sql_file.write_text("select 1;")
            self.assertEqual(config.find_config(sql_file), cfg)

    def test_returns_none_when_no_config_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "a" / "b"
            root.mkdir(parents=True)
            # Nothing written anywhere under tmp, so the search reaches the
            # filesystem root without finding a candidate.
            self.assertIsNone(config.find_config(root))


class KeywordCaseIntegrationTest(unittest.TestCase):
    def test_format_sql_applies_keyword_case_override(self):
        out = format_sql("SELECT * FROM t;", keyword_case={"SELECT": "select", "FROM": "from"})
        self.assertEqual(out, "select * from t;\n")

    def test_format_sql_treats_override_only_word_as_keyword(self):
        out = format_sql(
            "select jsonb_path from t;",
            keyword_case={"JSONB_PATH": "JSONB_PATH"},
        )
        self.assertEqual(out, "SELECT JSONB_PATH FROM t;\n")

    def test_lowercased_table_keyword_still_keeps_declared_name_paren_spaced(self):
        # Lowercasing TABLE must not break the object-name-vs-function-call
        # paren check, which matches keyword text case-insensitively.
        out = format_sql(
            "create table users (id serial);",
            keyword_case={"CREATE": "create", "TABLE": "table"},
        )
        self.assertEqual(out, "create table users (id SERIAL);\n")


if __name__ == "__main__":
    unittest.main()
