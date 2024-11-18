"""Core module."""

from __future__ import annotations

import concurrent.futures
import csv
import gzip
import heapq
import logging
import multiprocessing
import os
import shutil
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, TextIO

if TYPE_CHECKING:
    from threading import Lock as LockType

from .config import Config

ROOT_DIR = Path(__file__).resolve().parent
TEMP_DIRECTORY: Any = None


def _add_header_to_csv_file(output_path: str) -> None:
    """Add header at the beginning of csv file."""
    header = ["Timestamp", "Hostname", "SourceType", "Description", "SourceFile"]
    with gzip.open(output_path, "wt", newline="") as f:
        csv_dict_writer = csv.DictWriter(f, delimiter=",", quotechar='"', fieldnames=header)
        csv_dict_writer.writeheader()


def _map_open(input_file: Path) -> TextIO:
    return input_file.open(encoding="utf-8")


def _merge_sorted_files(paths: list[Path], output_path: str, temp_dir: str) -> int:
    """Merge sorted files contained in paths list to output_path file and return number of unique lines."""
    events_count = 0
    intermediate_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
        dir=temp_dir,
        encoding="utf-8",
        mode="w+",
        delete=False,
    )
    old_intermediate_file_name = ""
    while len(paths) != 0:
        sub_paths = []
        # We merge files by batch so that we do not reach the limitation of files opened at the same time
        # arbitrary value is 300 because 512 is the maximum value on Windows
        sub_paths = [paths.pop() for _ in range(min(300, len(paths)))]
        if old_intermediate_file_name != "":
            sub_paths.append(Path(old_intermediate_file_name))

        files = map(_map_open, sub_paths)
        previous_comparable = ""
        for line in heapq.merge(*files):
            comparable = line
            if previous_comparable != comparable:
                intermediate_file.write(line)
                previous_comparable = comparable
                if len(paths) == 0:
                    events_count += 1
        old_intermediate_file_name = intermediate_file.name
        intermediate_file.close()
        for f in files:
            f.close()
        intermediate_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
            dir=temp_dir,
            encoding="utf-8",
            mode="w+",
            delete=False,
        )

    _add_header_to_csv_file(output_path)
    with Path(old_intermediate_file_name).open(encoding="utf-8") as infile, gzip.open(
        output_path,
        "at",
        encoding="utf-8",
        newline="",
    ) as outfile:
        shutil.copyfileobj(infile, outfile)  # type: ignore[misc]

    return events_count


def _merge_timelines_for_host(hostname: str, output_path: str, tmp_dir: tempfile.TemporaryDirectory[str]) -> int:
    """Merge subtimelines for a given host.

    Merge all files that match 'timeline_{hostname}_*' regex
    for hostname in temporary directory to output_path file.
    """
    files_to_merge = list(Path(tmp_dir.name).glob(f"**/timeline_{hostname}_*"))
    logging.info("Merging all timelines generated per artefact for host %s", hostname)

    result = _merge_sorted_files(
        files_to_merge,
        output_path,
        tmp_dir.name,
    )

    for file in files_to_merge:
        file.unlink()

    return result


def _is_list_uniq(host_list: list[str]) -> bool:
    """Return True if all elements are different in host_lists."""
    return len(host_list) == len(set(host_list))


def _get_duplicate_values_from_list(input_list: list[str]) -> set[str]:
    """Return a sublist of input_list containing duplicate values of this list."""
    seen = set()
    dupes = set()
    for x in input_list:
        if x in seen:
            dupes.add(x)
        else:
            seen.add(x)
    return dupes


def _load_plugins(
    config: Config,
    orc_arguments: list[OrcArgument],
    tmp_dir: TemporaryDirectory[str],
    lock: LockType | None,
) -> list[Any]:
    plugin_classes_list = []
    for orc_argument in orc_arguments:
        hostname = orc_argument.hostname
        for plugin_config in config.plugin_conf_list:
            mod = import_module(f"orc2timeline.plugins.{plugin_config.plugin_name}")
            plugin_class = getattr(mod, plugin_config.plugin_name, None)
            if plugin_class is not None:
                plugin_timeline_path = Path(tmp_dir.name) / f"timeline_{hostname}_{plugin_class.__name__}"
                plugin_classes_list.append(
                    plugin_class(
                        plugin_config,
                        orc_argument.orc_paths,
                        plugin_timeline_path,
                        hostname,
                        tmp_dir.name,
                        lock,
                    ),
                )

    return plugin_classes_list


