"""Reformats SQL migration source into a consistent house style.

Strict by default: input that would require guessing (tabs, CRLF line
endings, a final statement with no terminating semicolon) is rejected with
an error rather than silently "fixed" in a way the author might not want.
Pass lenient=True to auto-fix those cases instead.
"""

from typing import Dict, List, Optional

from .tokenizer import FormatError, Token, tokenize

INDENT = "    "

KEYWORDS = frozenset(
    """
    SELECT FROM WHERE INSERT INTO VALUES UPDATE SET DELETE
    CREATE TABLE ALTER DROP ADD COLUMN CONSTRAINT PRIMARY KEY
    FOREIGN REFERENCES NOT NULL DEFAULT UNIQUE INDEX ON JOIN
    INNER LEFT RIGHT OUTER CROSS GROUP BY ORDER HAVING LIMIT OFFSET
    AS AND OR IN IS LIKE BETWEEN CASE WHEN THEN ELSE END
    DISTINCT EXISTS UNION ALL IF USING WITH VIEW TRIGGER FUNCTION
    RETURNS LANGUAGE BEGIN COMMIT ROLLBACK TRANSACTION GRANT REVOKE TO
    CASCADE RESTRICT TRUNCATE RENAME CHECK ASC DESC NULLS FIRST LAST
    VARCHAR INTEGER INT BIGINT SMALLINT BOOLEAN TEXT TIMESTAMP DATE
    NUMERIC DECIMAL SERIAL CHAR FLOAT DOUBLE PRECISION
    """.split()
)

NO_SPACE_BEFORE = {",", ";", ".", ")"}
NO_SPACE_AFTER = {"(", "."}
NON_CODE_KINDS = {"ws", "nl", "comment_line", "comment_block"}

# A "(" only opens a function call - and so should hug the token before it -
# when that token is an identifier being called. Anything else (a keyword
# like WHERE/IN/VALUES, an operator, another paren) is grouping or clause
# syntax, which keeps its usual leading space.
CALL_PAREN_KINDS = {"word", "quoted_ident"}

# Bare identifiers also precede a "(" when they're a declared object name
# rather than a function being called - CREATE TABLE users (...), INSERT
# INTO t (...), CREATE INDEX ON t (...). Walking back from the identifier
# over any keyword chain (e.g. "IF NOT EXISTS") to one of these keeps those
# column/definition lists spaced like grouping parens instead.
OBJECT_NAME_KEYWORDS = frozenset(
    {"TABLE", "INTO", "ON", "VIEW", "INDEX", "COLUMN", "CONSTRAINT", "TRIGGER", "REFERENCES"}
)


def _is_function_call_paren(kinds: List[str], texts: List[str], i: int) -> bool:
    if kinds[i - 1] not in CALL_PAREN_KINDS:
        return False
    j = i - 2
    while j >= 0 and kinds[j] == "keyword":
        if texts[j].upper() in OBJECT_NAME_KEYWORDS:
            return False
        j -= 1
    return True


def format_sql(
    source: str,
    *,
    lenient: bool = False,
    keyword_case: Optional[Dict[str, str]] = None,
) -> str:
    """Reformat `source`.

    `keyword_case` is an optional map from an uppercased word (e.g.
    "SELECT") to the exact text it should be rendered as. It can override
    the casing of a built-in keyword or add a dialect-specific word the
    built-in list doesn't know about; either way, the word starts being
    treated as a keyword for spacing purposes too.
    """
    if "\t" in source and not lenient:
        raise FormatError("tabs found; rerun with --lenient to expand them, or replace with spaces")
    if "\r" in source:
        if not lenient:
            raise FormatError("CRLF line endings found; rerun with --lenient to normalize to LF")
        source = source.replace("\r\n", "\n").replace("\r", "\n")
    if lenient:
        source = source.expandtabs(4)

    tokens = tokenize(source)
    statements, leftover = _split_statements(tokens)

    if _has_statement_content(leftover):
        if not lenient:
            raise FormatError("missing semicolon terminating final statement")
        statements.append(leftover)
    elif any(t.kind in ("comment_line", "comment_block") for t in leftover):
        statements.append(leftover)

    blocks = [
        rendered
        for rendered in (_render_statement(s, keyword_case) for s in statements)
        if rendered
    ]
    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n"


