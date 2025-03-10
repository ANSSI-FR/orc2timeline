"""Generic plugin, all real plugin will inherit from this plugin."""

from __future__ import annotations

import bisect
import csv
import logging
import os
import random
import re
import string
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator

import py7zr
import pytz

if TYPE_CHECKING:
    from threading import Lock

    from orc2timeline.config import PluginConfig

MAX_FILE_NAME_LENGTH = 255


def _delete_everything_in_dir(path: Path) -> None:
    """Mimic the command rm -r path."""
    for subpath in path.iterdir():
        if subpath.is_dir():
            _delete_everything_in_dir(subpath)
        else:
            subpath.unlink()
    path.rmdir()


def _get_relevant_archives(orc_list: list[str], archive_list: list[str]) -> Iterator[tuple[str, str]]:
    """Return Iterator that is a tuple of str.

    Return:
    ------
    Iterator[tuple[str, str]]
        first element of tuple: path to orc archive
        second element of tuple: archive type (Details, Memory, Little, General...)

    """
    for orc in orc_list:
        for archive in archive_list:
            if archive in Path(orc).name:
                yield orc, archive


def _extract_sub_archives_from_archive(archive_path: str, extraction_path: Path, sub_archive: str) -> None:
    def _sub_archive_filter(f: str) -> bool:
        return f == sub_archive

    _extract_filtered_files_from_archive(archive_path, extraction_path, _sub_archive_filter)


def _extract_matching_files_from_archive(archive_path: str, extraction_path: Path, match_pattern: str) -> None:
    filter_pattern = re.compile(match_pattern)

    def _re_filter(input_str: str) -> bool:
        return bool(filter_pattern.match(input_str))

    _extract_filtered_files_from_archive(archive_path, extraction_path, _re_filter)


def _extract_getthis_file_from_archive(archive_path: str, extraction_path: Path) -> None:
    def _get_this_filter(f: str) -> bool:
        return f == "GetThis.csv"

    _extract_filtered_files_from_archive(archive_path, extraction_path, _get_this_filter)


def _extract_filtered_files_from_archive(
    archive_path: str,
    extraction_path: Path,
    filter_function: Callable[[str], bool],
) -> None:
    try:
        with py7zr.SevenZipFile(archive_path, mode="r") as z:
            allfiles = z.getnames()
            targets = [f for f in allfiles if filter_function(f)]
            z.extract(
                targets=targets,
                path=extraction_path,
            )
    except OSError as e:
        if "File name too long:" in str(e) or (os.name == "nt" and "Invalid argument" in str(e)):
            _extract_safe(archive_path, extraction_path, filter_function)
        else:
            raise


def _extract_safe(archive_name: str, output_dir: Path, filter_function: Callable[[str], bool]) -> None:
    """Extract files from archive in a safe way.

    This function extracts files from the archive that is located in archive_name.
    All files that match filter_function (this function should return True) are extracted in
    a safe way. output_dir is the directory that will be used to write uncompressed files.

    To extract files in a safer way, the files that name does not exceed MAX_FILE_NAME_LENGTH
    are extracted in the simplest way.
    Matching files that name is too long are extracted using read function, and name will be truncated
    from the beginning until length is less than MAX_FILE_NAME_LENGTH.
    """
    with py7zr.SevenZipFile(archive_name, "r") as z:
        allfiles = z.getnames()
    files_to_extract = []
    exception_file = []
    targets = [f for f in allfiles if filter_function(f)]
    for i in targets:
        if len(Path(i).name) < MAX_FILE_NAME_LENGTH:
            files_to_extract.append(i)
        else:
            exception_file.append(i)

    with py7zr.SevenZipFile(archive_name, "r") as z:
        z.extract(targets=files_to_extract, path=output_dir)
        z.reset()
        res = z.read(targets=exception_file)
        for data in res:
            new_path = output_dir / Path(data).parent
            new_path.mkdir(parents=True, exist_ok=True)
            new_filename = Path(data).name[(len(Path(data).name) - MAX_FILE_NAME_LENGTH) :]
            new_filepath = new_path / new_filename
            with new_filepath.open("wb") as result_file:
                result_file.write(res[data].read())


class Event:
    def __init__(
        self,
        timestamp: datetime | None = None,
        timestamp_str: str = "",
        sourcetype: str = "",
        description: str = "",
        source: str = "",
    ) -> None:
        """Construct."""
        self.timestamp = timestamp
        self.timestamp_str = timestamp_str
        self.sourcetype = sourcetype
        self.description = description
        self.source = source


