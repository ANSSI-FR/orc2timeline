"""Test config parser."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_process(args: list[str]) -> tuple[str, str, int]:
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    code = process.returncode
    return out.decode("utf"), err.decode("utf"), code


def _get_conf_file_path() -> Path:
    out, err, code = _run_process(
        [
            "orc2timeline",
            "show_conf_file",
        ],
    )

    file_path = out.splitlines()[-1]
    return Path(file_path)


def test_conf_file_do_not_exist() -> None:
    """Test config parsing when file does not exist."""
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path_bak.rename(str(conf_file_path))

    assert "Cannot read configuration file" in err
    assert "(file does not exist)" in err


def test_conf_file_is_a_dir() -> None:
    """Test config parsing when configuration is in fact a directory."""
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    conf_file_path.mkdir()

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.rmdir()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "Cannot read configuration file" in err
    assert "(is not a file)" in err


def test_conf_file_wrong_yaml() -> None:
    """Test config when yaml parsing goes wrong."""
    content = '''Plugins:
  - RegistryToTimeline:
  archives: ["SAM", "Little", "Detail", "Offline"]
      sub_archives: ["SAM.7z", "SystemHives_little.7z", "UserHives.7z", "SystemHives.7z"]
      match_pattern: ".*data$"
      sourcetype: "Registry"'''
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    with conf_file_path.open("w") as conf_file:
        conf_file.write(content)

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.unlink()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "An error occured while parsing configuration" in err


def test_conf_file_empty_archive() -> None:
    """Test configuration parsing when archive is empty."""
    content = '''Plugins:
  - RegistryToTimeline:
      archives: []
      sub_archives: ["SAM.7z", "SystemHives_little.7z", "UserHives.7z", "SystemHives.7z"]
      match_pattern: ".*data$"
      sourcetype: "Registry"'''
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    with conf_file_path.open("w") as conf_file:
        conf_file.write(content)

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.unlink()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "configuration describes plugin without any archive." in err


def test_conf_file_sub_archives_empty() -> None:
    """Test configuration parsing when sub_archive is empty."""
    content = '''Plugins:
  - RegistryToTimeline:
      archives: ["SAM", "Little", "Detail", "Offline"]
      sub_archives: []
      match_pattern: ".*data$"
      sourcetype: "Registry"'''
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    with conf_file_path.open("w") as conf_file:
        conf_file.write(content)

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.unlink()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "FAKEMACHINE RegistryToTimeline 0" in err


def test_conf_file_empty_plugin_name() -> None:
    """Test configuration when plugin name is empty."""
    content = '''Plugins:
  - "":
      archives: ["SAM", "Little", "Detail", "Offline"]
      sub_archives: ["SAM.7z", "SystemHives_little.7z", "UserHives.7z", "SystemHives.7z"]
      match_pattern: ".*data$"
      sourcetype: "Registry"'''
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    with conf_file_path.open("w") as conf_file:
        conf_file.write(content)

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.unlink()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "Empty plugin name in configuration is not allowed." in err


def test_conf_file_fake_plugin() -> None:
    """Test configuration when plugin file does not exist."""
    content = '''Plugins:
  - "FAKEPLUGIN":
      archives: ["SAM", "Little", "Detail", "Offline"]
      sub_archives: ["SAM.7z", "SystemHives_little.7z", "UserHives.7z", "SystemHives.7z"]
      match_pattern: ".*data$"
      sourcetype: "Registry"'''
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    with conf_file_path.open("w") as conf_file:
        conf_file.write(content)

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.unlink()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "Plugin FAKEPLUGIN:" in err
    assert "orc2timeline/plugins/FAKEPLUGIN.py does not exist." in err


def test_conf_file_empty_sourcetype() -> None:
    """Test error in."""
    content = '''Plugins:
  - RegistryToTimeline:
      archives: ["SAM", "Little", "Detail", "Offline"]
      sub_archives: ["SAM.7z", "SystemHives_little.7z", "UserHives.7z", "SystemHives.7z"]
      match_pattern: ".*data$"
      sourcetype: ""'''
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    with conf_file_path.open("w") as conf_file:
        conf_file.write(content)

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.unlink()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "empty sourcetype is not allowed." in err


def test_conf_file_empty_match_pattern() -> None:
    """Test configuration when match_pattern is empty."""
    content = '''Plugins:
  - RegistryToTimeline:
      archives: ["SAM", "Little", "Detail", "Offline"]
      sub_archives: ["SAM.7z", "SystemHives_little.7z", "UserHives.7z", "SystemHives.7z"]
      match_pattern: ""
      sourcetype: "Registry"'''
    file_path = _get_conf_file_path()
    conf_file_path = Path(file_path)
    conf_file_path_bak = Path(file_path).parent / "Orc2Timeline.yaml.bak"
    conf_file_path.rename(str(conf_file_path_bak))
    with conf_file_path.open("w") as conf_file:
        conf_file.write(content)

    out, err, code = _run_process(
        [
            "orc2timeline",
            "process_dir",
            "--overwrite",
            "tests/data/conf_7_archives/",
            "tests/output/",
        ],
    )

    conf_file_path.unlink()
    conf_file_path_bak.rename(str(conf_file_path))

    assert "empty match_pattern is not allowed." in err
