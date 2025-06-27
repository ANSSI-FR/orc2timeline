"""Plugin to parse RecycleBin files."""

from __future__ import annotations

import struct
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from threading import Lock

    from orc2timeline.config import PluginConfig

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline

EPOCH_AS_FILETIME = 116444736000000000
HUNDREDS_OF_NANOSECONDS = 10000000


class RecycleBinToTimeline(GenericToTimeline):
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

    def _parse_artefact(self, artefact: Path) -> None:
        with artefact.open("rb") as f:
            try:
                raw = f.read()
                (header, file_size, deletion_ts) = struct.unpack_from("<3q", raw)
                epoch_timestamp = (deletion_ts - EPOCH_AS_FILETIME) / HUNDREDS_OF_NANOSECONDS
                event = Event(
                    timestamp=datetime.fromtimestamp(epoch_timestamp, tz=timezone.utc),
                    source=self.originalPath[artefact.name],
                )
                index = struct.calcsize("<3q")
                if header == 1:
                    # INFO2 file version 1: Windows Vista or Windows 7
                    filepath = raw[index : index + 250].decode("utf_16_le").rstrip("\x00")

                elif header == 2:  # noqa: PLR2004
                    # INFO2 file version 2: Windows 10+
                    (fp_length,) = struct.unpack_from("<i", raw[index:])
                    index += struct.calcsize("<i")
                    filepath = raw[index : index + fp_length * 2].decode("utf_16_le").rstrip("\x00")

                else:
                    msg = f"[RecycleBinToTimeline] [{self.hostname}] Unexpected header value : {header}"
                    self.logger.warning(msg)
                    return

                event.description = f"Deletion of file {filepath} - Filesize : {file_size}"
                self._add_event(event)
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Error while parsing %s : %s", artefact.name, e)
