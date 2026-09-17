# sql-migration-fmt

Migration files pile up over years and end up written by whoever was
touching the schema that day: some people write `select`, some write
`SELECT`, some indent with tabs, some with two spaces, some with four,
and someone always forgets the trailing semicolon on the last statement
in the file. None of that is a bug, but it makes every diff noisy and
every review slower than it needs to be.

`sql-migration-fmt` reformats `.sql` migration files into one consistent
style: keywords and built-in types uppercased, four-space indentation
driven by parenthesis nesting, no tabs, no trailing whitespace, exactly
one blank line between statements.

## Strict by default

The formatter refuses to guess on a few things that are genuinely
ambiguous rather than silently doing something the author might not
want:

- tabs anywhere in the file
- CRLF line endings
- a final statement with no terminating semicolon

By default these are errors. Pass `--lenient` to have them fixed
automatically instead (tabs expanded to spaces, CRLF normalized to LF,
a semicolon appended at end of file). Everything else about the
formatting - case, indentation, spacing - is always applied; only these
three are gated behind the flag, because they're the ones where "fix it
for me" and "tell me something's wrong" are both reasonable defaults
depending on who's asking.

## Usage

Install locally:

```
pip install -e .
```

Format a file in place:

```
sql-migration-fmt migrations/0042_add_users_table.sql
```

Check formatting in CI without writing anything:

```
sql-migration-fmt --check migrations/*.sql
```

Read from stdin, write to stdout:

```
cat migration.sql | sql-migration-fmt
```

### Example

Input:

```sql
create table users (
	id serial primary key,
	email text not null,
    created_at timestamp default now()
)
```

Running `sql-migration-fmt --lenient` on the above (it has a tab and no
trailing semicolon, so strict mode would reject it) produces:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Custom keyword casing

By default every recognized keyword is uppercased. If a team writes SQL
lowercase, or uses dialect-specific words the built-in keyword list
doesn't know about, drop a `.sql-migration-fmt.cfg` file next to the
migrations (or in any parent directory - the search walks upward from
each input file, the same way `.gitignore` discovery works):

```ini
[keywords]
select = select
from = from
jsonb_path = JSONB_PATH
```

Each line maps a word, matched case-insensitively, to the exact text it
should be rendered as. This both overrides built-in keywords (`select`,
`from`) and adds words the formatter otherwise treats as plain
identifiers (`jsonb_path`) - either way, the word is also treated as a
keyword for paren-spacing purposes. Pass `--config PATH` to use a
specific file instead of searching for one.

## Scope and limitations

This is a formatter, not a SQL parser. It tokenizes strings (including
dollar-quoted strings), quoted identifiers (double-quoted or
backtick-quoted), line comments, and block comments correctly so it
never reformats their contents, but it does not understand statement
grammar beyond parenthesis nesting and semicolon boundaries. Known
limitations in this version:

- content inside block comments, string literals, and dollar-quoted
  strings is left exactly as written, including internal line breaks -
  this is what makes `CREATE FUNCTION ... AS $$ ... $$` bodies safe to
  pass through untouched
- a single blank line inside a statement is kept as-is (useful for
  separating column definitions from constraints in a `CREATE TABLE`);
  runs of two or more are squashed to one, and blank lines at the very
  start or end of a statement are dropped
- function calls like `count(*)` are spaced apart from declared-object
  parens like `CREATE TABLE t (...)` by checking the keyword immediately
  before the name (`TABLE`, `INTO`, `ON`, and similar); if a line break
  falls between that keyword and the name, the check loses that context
  and may guess wrong

## License

MIT, see LICENSE.
