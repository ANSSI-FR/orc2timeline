"""Generic plugin to parse Firefox histories (places.sqlite)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytz

if TYPE_CHECKING:
    from pathlib import Path
    from threading import Lock

    from orc2timeline.config import PluginConfig

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline


def _reverse_hostname(hostname: str) -> str:

    if not hostname:
        return ""

    if len(hostname) <= 1:
        return hostname

    if hostname[-1] == ".":
        return hostname[::-1][1:]

    return hostname[::-1][0:]


class FirefoxHistoryToTimeline(GenericToTimeline):
    def __init__(
        self,
        config: PluginConfig,
        orclist: list[str],
        output_file_path: str,
        hostname: str,
        tmp_dir: str,
        lock: Lock,
    ) -> None:
        """Construct."""
        super().__init__(config, orclist, output_file_path, hostname, tmp_dir, lock)

        self.schema: dict[str, str] = {}
        self.columns_per_table: dict[str, list[str]] = {}
        self.required_structure = {
            "moz_places": frozenset(["url", "title", "visit_count", "rev_host", "hidden", "typed", "id"]),
            "moz_historyvisits": frozenset(["id", "visit_date", "from_visit", "visit_type", "place_id"]),
            "moz_bookmarks": frozenset(["type", "title", "dateAdded", "lastModified", "id", "fk"]),
            "moz_items_annos": frozenset(["content", "dateAdded", "lastModified", "id", "item_id"]),
        }

    def _get_schema(self, curr: sqlite3.Cursor) -> None:
        sql_req = (
            'SELECT tbl_name, sql FROM sqlite_master WHERE type = "table" AND '
            'tbl_name != "xp_proc" AND tbl_name != "sqlite_sequence"'
        )
        sql_results = curr.execute(sql_req)
        self.schema = {table_name: " ".join(query.split()) for table_name, query in sql_results}

    def _validate_db(self) -> bool:
        if not self.required_structure:
            return True

        for required_table, required_columns in self.required_structure.items():
            if required_table not in self.schema:
                return False

            ze_table = self.columns_per_table.get(required_table)
            if ze_table is not None and (not frozenset(required_columns).issubset(ze_table)):
                return False

        return True

    def _parse_visited_row(self, curr: sqlite3.Cursor, sqlite_path: Path) -> None:

        query = (
            "SELECT moz_historyvisits.id, moz_places.url, moz_places.title, "
            "moz_places.visit_count, moz_historyvisits.visit_date, "
            "(select moz_places.url from moz_places where moz_historyvisits.from_visit=moz_places.id) as referer_name,"
            "moz_historyvisits.from_visit, moz_places.rev_host, "
            "moz_places.hidden, moz_places.typed, moz_historyvisits.visit_type "
            "FROM moz_places, moz_historyvisits "
            "WHERE moz_places.id = moz_historyvisits.place_id"
        )

        curr.execute(query)
        sql_result = curr.fetchall()
        col_names = [desc[0] for desc in curr.description]

        for row in sql_result:
            row_dict = {col_names[i]: row[i] for i in range(len(col_names))}  # trick to create a dict from sql result
            description = (
                f"Url: {row_dict['url']} - "
                f"Title: {row_dict['title']} - "
                f"Count: {row_dict['visit_count']} - "
                f"Typed: {row_dict['typed']} - "
                f"Referer: {row_dict['referer_name']}"
            )
            # typed = tapé manuellement ?
            # hidden
            # referer => résoudre
            epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)
            timestamp = epoch + timedelta(microseconds=int(row_dict["visit_date"]))
            event = Event(timestamp=timestamp, source=self._get_original_path(sqlite_path), description=description)
            self._add_event(event)

    def _parse_artefact(self, artefact: Path) -> None:
        if "places.sqlite-wal" in artefact.stem or "places.sqlite-shm" in artefact.stem:
            return

        try:
            conn = sqlite3.connect(artefact)
            curr = conn.cursor()

            self._get_schema(curr)
            for table_name in self.schema:
                self.columns_per_table.setdefault(table_name, [])
                pragma_results = curr.execute(f'PRAGMA table_info("{table_name:s}")')
                for pragma_result in pragma_results:
                    self.columns_per_table[table_name].append(pragma_result[1])

            if self._validate_db():
                self._parse_visited_row(curr, artefact)

        except sqlite3.DatabaseError:
            self.logger.exception("%s is not a valid databse", artefact)
        except Exception:
            raise