def _run_plugin(
    plugin: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
    return plugin.add_to_timeline()


class OrcArgument:
    """Define all the needed parameters to process ORC and create timeline."""

    def __init__(self, hostname: str = "", output_path: Path = Path(), orc_paths: list[Path] | None = None) -> None:
        """Construct."""
        self.hostname = hostname
        self.output_path = output_path
        if orc_paths is None:
            self.orc_paths = []
        else:
            self.orc_paths = orc_paths


def process(file_list: list[Path], output_path: str, hostname: str, jobs: int) -> int:
    """Create a timeline for one host.

    Create timeline in output_path file from Orc given in file_list
    for a specific host (hostname), jobs variable is used to indicate
    how many threads can be used.
    """
    orc_argument = OrcArgument(orc_paths=file_list, hostname=hostname, output_path=Path(output_path))
    return _process_inner(orc_argument, jobs)


def _process_inner(orc_argument: OrcArgument, jobs: int) -> int:
    """Create timeline from OrcArgument object with "jobs" threads."""
    logging.info("Processing files for host: %s", orc_argument.hostname)
    lock = None
    if jobs > 1:
        lock = multiprocessing.Manager().Lock()
    temp_directory_parent = os.environ.get("TMPDIR")
    tmp_dir = tempfile.TemporaryDirectory(dir=temp_directory_parent, prefix="Orc2TimelineTempDir_")
    orc_arguments = [orc_argument]
    plugin_classes_list = _load_plugins(Config(), orc_arguments, tmp_dir, lock)

    # all_results is a list of tuple(host, plugin_name, number_of_events) that is later used to print final summary
    all_results = []
    if jobs <= 1:
        all_results.extend(
            [
                (
                    orc_argument.hostname,
                    plugin.__class__.__name__,
                    _run_plugin(plugin),
                )
                for plugin in plugin_classes_list
            ],
        )
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
            # store parallel plugin execution results
            futures = [pool.submit(_run_plugin, plugin) for plugin in plugin_classes_list]
            concurrent.futures.wait(futures)
            futures_results = [future.result() for future in futures]
            # loop to match plugin results to initial parameters
            for plugin, res in zip(plugin_classes_list, futures_results):
                all_results.append((orc_argument.hostname, plugin.__class__.__name__, res))

    total_result = _merge_timelines_for_host(orc_argument.hostname, str(orc_argument.output_path), tmp_dir)
    total_results_per_host = {orc_argument.hostname: total_result}

    _print_summaries(total_results_per_host, all_results)

    return total_result


def process_dir(orc_arguments: list[OrcArgument], jobs: int) -> int:
    """Process all plugins for all hosts."""
    lock = None
    if jobs > 1:
        lock = multiprocessing.Manager().Lock()

    temp_directory_parent = os.environ.get("TMPDIR")
    tmp_dir = tempfile.TemporaryDirectory(dir=temp_directory_parent, prefix="Orc2TimelineTempDir_")
    plugin_classes_list = _load_plugins(Config(), orc_arguments, tmp_dir, lock)

    _check_orc_list_and_print_intro(orc_arguments)

    # all_results is a list of tuple(host, plugin_name, number_of_events) that is later used to print final summary
    all_results = []
    if jobs <= 1:
        all_results.extend(
            [
                (
                    plugin.hostname,
                    plugin.__class__.__name__,
                    _run_plugin(plugin),
                )
                for plugin in plugin_classes_list
            ],
        )
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
            # store parallel plugin execution results
            futures = []
            index_list = []
            for plugin in plugin_classes_list:
                # need to keep trace of argument to make it match with results later
                index_list.append((plugin.hostname, plugin.__class__.__name__))
                futures.append(
                    pool.submit(_run_plugin, plugin),
                )

            concurrent.futures.wait(futures)
            future_results = [future.result() for future in futures]
            # building all_results by using simultanueously index_list and plugin results (futures)
            for index_num, index_tup in enumerate(index_list):
                hostname = index_tup[0]
                plugin = index_tup[1]
                all_results.append((hostname, plugin, future_results[index_num]))

    total_results = 0
    # dictionnary total_results_per_host[hostname] = total_number_of_events_for_this_host
    total_results_per_host = _merge_timelines_with_jobs(orc_arguments, jobs, tmp_dir)
    total_results = sum(total_results_per_host.values())

    _print_summaries(total_results_per_host, all_results)

    return total_results


def _get_all_results_filtered_by_host(all_results: list[tuple[str, str, int]], host: str) -> list[tuple[str, str, int]]:
    """Return sublist of all_results where first element of tuple (hostname) match given host."""
    return [result for result in all_results if host == result[0]]


def _get_all_results_filtered_by_plugin(
    all_results: list[tuple[str, str, int]],
    plugin: str,
) -> list[tuple[str, str, int]]:
    """Return sublist of all_results where second element of tuple (hostname) match given host."""
    return [result for result in all_results if plugin == result[1]]


def _check_orc_list_and_print_intro(orc_arguments: list[OrcArgument]) -> None:
    """Verify that there is no duplicates in given orc_arguments (stops the program if there is) and print intro."""
    host_list = [orc_argument.hostname for orc_argument in orc_arguments]
    if not _is_list_uniq(host_list):
        dupes = _get_duplicate_values_from_list(host_list)
        logging.critical("Unable to process directory if the same host is used many times.")
        logging.critical("Hint, these hosts seem to be the source of the problem : %s", dupes)
        sys.exit(2)

    _print_intro(orc_arguments)


def _print_intro(orc_arguments: list[OrcArgument]) -> None:
    """Print simple intro that sums up the files that will be used to generate timelines."""
    for orc_argument in orc_arguments:
        logging.info("==============================================")
        logging.info("Host: %s", orc_argument.hostname)
        logging.info("Files used: [%s]", ", ".join(str(path) for path in orc_argument.orc_paths))
        logging.info("Result file: %s", orc_argument.output_path)


def _print_summaries(total_results_per_host: dict[str, int], all_results: list[tuple[str, str, int]]) -> None:
    """Print summaries for every treated Orc at the end of the program execution.

    Parameters
    ----------
    total_results_per_host: dict[str, int]
        Dictionary with hostname as key and total_events_for_this_host (after deduplication) as value
    all_results: list[tuple[str, str, int]]
        List of tuple (hostname, plugin_name, events_number)

    """
    logging.info("== Printing final summary of generated timelines:")
    host_list = sorted(set(total_results_per_host.keys()))
    for host in host_list:
        logging.info(
            "=======================================================================",
        )
        logging.info("====== Hostname: %s - %s events", host, total_results_per_host[host])
        results_filtered_by_host = _get_all_results_filtered_by_host(all_results, host)
        plugin_list = sorted({plugin[1] for plugin in results_filtered_by_host})
        for plugin in plugin_list:
            results_filtered_by_plugin = _get_all_results_filtered_by_plugin(results_filtered_by_host, plugin)
            sum_for_plugin = sum([int(plugin[2]) for plugin in results_filtered_by_plugin])
            # for plugin in results_filtered_by_host:
            logging.info("========== %s %s %s", host, plugin, sum_for_plugin)
        logging.info("====== Total for %s: %s", host, total_results_per_host[host])

    logging.info(
        "=======================================================================",
    )
    logging.info("====== Total: %s events processed", sum(total_results_per_host.values()))
    logging.info(
        "=======================================================================",
    )


def _merge_timelines_with_jobs(
    orc_arguments: list[OrcArgument],
    jobs: int,
    tmp_dir: tempfile.TemporaryDirectory[str],
) -> dict[str, int]:
    """Create final timeline for every host by merging subtimelines.

    For a list of OrcArgument, for every host, this function will merge all
    the subtimelines that were generated by the execution of the plugins
    and create the final timeline.
    """
    result_list = []

    if jobs <= 1:
        result_list = [
            _merge_timelines_for_host(orc_argument.hostname, str(orc_argument.output_path), tmp_dir)
            for orc_argument in orc_arguments
        ]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = [
                pool.submit(_merge_timelines_for_host, orc_argument.hostname, str(orc_argument.output_path), tmp_dir)
                for orc_argument in orc_arguments
            ]
            concurrent.futures.wait(futures)
            result_list = [future.result() for future in futures]

    # return value is a dictionnary with hostname as key
    # and number of events for this host as value dict_res : dict{str, int}
    return dict(zip([orc_argument.hostname for orc_argument in orc_arguments], result_list))
