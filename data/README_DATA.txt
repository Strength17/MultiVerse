Place your existing NKJV.SQLite3, bible_vectors.index, and bible_verse_map.pkl here (see README step 2). corrections_learned.json will be created automatically after your first session.

Before pointing config.ini at any new/different Bible SQLite file, run:
    python inspect_bible_db.py data/YourFile.SQLite3 --sample
This checks the file's actual table/column names (no more guessing) and
caches the result. See COMMANDS.md in the project root for the full
cheat sheet. schema_cache.json will be created automatically here too.
