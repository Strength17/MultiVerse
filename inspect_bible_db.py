"""
inspect_bible_db.py

Standalone utility — run this any time you add or swap in a new Bible
SQLite file, BEFORE running server.py, to see exactly how MultiVerse
will interpret it.

Usage:
    python inspect_bible_db.py data/NKJV.SQLite3
    python inspect_bible_db.py data/NKJV.SQLite3 --rescan
    python inspect_bible_db.py data/NKJV.SQLite3 --sample

Flags:
    --rescan   Ignore the cache and force a fresh schema scan.
    --sample   After detecting the schema, print a couple of sample
               verses (Genesis 1:1 / John 3:16 if present) so you can
               eyeball that the text actually looks right.
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Inspect a Bible SQLite DB's schema.")
    parser.add_argument("db_path", help="Path to the .sqlite3 file, e.g. data/NKJV.SQLite3")
    parser.add_argument("--rescan", action="store_true", help="Force a fresh scan, ignore cache")
    parser.add_argument("--sample", action="store_true", help="Print a couple of sample verses")
    args = parser.parse_args()

    from bible_schema import resolve_schema, SchemaDetectionError

    print(f"\nInspecting: {args.db_path}\n{'-' * 60}")
    try:
        schema = resolve_schema(args.db_path, force_rescan=args.rescan)
    except SchemaDetectionError as e:
        print(f"\n❌ Could not detect a usable schema:\n\n{e}\n")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ {e}\n")
        sys.exit(1)

    print(f"Table:            {schema.table}")
    print(f"Book column:      {schema.col_book}  ({'numeric' if schema.book_is_numeric else 'text/name'})")
    print(f"Chapter column:   {schema.col_chapter}")
    print(f"Verse column:     {schema.col_verse}")
    print(f"Text column:      {schema.col_text}")
    print(f"File hash:        {schema.file_hash}")
    print(f"\n✅ This mapping is now cached — server.py will use it automatically.")

    if args.sample:
        from bible_db import BibleDB
        print(f"\nSample lookups:\n{'-' * 60}")
        db = BibleDB(args.db_path)
        for book_number, chapter, verse, label in [
            (10, 1, 1, "Genesis 1:1"),
            (430, 3, 16, "John 3:16"),
        ]:
            result = db.lookup_verse(book_number, chapter, verse)
            if result:
                print(f"{label}: {result['text']}")
            else:
                print(f"{label}: (not found — check the schema mapping above)")
    print()


if __name__ == "__main__":
    main()