class SortedChunk:
    """Store events temporary in a sorted way.

    This class describes an object that is used to store the events temporary in a sorted way.
    When the number of events reaches the limit (10 000 be default), the content of the chunk
    is written an disk.
    """

    def __init__(self, max_size: int) -> None:
        """Construct."""
        self.raw_lines: list[str] = []
        self.max_size: int = max_size

    def write(self, s: str) -> None:
        """Write in sorted chink."""
        bisect.insort(self.raw_lines, s)

    def new_chunk(self) -> None:
        """Create new chunk."""
        self.raw_lines = []

    def is_full(self) -> bool:
        """Check if chunk is full."""
        return len(self.raw_lines) > self.max_size


class GenericToTimeline:
    def __init__(
        self,
        config: PluginConfig,
        orclist: list[str],
        output_file_path: str,
        hostname: str,
        tmp_dir: str,
        lock: Lock | None,
    ) -> None:
        """Construct."""
        self.orclist = orclist
        self.hostname = hostname
        self.lock = lock
        self.written_rows_count = 0
        self.current_chunk = SortedChunk(10000)  # Default 10,000 lines at once
        self.output_file_nb = 0
        self.output_files_list: list[Path] = []
        self.nonce = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))  # noqa: S311
        self.output_file_path = f"{output_file_path}_{self.nonce}_nb{self.output_file_nb}"
        self.output_file_prefix = self.output_file_path

        self.archives: list[str] = []
        self.sub_archives: list[str] = []
        self.match_pattern = ""
        self.file_header = bytes([])

        self.sourcetype = ""

        self.tmpDirectory = tempfile.TemporaryDirectory(
            dir=tmp_dir,
            prefix=f"orc2timeline_{self.__class__.__name__}_",
        )

        self.logger = logging.getLogger()
        self.eventList: set[dict[str, str]] = set()
        self.originalPath: dict[str, str] = {}

        self._load_config(config)

    def _setup_next_output_file(self) -> None:
        """Switch output file to new one.

        When writing lines during the plugin execution, lines are not written straight ahead.
        Instead they are stored in a Chunk object (which hold sorted lines in memory), when this Chunk
        is full (10 000 events by default) all the events are written to disk and a new Chunk
        will be used (with a new output file).

        It is compulsary that a new file is used at every new chunk because the functions written
        in core.py consider that every subtimeline is already sorted when create the final timeline.

        File names follow this rule: timeline_{hostname}_{plugin_name}_nb{file_number}
        """
        self.output_file_nb += 1
        self.output_file_path = f"{self.output_file_prefix}_{self.nonce}_nb{self.output_file_nb}"
        self.fd_plugin_file = Path(self.output_file_path).open("w", encoding="utf-8", newline="")  # noqa: SIM115
        self.output_files_list.append(Path(self.output_file_path))

    def _delete_all_result_files(self) -> None:
        """Flush current chunk and delete all result files.

        This is can be necessary when an unpredictable error occurs during plugin execution.
        After calling this function, processing can be re-run from the beginning without worrying
        of previous execution.
        """
        self._flush_chunk()
        for output_file in self.output_files_list:
            logging.critical("Delete %s", self.output_files_list)
            output_file.unlink()
        logging.critical("Reinitialization of chunks")

        self.current_chunk = SortedChunk(10000)
        self.csvWriter = csv.writer(self.current_chunk, delimiter=",", quotechar='"')
        self.output_files_list = []
        self._setup_next_output_file()

    def _deflate_archives(self) -> None:
        """Deflate files from Orc.

        For all Orcs contained in self.orclist:
            Select archive that match self.archives.
                Deflate sub_archive from archive
                    Deflate files that match self.match_pattern from sub_archive in extraction_path

        extraction_path is built ad it follows:
            {tmp_dir}/{orc2timeline_tmp_dir}/{plugin_tmp_dir}/all_extraction
        """
        for orc, archive in _get_relevant_archives(self.orclist, self.archives):
            path_to_create = Path(self.tmpDirectory.name) / archive
            if not path_to_create.exists():
                path_to_create.mkdir(parents=True)
            extraction_path = path_to_create / "all_extraction"
            if len(self.sub_archives) == 0:
                # we look for matching files without subarchive
                try:
                    _extract_matching_files_from_archive(orc, extraction_path, self.match_pattern)
                except Exception as e:  # noqa: BLE001
                    logging.critical(
                        "Unable to open %s archive. Error: %s",
                        orc,
                        e,
                    )
            else:
                for sub_archive in self.sub_archives:
                    try:
                        sub_extraction_path = (
                            Path(self.tmpDirectory.name) / archive / (sub_archive + "_" + str(time.time()))
                        )

                        _extract_sub_archives_from_archive(orc, sub_extraction_path, sub_archive)
                        for f2 in Path(sub_extraction_path).glob(f"./**/{sub_archive}"):
                            _extract_matching_files_from_archive(str(f2), extraction_path, self.match_pattern)
                            _extract_getthis_file_from_archive(str(f2), extraction_path)
                            self._parse_then_delete_getthis_file(
                                extraction_path / "GetThis.csv",
                            )
                        _delete_everything_in_dir(sub_extraction_path)
                    except Exception as e:  # noqa: BLE001
                        err_msg = f"Unable to deflate {sub_archive} from {orc}. Error: {e}"
                        if "Invalid argument" in str(e):
                            err_msg += " (this may happen when compressed file is empty)"
                        logging.critical(err_msg)

    def _parse_artefact(self, artefact: Path) -> None:
        """Artefact specific function.

        The content of this function is specific to every plugin. Events will not be parsed
        the same way LNK files are. Therefore this function should not be implemented in
        the Generic plugin.

        When writing a specific plugin, this function is the only one that should be overwritten.
        """

    def _get_original_path(self, path: Path) -> str:
        original_formatted_path = str(path.relative_to(Path(self.tmpDirectory.name)).as_posix())
        return str(self.originalPath.get(path.name, original_formatted_path))

    def _parse_then_delete_getthis_file(self, path_to_file: Path) -> None:
        try:
            with Path(path_to_file).open(encoding="utf-8") as infile:
                for line in csv.reader(infile):
                    self.originalPath[Path(line[5].replace("\\", "/")).name] = line[4]
            path_to_file.unlink()
        except Exception as e:  # noqa: BLE001
            logging.debug(str(e))

    def _parse_all_artefacts(self) -> None:
        for art in Path(self.tmpDirectory.name).glob("**/all_extraction/**/*"):
            if not art.is_file():
                continue
            file_path_split = Path(art).parts
            try:
                file_name = file_path_split[-1]
                archive_name = "unknown"
                # Get archive name from artefact path (for logging purposes only)
                for i in range(len(file_path_split)):
                    if file_path_split[i] == "all_extraction":
                        archive_name = file_path_split[i - 1]
            except Exception:  # noqa: BLE001
                archive_name = "unknown"
            logging.debug(
                "[%s] [%s] parsing : %s",
                self.hostname,
                archive_name,
                file_name,
            )
            self._parse_artefact(art)

    def _add_event(self, event: Event) -> None:
        timestamp = ""

        if event.timestamp is None and event.timestamp_str == "":
            logging.critical("None Timestamp given for event %s", event)
            timestamp = datetime.fromtimestamp(0, tz=pytz.UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        if event.timestamp_str != "":
            timestamp = event.timestamp_str
        elif event.timestamp is not None:
            try:
                timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            except ValueError as e:
                logging.critical(e)
                timestamp = datetime.fromtimestamp(0, tz=pytz.UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        self._write_line(
            timestamp,
            self.sourcetype,
            event.description,
            event.source,
        )

    def _write_line(self, date: str, sourcetype: str, description: str, sourcefile: str) -> None:
        """Write event to timeline.

        The events are not written to disk along the way, instead they are store in a chunk object
        (in memory), when the chunk reaches the event number limit, all the events are written to
        disk in a sorted way. A new chunk will be used and its content will be written in another
        file.
        """
        # sanitize output
        rows_to_write = [row.replace("\n", "\\n") for row in (date, self.hostname, sourcetype, description, sourcefile)]
        self.csvWriter.writerow(rows_to_write)
        if self.current_chunk.is_full():
            self._flush_chunk_and_new_chunk()

    def _flush_chunk(self) -> None:
        self.fd_plugin_file.writelines(self.current_chunk.raw_lines)
        self.fd_plugin_file.close()
        self.written_rows_count += len(self.current_chunk.raw_lines)

    def _flush_chunk_and_new_chunk(self) -> None:
        self._flush_chunk()
        self.current_chunk.new_chunk()
        self._setup_next_output_file()

    def _filter_files_based_on_first_bytes(self) -> None:
        if len(self.file_header) == 0:
            return

        for art in Path(self.tmpDirectory.name).glob("**/all_extraction/**/*"):
            if not art.is_file():
                continue
            must_delete = False
            with Path(art).open("rb") as fd:
                first_bytes_of_file = fd.read(len(self.file_header))
                if first_bytes_of_file != self.file_header:
                    must_delete = True
            if must_delete:
                art.unlink()

    def _load_config(self, config: PluginConfig) -> None:
        self.archives = config.archives
        self.sub_archives = config.sub_archives
        self.match_pattern = config.match_pattern
        self.sourcetype = config.sourcetype

    def add_to_timeline(self) -> int:
        """Create the result file with the result of argument parsing."""
        logging.debug("%s started", self.__class__.__name__)
        self.csvWriter = csv.writer(self.current_chunk, delimiter=",", quotechar='"')
        self._setup_next_output_file()
        self._deflate_archives()
        self._filter_files_based_on_first_bytes()
        self._parse_all_artefacts()
        self._flush_chunk()
        logging.debug("%s ended", self.__class__.__name__)
        return self.written_rows_count
