import unittest

from sql_migration_fmt.formatter import format_sql
from sql_migration_fmt.tokenizer import FormatError


class KeywordCasingTest(unittest.TestCase):
    def test_keywords_are_uppercased(self):
        out = format_sql("select * from users;")
        self.assertEqual(out, "SELECT * FROM users;\n")

    def test_identifiers_are_left_alone(self):
        out = format_sql("SELECT Email FROM Users;")
        self.assertEqual(out, "SELECT Email FROM Users;\n")


class ParenSpacingTest(unittest.TestCase):
    """Function calls hug their parens; grouping and clause parens don't."""

    def test_function_call_has_no_space_before_paren(self):
        out = format_sql("select count(*) from t;")
        self.assertEqual(out, "SELECT count(*) FROM t;\n")

    def test_function_call_paren_hugs_even_with_source_space(self):
        out = format_sql("select count (*) from t;")
        self.assertEqual(out, "SELECT count(*) FROM t;\n")

    def test_where_grouping_paren_keeps_leading_space(self):
        out = format_sql("select * from t where (a = 1);")
        self.assertEqual(out, "SELECT * FROM t WHERE (a = 1);\n")

    def test_values_clause_keeps_leading_space(self):
        out = format_sql("insert into t values (1, 2);")
        self.assertEqual(out, "INSERT INTO t VALUES (1, 2);\n")

    def test_no_stray_space_before_closing_paren(self):
        out = format_sql("select * from t where id in (1, 2, 3);")
        self.assertEqual(out, "SELECT * FROM t WHERE id IN (1, 2, 3);\n")

    def test_nested_function_call_inside_grouping_paren(self):
        out = format_sql("select * from t where (count(id) > 1);")
        self.assertEqual(out, "SELECT * FROM t WHERE (count(id) > 1);\n")

    def test_quoted_identifier_as_function_name(self):
        out = format_sql('select "myFunc"(a) from t;')
        self.assertEqual(out, 'SELECT "myFunc"(a) FROM t;\n')

    def test_create_table_name_paren_keeps_space_not_a_call(self):
        out = format_sql("create table users (id serial);")
        self.assertEqual(out, "CREATE TABLE users (id SERIAL);\n")

    def test_create_table_if_not_exists_keeps_space(self):
        out = format_sql("create table if not exists users (id serial);")
        self.assertEqual(out, "CREATE TABLE IF NOT EXISTS users (id SERIAL);\n")

    def test_insert_into_column_list_keeps_space(self):
        out = format_sql("insert into t (a, b) values (1, 2);")
        self.assertEqual(out, "INSERT INTO t (a, b) VALUES (1, 2);\n")


class StatementSplittingTest(unittest.TestCase):
    def test_semicolon_inside_parens_does_not_split_statement(self):
        out = format_sql("create table t (a int);")
        self.assertEqual(out, "CREATE TABLE t (a INT);\n")

    def test_multiple_statements_get_one_blank_line_between(self):
        out = format_sql("select 1; select 2;")
        self.assertEqual(out, "SELECT 1;\n\nSELECT 2;\n")


class StrictModeTest(unittest.TestCase):
    def test_tabs_rejected_without_lenient(self):
        with self.assertRaises(FormatError):
            format_sql("select\t1;")

    def test_tabs_expanded_with_lenient(self):
        out = format_sql("select\t1;", lenient=True)
        self.assertEqual(out, "SELECT 1;\n")

    def test_missing_final_semicolon_rejected_without_lenient(self):
        with self.assertRaises(FormatError):
            format_sql("select 1")

    def test_missing_final_semicolon_added_with_lenient(self):
        out = format_sql("select 1", lenient=True)
        self.assertEqual(out, "SELECT 1;\n")

    def test_crlf_rejected_without_lenient(self):
        with self.assertRaises(FormatError):
            format_sql("select 1;\r\n")

    def test_crlf_normalized_with_lenient(self):
        out = format_sql("select 1;\r\n", lenient=True)
        self.assertEqual(out, "SELECT 1;\n")


if __name__ == "__main__":
    unittest.main()
