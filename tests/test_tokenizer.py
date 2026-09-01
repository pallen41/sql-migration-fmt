import unittest

from sql_migration_fmt.tokenizer import FormatError, tokenize


def kinds(tokens):
    return [t.kind for t in tokens]


def texts(tokens):
    return [t.text for t in tokens]


class RoundTripTest(unittest.TestCase):
    """Every token's text concatenated back together must equal the source.

    This is the invariant the rest of the formatter leans on: it never
    has to reconstruct whitespace or punctuation itself, only reorder
    and re-space the tokens it's given.
    """

    def check(self, source):
        self.assertEqual("".join(t.text for t in tokenize(source)), source)

    def test_plain_statement(self):
        self.check("select * from users where id = 1;")

    def test_mixed_quoting_and_comments(self):
        self.check(
            "SELECT \"col\"\"umn\" -- trailing comment\n"
            "FROM t /* block\ncomment */ WHERE x = 'a''b'\n"
        )

    def test_empty_source(self):
        self.check("")


class WhitespaceAndNewlineTest(unittest.TestCase):
    def test_empty_source_has_no_tokens(self):
        self.assertEqual(tokenize(""), [])

    def test_spaces_and_tabs_group_into_one_token(self):
        tokens = tokenize("  \t \t")
        self.assertEqual(kinds(tokens), ["ws"])
        self.assertEqual(texts(tokens), ["  \t \t"])

    def test_newline_is_its_own_token_and_bumps_line(self):
        tokens = tokenize("a\nb")
        self.assertEqual(kinds(tokens), ["word", "nl", "word"])
        self.assertEqual([t.line for t in tokens], [1, 1, 2])


class CommentTest(unittest.TestCase):
    def test_line_comment_stops_before_newline(self):
        tokens = tokenize("-- hello\nSELECT")
        self.assertEqual(kinds(tokens), ["comment_line", "nl", "word"])
        self.assertEqual(tokens[0].text, "-- hello")
        self.assertEqual(tokens[2].line, 2)

    def test_line_comment_at_end_of_file(self):
        tokens = tokenize("-- no trailing newline")
        self.assertEqual(kinds(tokens), ["comment_line"])
        self.assertEqual(tokens[0].text, "-- no trailing newline")

    def test_block_comment_single_line(self):
        tokens = tokenize("/* hi */")
        self.assertEqual(kinds(tokens), ["comment_block"])
        self.assertEqual(tokens[0].text, "/* hi */")
        self.assertEqual(tokens[0].line, 1)

    def test_block_comment_spans_lines_and_advances_line_counter(self):
        tokens = tokenize("/*\n\n*/x")
        self.assertEqual(kinds(tokens), ["comment_block", "word"])
        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[1].line, 3)

    def test_unterminated_block_comment_raises(self):
        with self.assertRaises(FormatError):
            tokenize("/* never closes")


class StringLiteralTest(unittest.TestCase):
    def test_simple_string(self):
        tokens = tokenize("'hello'")
        self.assertEqual(kinds(tokens), ["string"])
        self.assertEqual(tokens[0].text, "'hello'")

    def test_doubled_quote_is_escape_not_terminator(self):
        tokens = tokenize("'it''s'")
        self.assertEqual(kinds(tokens), ["string"])
        self.assertEqual(tokens[0].text, "'it''s'")

    def test_string_spanning_lines_updates_line_counter(self):
        tokens = tokenize("'a\nb' x")
        self.assertEqual(tokens[0].kind, "string")
        self.assertEqual(tokens[0].line, 1)
        word = [t for t in tokens if t.kind == "word"][0]
        self.assertEqual(word.line, 2)

    def test_unterminated_string_raises(self):
        with self.assertRaises(FormatError):
            tokenize("'abc")


class QuotedIdentifierTest(unittest.TestCase):
    def test_doubled_quote_is_escape_not_terminator(self):
        tokens = tokenize('"a""b"')
        self.assertEqual(kinds(tokens), ["quoted_ident"])
        self.assertEqual(tokens[0].text, '"a""b"')

    def test_unterminated_quoted_identifier_raises(self):
        with self.assertRaises(FormatError):
            tokenize('"abc')


class WordAndNumberTest(unittest.TestCase):
    def test_identifier_with_underscore_and_digits(self):
        tokens = tokenize("_foo123 bar")
        self.assertEqual(kinds(tokens), ["word", "ws", "word"])
        self.assertEqual(texts(tokens), ["_foo123", " ", "bar"])

    def test_integer(self):
        tokens = tokenize("123")
        self.assertEqual(kinds(tokens), ["number"])
        self.assertEqual(tokens[0].text, "123")

    def test_decimal(self):
        tokens = tokenize("123.45")
        self.assertEqual(kinds(tokens), ["number"])
        self.assertEqual(tokens[0].text, "123.45")

    def test_trailing_dot_is_not_absorbed_into_number(self):
        tokens = tokenize("123.")
        self.assertEqual(kinds(tokens), ["number", "punct"])
        self.assertEqual(texts(tokens), ["123", "."])


class PunctuationTest(unittest.TestCase):
    def test_two_char_operators(self):
        tokens = tokenize("<= >= <> != ||")
        punct = [t.text for t in tokens if t.kind == "punct"]
        self.assertEqual(punct, ["<=", ">=", "<>", "!=", "||"])

    def test_single_char_punctuation_not_merged(self):
        tokens = tokenize("(),;.+")
        self.assertEqual(kinds(tokens), ["punct"] * 6)
        self.assertEqual(texts(tokens), ["(", ")", ",", ";", ".", "+"])


if __name__ == "__main__":
    unittest.main()
