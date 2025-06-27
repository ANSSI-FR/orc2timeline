"""Test for command line interface."""

from __future__ import annotations

import gzip
import hashlib
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner

from orc2timeline import __version__, entrypoint


def _zcat_and_sha1(file: str) -> str:
    buf_size = 65536
    with gzip.open(file, "rb") as fd:
        my_sha1 = hashlib.sha1()  # noqa: S324
        while True:
            data = fd.read(buf_size)
            if not data:
                break
            my_sha1.update(data)

    return str(my_sha1.hexdigest())


def _run_process(args: list[str]) -> tuple[str, str, int]:
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    code = process.returncode
    return out.decode("utf"), err.decode("utf"), code


def test_cli_version() -> None:
    """Test if the command line interface is installed correctly."""
    ver = f"version {__version__}"
    out = subprocess.check_output(
        (
            "orc2timeline",
            "--version",
        ),
        text=True,
        shell=False,
    )
    assert ver in out
    out = subprocess.check_output(
        (
            sys.executable,
            "-m",
            "orc2timeline",
            "--version",
        ),
        text=True,
        shell=False,
    )
    assert ver in out
    runner = CliRunner()
    result = runner.invoke(entrypoint, ["--version"])
    out = result.output
    assert ver in out


def test_import() -> None:
    """Test if module entrypoint has correct imports."""
    import orc2timeline.__main__  # noqa: F401, PLC0415


def test_dir_input_dir_is_a_file() -> None:
    """Test is error a properly triggered when a file is given instead of the input dir."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z",
            "tests/output/",
        ],
    )

    assert (
        "Invalid value for 'INPUT_DIR': Directory "
        "'tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z' is a file." in err
    )


def test_dir_output_dir_is_a_file() -> None:
    """Test is error a properly triggered when a file is given instead of the output dir."""
    Path("tests/output/file_instead_of_dir").touch()
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "tests/data/conf_7_archives/",
            "tests/output/file_instead_of_dir",
        ],
    )

    Path("tests/output/file_instead_of_dir").unlink()

    assert "Invalid value for 'OUTPUT_DIR': Directory 'tests/output/file_instead_of_dir' is a file." in err


def test_dir_no_job() -> None:
    """Test if processing directory with 1 job works correctly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    assert "== Printing final summary of generated timelines:" in err
    assert "====== Hostname: FAKEMACHINE - 6930 events" in err
    assert "========== FAKEMACHINE RegistryToTimeline 5117" in err
    assert "========== FAKEMACHINE EventLogsToTimeline 125" in err
    assert "========== FAKEMACHINE NTFSInfoToTimeline 413" in err
    assert "========== FAKEMACHINE USNInfoToTimeline 99" in err
    assert "========== FAKEMACHINE I30InfoToTimeline 54" in err
    assert "========== FAKEMACHINE FirefoxHistoryToTimeline 13" in err
    assert "========== FAKEMACHINE RecycleBinToTimeline 1" in err
    assert "========== FAKEMACHINE UserAssistToTimeline 25" in err
    assert "========== FAKEMACHINE AmCacheToTimeline 2086" in err
    assert "====== Total for FAKEMACHINE: 6930" in err
    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "96d3be2880956f647e28825cea80ff0d8a077234"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()

    for f in Path("tests/output").glob("**"):
        if f.is_file():
            f.unlink()