def _split_statements(tokens: List[Token]):
    statements = []
    current: List[Token] = []
    depth = 0
    for tok in tokens:
        if tok.kind == "punct":
            if tok.text == "(":
                depth += 1
            elif tok.text == ")":
                depth = max(0, depth - 1)
            elif tok.text == ";" and depth == 0:
                statements.append(current)
                current = []
                continue
        current.append(tok)
    return statements, current


def _has_statement_content(tokens: List[Token]) -> bool:
    return any(t.kind not in NON_CODE_KINDS for t in tokens)


def _is_blank_line(line: List[Token]) -> bool:
    return all(t.kind == "ws" for t in line)


def _collapse_blank_lines(lines: List[List[Token]]) -> List[List[Token]]:
    """Drop leading/trailing blank lines and squash interior runs to one.

    A blank line the author left between two clauses is usually there on
    purpose (separating column defs from constraints, say), so it's kept -
    but only one of them, and never at the edges of the statement, since
    that spacing is already handled by the blank line _render_statement's
    caller puts between statements.
    """
    start = 0
    end = len(lines)
    while start < end and _is_blank_line(lines[start]):
        start += 1
    while end > start and _is_blank_line(lines[end - 1]):
        end -= 1
    lines = lines[start:end]

    result: List[List[Token]] = []
    prev_blank = False
    for ln in lines:
        blank = _is_blank_line(ln)
        if blank and prev_blank:
            continue
        result.append(ln)
        prev_blank = blank
    return result


def _render_statement(tokens: List[Token], keyword_case: Optional[Dict[str, str]] = None) -> str:
    lines: List[List[Token]] = []
    current: List[Token] = []
    for tok in tokens:
        if tok.kind == "nl":
            lines.append(current)
            current = []
        else:
            current.append(tok)
    lines.append(current)
    lines = _collapse_blank_lines(lines)
    if not lines:
        return ""

    depth = 0
    out_lines = []
    has_code = False
    for line in lines:
        if _is_blank_line(line):
            out_lines.append("")
            continue

        content = [t for t in line if t.kind != "ws"]
        leading_close = 0
        for t in content:
            if t.kind == "punct" and t.text == ")":
                leading_close += 1
            else:
                break

        indent = max(0, depth - leading_close)
        out_lines.append(INDENT * indent + _render_line(content, keyword_case))

        for t in content:
            if t.kind not in NON_CODE_KINDS:
                has_code = True
            if t.kind == "punct":
                if t.text == "(":
                    depth += 1
                elif t.text == ")":
                    depth = max(0, depth - 1)

    body = "\n".join(out_lines)
    return body + (";" if has_code else "")


def _render_line(content: List[Token], keyword_case: Optional[Dict[str, str]] = None) -> str:
    overrides = keyword_case or {}
    texts = []
    kinds = []
    for t in content:
        upper = t.text.upper()
        if t.kind == "word" and upper in overrides:
            texts.append(overrides[upper])
            kinds.append("keyword")
        elif t.kind == "word" and upper in KEYWORDS:
            texts.append(upper)
            kinds.append("keyword")
        else:
            texts.append(t.text)
            kinds.append(t.kind)

    pieces = []
    for i, text in enumerate(texts):
        if i == 0:
            pieces.append(text)
            continue
        prev_text = texts[i - 1]
        if text == "(" and _is_function_call_paren(kinds, texts, i):
            needs_space = False
        else:
            needs_space = not (text in NO_SPACE_BEFORE or prev_text in NO_SPACE_AFTER)
        if needs_space:
            pieces.append(" ")
        pieces.append(text)
    return "".join(pieces)
