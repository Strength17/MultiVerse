Place your Bible database files here when running from source.

INSTALLED DESKTOP APP: use Documents\WindowVerse\data\ instead (same layout below).

Expected folder layout for multiple versions/languages:

    data/
      NKJV/
        English/NKJV.sqlite3
        French/LSG.sqlite3          <- any language folder name works
      ASV/
        English/ASV.sqlite3

Background images for verse display: data/backgrounds/  (.jpg, .png, .webp)
Pick them in Settings → Verse appearance → Background image.

Before pointing config.ini at any new/different Bible SQLite file, run:
    python inspect_bible_db.py data/YourFile.SQLite3 --sample
This checks the file's actual table/column names (no more guessing) and
caches the result. See COMMANDS.md in the project root for the full
cheat sheet. schema_cache.json will be created automatically here too.