def test_dir_1_jobs() -> None:
    """Test if processing directory with 1 job works correctly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "-j 1",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    assert "== Printing final summary of generated timelines:" in err
    assert "====== Hostname: FAKEMACHINE - 6930 events" in err
    assert "========== FAKEMACHINE RegistryToTimeline 5117" in err
    assert "========== FAKEMACHINE EventLogsToTimeline 125" in err
    assert "========== FAKEMACHINE NTFSInfoToTimeline 413" in err
    assert "========== FAKEMACHINE USNInfoToTimeline 99" in err
    assert "========== FAKEMACHINE I30InfoToTimeline 54" in err
    assert "========== FAKEMACHINE FirefoxHistoryToTimeline 13" in err
    assert "========== FAKEMACHINE RecycleBinToTimeline 1" in err
    assert "========== FAKEMACHINE UserAssistToTimeline 25" in err
    assert "========== FAKEMACHINE AmCacheToTimeline 2086" in err
    assert "====== Total for FAKEMACHINE: 6930" in err
    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "96d3be2880956f647e28825cea80ff0d8a077234"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()

    for f in Path("tests/output").glob("**"):
        if f.is_file():
            f.unlink()


def test_dir_5_jobs() -> None:
    """Test if processing directory with 5 jobs works correctly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "-j 5",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    assert "== Printing final summary of generated timelines:" in err
    assert "====== Hostname: FAKEMACHINE - 6930 events" in err
    assert "========== FAKEMACHINE RegistryToTimeline 5117" in err
    assert "========== FAKEMACHINE EventLogsToTimeline 125" in err
    assert "========== FAKEMACHINE NTFSInfoToTimeline 413" in err
    assert "========== FAKEMACHINE USNInfoToTimeline 99" in err
    assert "========== FAKEMACHINE I30InfoToTimeline 54" in err
    assert "========== FAKEMACHINE FirefoxHistoryToTimeline 13" in err
    assert "========== FAKEMACHINE RecycleBinToTimeline 1" in err
    assert "========== FAKEMACHINE UserAssistToTimeline 25" in err
    assert "========== FAKEMACHINE AmCacheToTimeline 2086" in err
    assert "====== Total for FAKEMACHINE: 6930" in err
    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "96d3be2880956f647e28825cea80ff0d8a077234"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()

    for f in Path("tests/output").glob("**"):
        if f.is_file():
            f.unlink()


def test_dir_twice_same_hostname() -> None:
    """Test if error is properly triggered when two Orc with the same hostname are in input directory."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "tests/data/",
            "tests/output/",
        ],
    )

    assert "CRITICAL - Unable to process directory if the same host is used many times." in err
    assert "CRITICAL - Hint, these hosts seem to be the source of the problem : {'FAKEMACHINE'}" in err


def test_dir_output_file_already_exists() -> None:
    """Test if the error meggase is displayed when process_dir is called for result file that already exists."""
    Path("tests/output/FAKEMACHINE.csv.gz").touch()
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    assert (
        "Output file 'tests/output/FAKEMACHINE.csv.gz' already exists, processing"
        " will be ignored for host FAKEMACHINE use '--overwrite' if you know what you are doing." in err
    )
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()


def test_simple_5_jobs() -> None:
    """Test if processing the test ORCs with 5 jobs works correctly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process",
            "--overwrite",
            "-j 5",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Detail.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Little.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_SAM.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Browsers.7z",
            "tests/output/FAKEMACHINE.csv.gz",
        ],
    )

    assert "== Printing final summary of generated timelines:" in err
    assert "====== Hostname: FAKEMACHINE - 6930 events" in err
    assert "========== FAKEMACHINE RegistryToTimeline 5117" in err
    assert "========== FAKEMACHINE EventLogsToTimeline 125" in err
    assert "========== FAKEMACHINE NTFSInfoToTimeline 413" in err
    assert "========== FAKEMACHINE USNInfoToTimeline 99" in err
    assert "========== FAKEMACHINE I30InfoToTimeline 54" in err
    assert "========== FAKEMACHINE FirefoxHistoryToTimeline 13" in err
    assert "========== FAKEMACHINE RecycleBinToTimeline 1" in err
    assert "========== FAKEMACHINE UserAssistToTimeline 25" in err
    assert "========== FAKEMACHINE AmCacheToTimeline 2086" in err
    assert "====== Total for FAKEMACHINE: 6930" in err
    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "96d3be2880956f647e28825cea80ff0d8a077234"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()


