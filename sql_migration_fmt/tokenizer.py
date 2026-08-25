"""Character-level scanner that turns SQL source into a flat token stream.

The scanner does not know anything about statement grammar - it only knows
how to find the boundaries of strings, quoted identifiers, and comments so
the formatter never mangles their contents. Everything else (keywords,
identifiers, punctuation) is handed back as-is for the formatter to
interpret.
"""

from typing import List, NamedTuple

TWO_CHAR_PUNCT = {"<=", ">=", "<>", "!=", "||"}


class FormatError(Exception):
    """Raised for input the formatter refuses to guess about, or can't parse at all."""


class Token(NamedTuple):
    kind: str  # word, number, string, quoted_ident, comment_line, comment_block, punct, ws, nl
    text: str
    line: int


def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    n = len(source)
    line = 1

    while i < n:
        c = source[i]

        if c == "\n":
            tokens.append(Token("nl", "\n", line))
            line += 1
            i += 1
            continue

        if c == " " or c == "\t":
            start = i
            while i < n and source[i] in " \t":
                i += 1
            tokens.append(Token("ws", source[start:i], line))
            continue

        if c == "-" and source[i : i + 2] == "--":
            start = i
            while i < n and source[i] != "\n":
                i += 1
            tokens.append(Token("comment_line", source[start:i], line))
            continue

        if c == "/" and source[i : i + 2] == "/*":
            start = i
            start_line = line
            end = source.find("*/", i + 2)
            if end == -1:
                raise FormatError(f"line {start_line}: unterminated block comment")
            line += source.count("\n", i, end + 2)
            i = end + 2
            tokens.append(Token("comment_block", source[start:i], start_line))
            continue

        if c == "'":
            start = i
            start_line = line
            i += 1
            while True:
                if i >= n:
                    raise FormatError(f"line {start_line}: unterminated string literal")
                if source[i] == "'":
                    if source[i : i + 2] == "''":
                        i += 2
                        continue
                    i += 1
                    break
                if source[i] == "\n":
                    line += 1
                i += 1
            tokens.append(Token("string", source[start:i], start_line))
            continue

        if c == '"':
            start = i
            start_line = line
            i += 1
            while True:
                if i >= n:
                    raise FormatError(f"line {start_line}: unterminated quoted identifier")
                if source[i] == '"':
                    if source[i : i + 2] == '""':
                        i += 2
                        continue
                    i += 1
                    break
                if source[i] == "\n":
                    line += 1
                i += 1
            tokens.append(Token("quoted_ident", source[start:i], start_line))
            continue

        if c.isalpha() or c == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            tokens.append(Token("word", source[start:i], line))
            continue

        if c.isdigit():
            start = i
            while i < n and source[i].isdigit():
                i += 1
            if i < n and source[i] == "." and i + 1 < n and source[i + 1].isdigit():
                i += 1
                while i < n and source[i].isdigit():
                    i += 1
            tokens.append(Token("number", source[start:i], line))
            continue

        if source[i : i + 2] in TWO_CHAR_PUNCT:
            tokens.append(Token("punct", source[i : i + 2], line))
            i += 2
            continue

        tokens.append(Token("punct", c, line))
        i += 1

    return tokens
