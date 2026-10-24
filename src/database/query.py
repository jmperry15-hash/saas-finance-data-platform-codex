"""Run one SQL query against the local learning database without modifying it."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from .load import DEFAULT_DATABASE


def run_query(database, sql, limit=50):
    if limit < 1:
        raise ValueError("Display limit must be positive")
    # mode=ro prevents SQLite from silently creating a missing database.
    uri = Path(database).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        conn.execute("PRAGMA query_only = ON")
        cursor = conn.execute(sql)
        if cursor.description is None:
            raise ValueError("Use a SELECT query that returns rows")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(limit + 1)
        return columns, rows[:limit], len(rows) > limit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="SQL file containing one query")
    source.add_argument("--sql", help="One SQL query")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--limit", type=int, default=50, help="Maximum displayed rows (default: 50)")
    args = parser.parse_args()
    try:
        sql = args.file.read_text() if args.file else args.sql
        columns, rows, truncated = run_query(args.database, sql, args.limit)
        display = [["NULL" if value is None else str(value) for value in row] for row in rows]
        widths = [max([len(col)] + [len(row[i]) for row in display]) for i, col in enumerate(columns)]
        for row in [columns, ["-" * n for n in widths]] + display:
            print(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)))
        print(f"{len(rows)} row(s) shown" + ("; more available (increase --limit)." if truncated else "."))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"Query failed: {exc}\n")


if __name__ == "__main__":
    main()