def test_simple_1_job() -> None:
    """Test if processing the test ORCs with 1 job works correctly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process",
            "--overwrite",
            "-j 1",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Detail.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Little.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_SAM.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Browsers.7z",
            "tests/output/FAKEMACHINE.csv.gz",
        ],
    )

    assert "== Printing final summary of generated timelines:" in err
    assert "====== Hostname: FAKEMACHINE - 6930 events" in err
    assert "========== FAKEMACHINE RegistryToTimeline 5117" in err
    assert "========== FAKEMACHINE EventLogsToTimeline 125" in err
    assert "========== FAKEMACHINE NTFSInfoToTimeline 413" in err
    assert "========== FAKEMACHINE USNInfoToTimeline 99" in err
    assert "========== FAKEMACHINE I30InfoToTimeline 54" in err
    assert "========== FAKEMACHINE FirefoxHistoryToTimeline 13" in err
    assert "========== FAKEMACHINE RecycleBinToTimeline 1" in err
    assert "========== FAKEMACHINE UserAssistToTimeline 25" in err
    assert "========== FAKEMACHINE AmCacheToTimeline 2086" in err
    assert "====== Total for FAKEMACHINE: 6930" in err
    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "96d3be2880956f647e28825cea80ff0d8a077234"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()


def test_simple_no_job() -> None:
    """Test if processing the test ORCs with 1 job works correctly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process",
            "--overwrite",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Detail.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Little.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_SAM.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Browsers.7z",
            "tests/output/FAKEMACHINE.csv.gz",
        ],
    )

    assert "== Printing final summary of generated timelines:" in err
    assert "====== Hostname: FAKEMACHINE - 6930 events" in err
    assert "========== FAKEMACHINE RegistryToTimeline 5117" in err
    assert "========== FAKEMACHINE EventLogsToTimeline 125" in err
    assert "========== FAKEMACHINE NTFSInfoToTimeline 413" in err
    assert "========== FAKEMACHINE USNInfoToTimeline 99" in err
    assert "========== FAKEMACHINE I30InfoToTimeline 54" in err
    assert "========== FAKEMACHINE FirefoxHistoryToTimeline 13" in err
    assert "========== FAKEMACHINE RecycleBinToTimeline 1" in err
    assert "========== FAKEMACHINE UserAssistToTimeline 25" in err
    assert "========== FAKEMACHINE AmCacheToTimeline 2086" in err
    assert "====== Total for FAKEMACHINE: 6930" in err
    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "96d3be2880956f647e28825cea80ff0d8a077234"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()


def test_simple_log_file() -> None:
    """Test if processing the test ORCs with 1 job works correctly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "--log-file",
            "tests/output/blabla.log",
            "process",
            "--overwrite",
            "-j 1",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Detail.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Little.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_SAM.7z",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Browsers.7z",
            "tests/output/FAKEMACHINE.csv.gz",
        ],
    )

    if Path("tests/output/blabla.log").exists():
        with Path("tests/output/blabla.log").open("r") as f:
            data = f.read()
            assert "== Printing final summary of generated timelines:" in data
            assert "====== Hostname: FAKEMACHINE - 6930 events" in data
            assert "========== FAKEMACHINE RegistryToTimeline 5117" in data
            assert "========== FAKEMACHINE EventLogsToTimeline 125" in data
            assert "========== FAKEMACHINE NTFSInfoToTimeline 413" in data
            assert "========== FAKEMACHINE USNInfoToTimeline 99" in data
            assert "========== FAKEMACHINE I30InfoToTimeline 54" in data
            assert "========== FAKEMACHINE FirefoxHistoryToTimeline 13" in data
            assert "========== FAKEMACHINE RecycleBinToTimeline 1" in data
            assert "========== FAKEMACHINE UserAssistToTimeline 25" in data
            assert "========== FAKEMACHINE AmCacheToTimeline 2086" in data
            assert "====== Total for FAKEMACHINE: 6930" in data

    Path("tests/output/FAKEMACHINE.csv.gz").unlink()
    Path("tests/output/blabla.log").unlink()


def test_simple_input_file_doesnt_exist() -> None:
    """Test if the error is triggered when orc2timeline is used with wrong parameters."""
    out, err, code = _run_process(
        ["orc2timeline", "process", "tests/data/DOES_NOT_EXIST", "tests/output/FAKEMACHINE.csv.gz"],
    )

    assert "Error: Invalid value for '[FILE_LIST]...': File 'tests/data/DOES_NOT_EXIST' does not exist." in err


def test_simple_output_file_already_exists() -> None:
    """Test if the error is triggered when orc2timeline is used with wrong parameters."""
    Path("tests/output/FAKEMACHINE.csv.gz").touch()
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z",
            "tests/output/FAKEMACHINE.csv.gz",
        ],
    )

    assert (
        "Error: Invalid value: 'OUTPUT_PATH': File 'tests/output/FAKEMACHINE.csv.gz' already exists, use '--overwrite' if you know what you are doing."  # noqa: E501
        in err
    )
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()


def test_simple_output_dir_does_not_exist() -> None:
    """Test if the error is triggered when orc2timeline is used with wrong parameters."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "process",
            "tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z",
            "tests/DOES_NOT_EXIST/FAKEMACHINE.csv.gz",
        ],
    )

    assert (
        "Error: Invalid value: 'OUTPUT_PATH': Directory 'tests/DOES_NOT_EXIST' does not exist or is not a directory."
        in err
    )


def test_show_conf() -> None:
    """Test if show_conf works properly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "show_conf",
        ],
    )


def test_show_conf_file() -> None:
    """Test if show_conf_file works properly."""
    out, err, code = _run_process(
        [
            "orc2timeline",
            "show_conf_file",
        ],
    )
