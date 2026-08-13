# Window Verse — Command Cheat Sheet

Quick reference for the Bible-DB schema detection workflow. Keep this
handy so you don't have to remember flags.

---

## Normal use — nothing to remember

```powershell
python server.py
```

This automatically:
1. Reads `db_path` from `config/config.ini`.
2. Detects the DB's real table/column names (or loads them from cache
   if the file hasn't changed since last time).
3. Refuses to start with a clear error if it can't understand the file
   (instead of silently failing mid-transcript like before).

You do **not** need to run anything manually for the normal case.

---

## When you add or swap in a new Bible database file

**Always inspect a new file BEFORE pointing the server at it:**

```powershell
python inspect_bible_db.py data/YourNewFile.SQLite3 --sample
```

This prints the detected table name, column mapping, and (with
`--sample`) pulls Genesis 1:1 and John 3:16 so you can eyeball that the
text looks right. If it fails, it tells you exactly what tables and
columns it found so you can see why.

Then point `config.ini` at it:

```ini
[database]
db_path = data/YourNewFile.SQLite3
translation = YourTranslationLabel
```

Run `python server.py` — it will pick up the new file and detect its
schema automatically.

---

## Force a re-scan of a file you edited in place

Normally Window Verse only re-scans when the file's content hash changes.
If you're not sure it noticed a change (e.g. you edited it in a way
that didn't change size/edges), force it:

```powershell
python inspect_bible_db.py data/NKJV.SQLite3 --rescan
```

---

## Check or clear the schema cache

The cache lives at `data/schema_cache.json` — plain JSON, safe to open
and read.

Clear the entire cache (forces re-detection of every DB next time it's used):

```powershell
python -c "from bible_schema import clear_cache; clear_cache()"
```

If you swap in a new/different Bible file, delete both caches so neither
the schema mapping nor the chapter/verse range table are stale:

```powershell
del data\schema_cache.json data\range_cache.json
```

Clear just one file's cached entry:

```powershell
python -c "from bible_schema import clear_cache; clear_cache('data/NKJV.SQLite3')"
```

---

## Quick manual peek at a DB's raw tables/columns

If you just want to see what's inside a `.sqlite3` file without running
the full detector (no `sqlite3` CLI needed — it's a built-in Python module):

```powershell
python -c "import sqlite3; c=sqlite3.connect('data/NKJV.SQLite3'); print(c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall())"
```

Then for a specific table's columns:

```powershell
python -c "import sqlite3; c=sqlite3.connect('data/NKJV.SQLite3'); print(c.execute('PRAGMA table_info(bible)').fetchall())"
```

(Replace `bible` with whatever table name the first command returned.)

---

## Tracking multiple translations

`config.ini` has a `[translations]` section for bookkeeping — list the
files you have available there as comments, e.g.:

```ini
[translations]
NKJV = data/NKJV.SQLite3
KJV = data/KJV.SQLite3
ESV = data/ESV.SQLite3
```

To actually switch which one is active, change `db_path` under
`[database]` and run `inspect_bible_db.py` on it first (see above).
This section is not read automatically yet — it's just so you don't
lose track of what files you have.

---

## Files involved

| File | Purpose |
|---|---|
| `bible_schema.py` | Core schema detector — inspects `sqlite_master` + `PRAGMA table_info`, scores candidate tables, resolves the mapping. |
| `bible_db.py` | Uses the resolved schema to build all queries dynamically — no hardcoded table/column names. |
| `inspect_bible_db.py` | Standalone CLI to check a DB before using it. |
| `data/schema_cache.json` | Cached schema mappings, keyed by file path + content hash. Auto-created/updated. |
| `data/range_cache.json` | Cached chapter/verse-count table (per book), keyed the same way. Powers out-of-range detection. Auto-created/updated. |
