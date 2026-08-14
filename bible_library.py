"""
bible_library.py

Auto-discovers Bible database files under a data root and exposes them as
(version, language) pairs, so the app never needs a code change to pick up
a new translation or a new language edition -- drop a file in the right
folder and it shows up.

Expected layout (each level optional -- see discover() docstring for the
fallback when a version has no language subfolders at all):

    data/
      NKJV/
        English/NKJV.sqlite3
        French/LSG.sqlite3          <- any language folder name works;
      ASV/                             this is NOT hardcoded to French/English.
        English/ASV.sqlite3

A "version" is just a folder name under the data root -- it groups
together every language edition of the same underlying translation set,
so that when a verse is detected against data/NKJV/English/..., the
system knows to look for a same-verse rendering in data/NKJV/French/...
(or whatever other language folder sits next to it) without the two
translations needing matching file names.

This module owns discovery + lazy BibleDB loading ONLY. It knows nothing
about detection, WebSocket messages, or the UI -- server.py wires those
together. That separation is what lets the library be rescanned, or a
single bad DB file fail to load, without touching (or crashing) anything
else in the pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from bible_db import BibleDB

logger = logging.getLogger("windowverse.bible_library")

_DB_EXTENSIONS = {".sqlite3", ".sqlite", ".db"}


@dataclass
class VersionEntry:
    version: str
    # language folder name (as found on disk, e.g. "English", "French") -> db file path
    languages: dict[str, Path] = field(default_factory=dict)


class BibleLibrary:
    """
    Scans `data_root` for Bible DB files and caches BibleDB instances per
    (version, language). Nothing here is hardcoded to a specific version
    name or language -- both come entirely from folder names on disk.
    """

    def __init__(self, data_root: str = "data"):
        self.data_root = Path(data_root)
        self._versions: dict[str, VersionEntry] = {}
        self._db_cache: dict[tuple[str, str], BibleDB] = {}

    # ------------------------------------------------------------------
    def rescan(self) -> dict[str, VersionEntry]:
        """
        Re-reads the folder tree from disk. Cheap (just a directory walk,
        no file parsing) -- safe to call periodically. Existing loaded
        BibleDB instances are kept in the cache; only the discovery map is
        rebuilt, so an in-progress detection isn't disturbed by a rescan.
        """
        found: dict[str, VersionEntry] = {}

        if not self.data_root.exists():
            logger.warning("Bible data root '%s' does not exist yet", self.data_root)
            self._versions = found
            return found

        for version_dir in sorted(p for p in self.data_root.iterdir() if p.is_dir()):
            entry = VersionEntry(version=version_dir.name)
            lang_dirs = [p for p in version_dir.iterdir() if p.is_dir()]

            if lang_dirs:
                for lang_dir in sorted(lang_dirs):
                    db_file = self._first_db_file(lang_dir)
                    if db_file:
                        entry.languages[lang_dir.name] = db_file
            else:
                # No language subfolders -- treat the version folder itself
                # as a single (English-default) edition, so a version
                # doesn't need a language folder just to be picked up.
                db_file = self._first_db_file(version_dir)
                if db_file:
                    entry.languages["English"] = db_file

            if entry.languages:
                found[entry.version] = entry

        # Backward compatibility: a flat *.sqlite3 sitting directly in
        # data/ (the pre-existing layout, e.g. data/NKJV.SQLite3) is still
        # picked up as its own single-language version named after the file.
        for f in self.data_root.iterdir():
            if f.is_file() and f.suffix.lower() in _DB_EXTENSIONS:
                version_name = f.stem
                if version_name not in found:
                    found[version_name] = VersionEntry(version=version_name,
                                                         languages={"English": f})

        added = set(found) - set(self._versions)
        removed = set(self._versions) - set(found)
        if added:
            logger.info("Bible library: new version(s) detected: %s", sorted(added))
        if removed:
            logger.info("Bible library: version(s) no longer present: %s", sorted(removed))

        self._versions = found
        return found

    @staticmethod
    def _first_db_file(directory: Path) -> Path | None:
        for f in sorted(directory.iterdir()):
            if f.is_file() and f.suffix.lower() in _DB_EXTENSIONS:
                return f
        return None

    # ------------------------------------------------------------------
    def list_versions(self) -> list[dict]:
        """UI-facing summary: [{version, languages: [..]}]"""
        return [
            {"version": v, "languages": sorted(entry.languages)}
            for v, entry in sorted(self._versions.items())
        ]

    def has_language(self, version: str, language: str) -> bool:
        entry = self._versions.get(version)
        return bool(entry and language in entry.languages)

    def languages_for(self, version: str) -> list[str]:
        entry = self._versions.get(version)
        return sorted(entry.languages) if entry else []

    def secondary_language_for(self, version: str, primary_language: str) -> str | None:
        """Secondary display language for bilingual output. English primary
        always pairs with French when that folder exists."""
        langs = self.languages_for(version)
        if primary_language == "English" and "French" in langs:
            return "French"
        others = [l for l in langs if l != primary_language]
        return others[0] if others else None

    def resolve_primary_db(
        self,
        preferred_version: str = "NKJV",
        preferred_language: str = "English",
    ) -> tuple[str, str, Path] | None:
        """Primary detection DB: preferred NKJV English, then any English edition."""
        if not self._versions:
            self.rescan()
        if preferred_version in self._versions:
            entry = self._versions[preferred_version]
            if preferred_language in entry.languages:
                path = entry.languages[preferred_language]
                if path.exists():
                    return preferred_version, preferred_language, path
        for version, entry in sorted(self._versions.items()):
            if "English" in entry.languages:
                path = entry.languages["English"]
                if path.exists():
                    return version, "English", path
        return None

    def has_french_for_version(self, version: str) -> bool:
        return self.has_language(version, "French")

    # ------------------------------------------------------------------
    def get_db(self, version: str, language: str = "English") -> BibleDB | None:
        """
        Lazily loads (and caches) the BibleDB for this (version, language).
        Returns None -- never raises -- if the pair isn't in the library or
        the file fails schema detection, so a bad/foreign-schema secondary
        DB can't take down primary detection. The failure is logged once.
        """
        key = (version, language)
        if key in self._db_cache:
            return self._db_cache[key]

        entry = self._versions.get(version)
        if not entry or language not in entry.languages:
            return None

        path = entry.languages[language]
        try:
            db = BibleDB(str(path), translation=version)
        except Exception as e:
            logger.error("Failed to load Bible DB %s (%s/%s): %s", path, version, language, e)
            return None

        self._db_cache[key] = db
        return db
