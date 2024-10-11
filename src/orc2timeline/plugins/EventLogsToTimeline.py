"""Plugin to parse windows event logs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from threading import Lock

    from orc2timeline.config import PluginConfig

from typing import Any, Iterator

import pyevtx

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline


def _get_event_id(event: Any) -> int | None:  # noqa: ANN401
    try:
        raw_event_id = event.get_event_identifier()
    except OSError:
        logging.debug("Error while trying to recover event identifier")
        return None
    # Mask the facility code, reserved, customer and severity bits. Only keeps the status code.
    return int(0xFFFF & raw_event_id)


def _get_args(event: Any) -> list[str]:  # noqa: ANN401
    args = []
    args_number = 0
    try:
        args_number = event.get_number_of_strings()
    except OSError as e:
        if "unable to retrieve number of strings" in str(e):
            logging.debug(
                "Unable to retrieve args_number for event. Error: %s",
                e,
            )
            return []
        raise

    for i in range(args_number):
        argi = None
        try:
            argi = event.get_string(i)
        except OSError as err:
            if "pyevtx_record_get_string_by_index: unable to determine size of string:" in str(err):
                logging.debug("Unable to get string argument from event. Error: %s", err)
            else:
                raise

        if argi:
            argi = argi.replace("\r\n", "\\r\\n")
            argi = argi.replace("\n", "\\n")
            argi = argi.replace("\r", "\\r")
            args.append(argi)
        else:
            args.append("")

    return args


class EventLogsToTimeline(GenericToTimeline):
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

        self.event_tags_file = Path(__file__).parent / "EventLogsToTimeline-eventmap.txt"
        self.event_tags = self._parse_event_tags_file(self.event_tags_file)

    def _build_description_field(self, event_provider: str, event_id: int, user_id: str, args: list[str]) -> str:
        description = f"{event_provider}:{event_id}"

        if (event_provider in self.event_tags) and (event_id in self.event_tags[event_provider]):
            description += f" {self.event_tags[event_provider][event_id]}"

        description += f" {user_id}"

        if len(args) != 0:
            args_string = " ".join(args)
            description += f" ({args_string})"

        return description

    def _parse_artefact(self, artefact: Path) -> None:
        for event in self._evtx_events(artefact):
            evt_dict = self._evtx_get_event_object(
                event,
                artefact,
                recovered=False,
            )

            if evt_dict and evt_dict.description and evt_dict.description != "":
                self._add_event(evt_dict)

        for event in self._evtx_recovered_events(artefact):
            evt_dict = self._evtx_get_event_object(
                event,
                artefact,
                recovered=True,
            )
            if evt_dict and evt_dict.description and evt_dict.description != "":
                self._add_event(evt_dict)

    def _evtx_recovered_events(self, evtx_file_path: Path) -> Iterator[Any]:
        with Path(evtx_file_path).open("rb") as f:
            evtx_file = pyevtx.file()
            try:
                evtx_file.open_file_object(f)
            except OSError:
                logging.critical(
                    "Error while opening the event log file %s",
                    evtx_file_path,
                )
            else:
                for i in range(evtx_file.number_of_recovered_records):
                    try:
                        evtx = evtx_file.get_recovered_record(i)
                    except OSError as e:
                        logging.debug(
                            "Error while parsing a recovered event record in %s. Error: %s",
                            evtx_file_path,
                            e,
                        )
                        continue
                    yield evtx
                evtx_file.close()

    def _evtx_events(self, evtx_file_path: Path) -> Iterator[Any]:
        with Path(evtx_file_path).open("rb") as f:
            evtx_file = pyevtx.file()
            try:
                evtx_file.open_file_object(f)
            except OSError:
                logging.critical(
                    "Error while opening the event log file %s",
                    evtx_file_path,
                )
            else:
                for i in range(evtx_file.number_of_records):
                    try:
                        evtx = evtx_file.get_record(i)
                    except OSError as e:
                        logging.debug(
                            "Error while parsing an event record in %s. Error: %s",
                            evtx_file_path,
                            e,
                        )
                        continue
                    yield evtx
                evtx_file.close()

    def _evtx_get_event_object(
        self,
        event_input: Any,  # noqa: ANN401
        event_file: Path,
        *,
        recovered: bool,
    ) -> Event | None:
        event_result = Event(source=self._get_original_path(event_file))

        try:
            event_result.timestamp = event_input.get_written_time()
        except ValueError:
            logging.critical("Unable to get written time from event in %s", event_file)
            return None

        # Event ID
        event_id = _get_event_id(event_input)
        if event_id is None:
            return None

        # Get the non formatted arguments
        args = []
        args = _get_args(event_input)

        event_provider = "Unknown"
        try:
            event_provider = event_input.get_source_name()
        except OSError as err:
            if "pyevtx_record_get_source_name: unable to determine size of source name as UTF-8 string." in str(err):
                logging.debug("Unable to get source name from event")
            else:
                raise
        user_id = event_input.get_user_security_identifier()

        event_result.description = self._build_description_field(event_provider, event_id, user_id, args)
        if recovered:
            event_result.description += " (Recovered)"

        return event_result

    def _parse_event_tags_file(self, event_tags_file: Path) -> dict[str, dict[int, str]]:
        """Parse a file containing information to add tags to some event."""
        event_tags = {}
        if event_tags_file.exists():
            with event_tags_file.open() as f:
                for line in f.readlines():
                    my_line = line.strip()

                    # commented-out line
                    if my_line.startswith("#") or len(my_line) == 0:
                        continue

                    splitted_line = my_line.split(":")
                    if len(splitted_line) != 2:  # noqa: PLR2004
                        logging.warning(
                            'Wrong format for a line in %s: "%s"',
                            event_tags_file,
                            my_line,
                        )
                        continue

                    event, tag = splitted_line

                    splitted_event = event.split("/")
                    if len(splitted_event) != 2:  # noqa: PLR2004
                        logging.warning(
                            'Wrong format for a line in %s: "%s"',
                            event_tags_file,
                            my_line,
                        )
                        continue

                    event_provider, event_id = splitted_event[0], int(splitted_event[1])

                    if event_provider not in event_tags:
                        event_tags[event_provider] = {event_id: tag}
                    else:
                        event_tags[event_provider][event_id] = tag

        return event_tags
