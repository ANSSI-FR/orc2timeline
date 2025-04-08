"""Plugin to parse USNInfo files."""

from __future__ import annotations

import _csv
import csv
import string
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from threading import Lock

    from orc2timeline.config import PluginConfig

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline


class USNInfoToTimeline(GenericToTimeline):
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

    def _parse_usn_file(self, csv_reader: Any, artefact: Path) -> None:  # noqa: ANN401
        for row in csv_reader:
            # Not pretty but it's a way to skip header
            if row["USN"] == "USN":
                continue
            event = Event(
                timestamp_str=row["TimeStamp"],
                source=Path(artefact).name,
            )
            mft_segment_number = 0
            try:
                mft_segment_number = int(row["FRN"], 16) & 0xFFFFFFFF
            except ValueError as e:
                self.logger.warning("Error while getting FRN. Error: %s", e)
            full_path = row["FullPath"]
            reason = row["Reason"]
            event.description = f"{full_path} - {reason} - MFT segment num : {mft_segment_number}"

            self._add_event(event)

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
                self._parse_usn_file(csv_reader, artefact)
        # when file contains NULL character, old versions of csv can crash
        except (_csv.Error, UnicodeDecodeError) as e:
            with Path(artefact).open(encoding="utf-8", errors="ignore") as fd:
                self.logger.critical("csv error caught alternative way for host %s: %s", self.hostname, e)
                self._delete_all_result_files()
                data = fd.read()
                clean_data = "".join(c for c in data if c in string.printable)
                data_io = StringIO(clean_data)
                csv_reader = csv.DictReader(data_io)
                self._parse_usn_file(csv_reader, artefact)
