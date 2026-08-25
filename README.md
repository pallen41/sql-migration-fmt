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

## Scope and limitations

This is a formatter, not a SQL parser. It tokenizes strings, quoted
identifiers, line comments, and block comments correctly so it never
reformats their contents, but it does not understand statement grammar
beyond parenthesis nesting and semicolon boundaries. Known limitations
in this version:

- content inside block comments and string literals is left exactly as
  written, including internal line breaks
- there's no parenthesis-spacing distinction yet between grouping and
  function calls, so `COUNT (*)` and `WHERE (a = 1)` are spaced the same
- dollar-quoted strings (`$$ ... $$`) and dialect-specific quoting like
  backtick identifiers aren't recognized
- blank lines inside a statement are collapsed rather than preserved

## License

MIT, see LICENSE.
