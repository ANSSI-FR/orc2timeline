"""Plugin to parse NTFSInfo files."""

from __future__ import annotations

import _csv
import csv
import logging
import string
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from threading import Lock

    from orc2timeline.config import PluginConfig

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline


class NTFSInfoToTimeline(GenericToTimeline):
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

    def _set_separator(self, parentname: str) -> None:
        if len(parentname) == 0:
            self.separator = "\\"
        elif len(parentname) == 1:
            if parentname != "\\":
                self.separator = "\\"
            else:
                self.separator = ""
        elif parentname[-1] != "\\":
            self.separator = "\\"
        else:
            self.separator = ""

    def _generate_one_csv_line(
        self,
        ntfs_info_row: dict[str, str],
        ntfs_info_path_source: str,
        same_timestamps_group: list[str],
        ref_timestamp: str,
    ) -> None:
        si = [
            ("LastModificationDate", "M"),
            ("LastAccessDate", "A"),
            ("LastAttrChangeDate", "C"),
            ("CreationDate", "B"),
        ]
        fn = [
            ("FileNameLastModificationDate", "M"),
            ("FileNameLastAccessDate", "A"),
            ("FileNameLastAttrModificationDate", "C"),
            ("FileNameCreationDate", "B"),
        ]

        event = Event(timestamp_str=ref_timestamp, source=ntfs_info_path_source)

        fn_flag = ntfs_info_row.get("FilenameFlags")
        if fn_flag is not None and fn_flag == "2":
            return

        meaning = "$SI: "
        for t in si:
            if t[0] in same_timestamps_group:
                meaning += t[1]
            else:
                meaning += "."
        meaning += " - $FN: "
        for t in fn:
            if t[0] in same_timestamps_group:
                meaning += t[1]
            else:
                meaning += "."

        if not hasattr(self, "separator"):
            self._set_separator(ntfs_info_row["ParentName"])
        name = ntfs_info_row["ParentName"] + self.separator + ntfs_info_row["File"]

        size_in_bytes: str | None = "unknown"

        try:
            size_in_bytes = ntfs_info_row.get("SizeInBytes")
        except ValueError as e:
            logging.debug("Error while getting FRN or Size. Error: %s", e)

        event.description = f"{meaning} - Name: {name} - Size in bytes: {size_in_bytes}"
        self._add_event(event)

    def __parse_artefact(self, csv_reader: Any, artefact: Path) -> None:  # noqa: ANN401
        for ntfs_info_row in csv_reader:
            timestamp_fields = [
                "CreationDate",
                "LastModificationDate",
                "LastAccessDate",
                "LastAttrChangeDate",
                "FileNameCreationDate",
                "FileNameLastModificationDate",
                "FileNameLastAccessDate",
                "FileNameLastAttrModificationDate",
            ]

            while len(timestamp_fields) > 0:
                ref_field = timestamp_fields.pop()
                ref_timestamp = ntfs_info_row[ref_field]
                same_timestamps_group = [ref_field]
                same_timestamps_group.extend(
                    field for field in timestamp_fields if ref_timestamp == ntfs_info_row[field]
                )

                self._generate_one_csv_line(
                    ntfs_info_row,
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
                self.__parse_artefact(csv_reader, artefact)
        # when file contains NULL character, old versions of csv can crash
        except (_csv.Error, UnicodeDecodeError) as e:
            with Path(artefact).open(encoding="utf-8", errors="ignore") as fd:
                logging.critical("csv error caught alternative way for host %s: %s", self.hostname, e)
                self._delete_all_result_files()
                data = fd.read()
                clean_data = "".join(c for c in data if c in string.printable)
                data_io = StringIO(clean_data)
                csv_reader = csv.DictReader(data_io)
                self.__parse_artefact(csv_reader, artefact)
