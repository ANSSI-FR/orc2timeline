"""Plugin to parse I30Info files."""

from __future__ import annotations

import _csv
import csv
import logging
import string
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from threading import Lock

    from orc2timeline.config import PluginConfig

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline


class I30InfoToTimeline(GenericToTimeline):
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

    def _generate_one_csv_line(
        self,
        i30_info_row: dict[str, str],
        i30_info_path_source: str,
        same_timestamps_group: list[str],
        ref_timestamp: str,
    ) -> None:
        fn = [
            ("FileNameLastModificationDate", "M"),
            ("FileNameLastAccessDate", "A"),
            ("FileNameLastAttrModificationDate", "C"),
            ("FileNameCreationDate", "B"),
        ]

        event = Event(timestamp_str=ref_timestamp, source=i30_info_path_source)
        meaning = ""
        for t in fn:
            if t[0] in same_timestamps_group:
                meaning += t[1]
            else:
                meaning += "."

        event.description = "Entry in slackspace - $FN: {} - Name: {} - MFT segment num: {} - Parent FRN: {} ".format(
            meaning,
            i30_info_row["Name"],
            str(int(i30_info_row["FRN"], 16) & 0xFFFFFFFFFFFF),
            i30_info_row["ParentFRN"],
        )
        self._add_event(event)

    def _parse_line(self, i30_info_row: dict[str, str], artefact: Path) -> None:
        # CarvedEntry
        if "CarvedEntry" in i30_info_row and i30_info_row["CarvedEntry"] == "Y":
            timestamp_fields = [
                "FileNameCreationDate",
                "FileNameLastModificationDate",
                "FileNameLastAccessDate",
                "FileNameLastAttrModificationDate",
            ]
            while len(timestamp_fields) > 0:
                ref_field = timestamp_fields.pop()
                ref_timestamp = i30_info_row[ref_field]
                same_timestamps_group = [ref_field]
                same_timestamps_group.extend(
                    field for field in timestamp_fields if ref_timestamp == i30_info_row[field]
                )

                # generate an event for a groupe sharing the same timestamp
                self._generate_one_csv_line(
                    i30_info_row,
                    Path(artefact).name,
                    same_timestamps_group,
                    ref_timestamp,
                )

                for field in same_timestamps_group:
                    if field != ref_field:
                        timestamp_fields.remove(field)

    def _parse_artefact(self, artefact: Path) -> None:
        # It is compulsary to use new chunk because if an error occurs
        # all files in self.output_files_list will be deleted an artefact
        # will be reprocessed.
        # Processing as it follow ensures that events extracted from previous
        # artefacts will not be deleted is an error occurs while processing
        # current artefact.
        self.output_files_list = []
        self._flush_chunk_and_new_chunk()
        try:
            with Path(artefact).open(encoding="utf-8") as fd:
                csv_reader = csv.DictReader(fd)
                for i30_info_row in csv_reader:
                    self._parse_line(i30_info_row, artefact)
        # when file contains NULL character, old versions of csv can crash
        except (_csv.Error, UnicodeDecodeError) as e:
            with Path(artefact).open(encoding="utf-8", errors="ignore") as fd:
                logging.critical("csv error caught alternative way for host %s: %s", self.hostname, e)
                self._delete_all_result_files()
                data = fd.read()
                clean_data = "".join(c for c in data if c in string.printable)
                data_io = StringIO(clean_data)
                csv_reader = csv.DictReader(data_io)
                for i30_info_row in csv_reader:
                    self._parse_line(i30_info_row, artefact)
