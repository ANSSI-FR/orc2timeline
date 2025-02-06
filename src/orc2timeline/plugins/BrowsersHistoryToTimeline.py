"""Plugin to parse Browsers History files (SQLite only)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pathlib import Path
if TYPE_CHECKING:
    from threading import Lock

    from orc2timeline.config import PluginConfig

import sqlite3

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline

class BrowsersHistoryToTimeline(GenericToTimeline):
    def __init__(
        self,
        config: PluginConfig,
        orclist: list[str],
        output_file_path: str,
        hostname: str,
        tmp_dir: str,
        lock: Lock,
    ) -> None:
        """Construct.
        Please note that I didn't defined self.file_header.
        Because WAL files have different magic number than SQLite. self.file_header could only contains one byte array.
        Please note also that the match_pattern couldn't be more precise than all .data files,
        as filename nomenclature is not coherent between browsers.
        """
        super().__init__(config, orclist, output_file_path, hostname, tmp_dir, lock)

        self.timestampmap_file = Path(__file__).parent / "BrowsersHistoryToTimeline-timestampmap.json"
        self.timestampmap = self._parse_timestampmap_config_file(self.timestampmap_file)

    def _get_complete_database(self, artefact: Path) -> None:
        """wal file -> storing recent transactions before they are committed to the main database.
        shm file -> shared memory file used for managing WAL operations.
        To get a complete database, it is mandatory to replay pending transactions.
        Otherwise, the database may not be complete.

        There is maybe an error when the results of conn.execute("PRAGMA wal_checkpoint(FULL);") are (0, -1, -1).
        This behaviour likely occurs when shm and wal files does not exists.
        """
        try:
            with sqlite3.connect(Path(artefact)) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                results = cursor.fetchone()
                logging.debug("Database integrity check result: %s", results[0])
                logging.debug("Trying to replay transaction from wal and shm files to get a complete database.")
                cursor = conn.execute("PRAGMA wal_checkpoint(FULL);")
                results = cursor.fetchone()
                conn.commit()
                logging.debug("Replaying transactions successful! Checkpointed frames: %i. WAL size: %i. Frame written to database: %i.", results[0], results[1], results[2])
        except Exception as e:
            logging.warning("Unable to replay database (%s) transactions. Error: %s", artefact.name, e)

    def _get_event(self, table_name: str, data: dict, source: str) -> Event:
        from datetime import datetime, timedelta
        timestamp = datetime(1970, 1, 1) # Will be set after if timestamp exists.
        description = f"TableName: {table_name} - "
        for key, value in data.items():
            description += f"{key}: {value} - "
            # If the value must be considered as the timestamp of the event.
            if table_name in self.timestampmap and self.timestampmap[table_name] == key and value != None:
                if value < 1_000_000_000: # Unix timestamp.
                    timestamp = value / 1_000_000 # Convert into seconds.
                    timestamp = datetime.fromtimestamp(timestamp)
                else: # When timestamp comes from Webkit/Chromium.
                    windows_epoch = datetime(1601, 1, 1)
                    timestamp = windows_epoch + timedelta(microseconds=value)
        return Event(
                   timestamp=timestamp,
                   source=source,
                   description=description
               )

    def _parse_artefact(self, artefact: Path) -> None:
        # Maybe not a perfect filter. The idea is to target only the sqlite file.
        if not ("-shm_" in artefact.name or "-wal_" in artefact.name):
            self._get_complete_database(artefact)
            try:
                with sqlite3.connect(Path(artefact)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM main.sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    for table in tables:
                        rows = cursor.execute(f"SELECT * FROM {table[0]};").fetchall()
                        datas = [dict(row) for row in rows]
                        for data in datas:
                            self._add_event(self._get_event(table[0], data, Path(artefact).name))
            except Exception as e:
                logging.warning("Unable to parse artifacts from (%s). Error: %s", artefact.name, e)

    def _parse_timestampmap_config_file(self, timestampmap_file: Path) -> dict[str, str]:
        """Parse BrowsersHistoryToTimeline-timestampmap.json which contains config about
        which column name must be considered as the event timestamps, for a given table.
        For each table, there MUST be one or zero column name.
        Theses values are used inside _get_event function to add the desired timestamp to the event.
        Config format:
        "<table_name>": "<desired_timestamp_column>"
        """
        import json
        try:
            with timestampmap_file.open(encoding="utf-8") as f:
                return json.load(f)
        except OSError as e:
            logging.critical("Error while opening the timestamp map file %s: %s", timestampmap_file, e)