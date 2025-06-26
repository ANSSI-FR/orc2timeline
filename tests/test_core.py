"""Test core module."""

import gzip
import hashlib
from pathlib import Path

from orc2timeline import process


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


def test_process_1_job() -> None:
    """Test import mode with 1 job."""
    file_list = [
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Detail.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Little.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_SAM.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Browsers.7z"),
    ]

    if Path("tests/output/FAKEMACHINE.csv.gz").exists():
        Path("tests/output/FAKEMACHINE.csv.gz").unlink()

    process(file_list, "tests/output/FAKEMACHINE.csv.gz", "FAKEMACHINE", 1)

    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "c485ca85a5c13661eaebacc2829e413eaa95ab3a"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()


def test_process_5_jobs() -> None:
    """Test import mode with 5 jobs."""
    file_list = [
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_General.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Detail.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Little.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_SAM.7z"),
        Path("tests/data/conf_7_archives/ORC_Server_FAKEMACHINE_Browsers.7z"),
    ]

    if Path("tests/output/FAKEMACHINE.csv.gz").exists():
        Path("tests/output/FAKEMACHINE.csv.gz").unlink()

    process(file_list, "tests/output/FAKEMACHINE.csv.gz", "FAKEMACHINE", 5)

    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "c485ca85a5c13661eaebacc2829e413eaa95ab3a"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()


def test_null_in_csv_files() -> None:
    """Test import mode with 1 job."""
    file_list = [
        Path("tests/data/null_csv/ORC_Server_FAKEMACHINE_General.7z"),
        Path("tests/data/null_csv/ORC_Server_FAKEMACHINE_Detail.7z"),
        Path("tests/data/null_csv/ORC_Server_FAKEMACHINE_Little.7z"),
        Path("tests/data/null_csv/ORC_Server_FAKEMACHINE_SAM.7z"),
        Path("tests/data/null_csv/ORC_Server_FAKEMACHINE_Browsers.7z"),
    ]

    if Path("tests/output/FAKEMACHINE.csv.gz").exists():
        Path("tests/output/FAKEMACHINE.csv.gz").unlink()

    process(file_list, "tests/output/FAKEMACHINE.csv.gz", "FAKEMACHINE", 1)

    assert _zcat_and_sha1("tests/output/FAKEMACHINE.csv.gz") == "c485ca85a5c13661eaebacc2829e413eaa95ab3a"
    Path("tests/output/FAKEMACHINE.csv.gz").unlink()
