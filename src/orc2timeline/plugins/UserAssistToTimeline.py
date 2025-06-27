"""Plugin to decode unformation from UserAssist registry keys."""

from __future__ import annotations

import codecs
import struct
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytz
from dfwinreg import regf as dfwinreg_regf
from dfwinreg import registry as dfwinreg_registry

if TYPE_CHECKING:
    from pathlib import Path
    from threading import Lock

    from orc2timeline.config import PluginConfig

from orc2timeline.plugins.GenericToTimeline import Event
from orc2timeline.plugins.RegistryToTimeline import RegistryToTimeline

GUID_to_path = {}
GUID_to_path["{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"] = r"C:\Windows\System32"
GUID_to_path["{6D809377-6AF0-444B-8957-A3773F02200E}"] = r"C:\Program Files"
GUID_to_path["{7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E}"] = r"C:\Program Files (x86)"
GUID_to_path["{F38BF404-1D43-42F2-9305-67DE0B28FC23}"] = r"C:\Windows"
GUID_to_path["{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}"] = r"C:\ProgramData\Microsoft\Windows \Start Menu\Programs"
GUID_to_path["{9E3995AB-1F9C-4F13-B827-48B24B6C7174}"] = (
    r"%AppData%\Roaming\Microsoft\Internet Explorer\Quick Launch\User Pinned"
)
GUID_to_path["{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}"] = r"%AppData%\Roaming\Microsoft\Windows \Start Menu\Programs"
GUID_to_path["{D65231B0-B2F1-4857-A4CE-A8E7C6EA7D27}"] = r"C:\Windows\SysWOW64"


class UserAssistToTimeline(RegistryToTimeline):
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

    def _parse_key_values(self, key: Any, artefact: Path) -> None:  # noqa: ANN401
        for value in key.GetValues():
            reg_time = key.last_written_time.CopyToDateTimeString()[:-4]
            exec_path = codecs.encode(value.name, "rot_13")
            if exec_path[0:8] == "UEME_CTL":
                continue
            path_prefix = exec_path.split("\\")[0]
            if path_prefix in GUID_to_path:
                exec_path = exec_path.replace(path_prefix, GUID_to_path[path_prefix])
            # Recent versions
            if len(value.data) == 72:  # noqa: PLR2004
                run_count = struct.unpack("I", value.data[4:8])[0]
                focus_time = struct.unpack("I", value.data[12:16])[0]
                last_run = struct.unpack("Q", value.data[60:68])[0]
                last_run = (last_run - 116444736000000000) // 10
                last_run_time = datetime(1970, 1, 1, tzinfo=pytz.UTC) + timedelta(microseconds=last_run)

                event = Event(
                    timestamp_str=last_run_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    source=self.originalPath[artefact.name],
                )
                event.description = (
                    f"ExecPath: {exec_path} - RunCount: {run_count} - "
                    f"FocusTime: {focus_time} - RegistryTimestamp: {reg_time}"
                )
                self._add_event(event)

            # Old versions: XP and Vista
            elif len(value.data) == 16:  # noqa: PLR2004
                run_count = struct.unpack("I", value.data[4:8])[0] - 5
                last_run = struct.unpack("Q", value.data[8:16])[0]
                last_run = (last_run - 116444736000000000) // 10
                last_run_time = datetime(1970, 1, 1, tzinfo=pytz.UTC) + timedelta(microseconds=last_run)

                event = Event(
                    timestamp_str=last_run_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    source=self.originalPath[artefact.name],
                )
                event.description = f"ExecPath: {exec_path} - RunCount: {run_count} - RegistryTimestamp: {reg_time}"
                self._add_event(event)

    def _parse_key(self, key: Any, artefact: Path) -> None:  # noqa: ANN401
        if key is not None:
            if key.path.split("\\")[-1] == "Count":
                self._parse_key_values(key, artefact)
            for subkey_index in range(key.number_of_subkeys):
                try:
                    subkey = key.GetSubkeyByIndex(subkey_index)
                    self._parse_key(subkey, artefact)
                except OSError as e:
                    self.logger.critical("Error while parsing registry keys : %s", e)

    def _parse_artefact(self, artefact: Path) -> None:
        with artefact.open("rb") as f:
            try:
                reg_file = dfwinreg_regf.REGFWinRegistryFile(emulate_virtual_keys=False)
                reg_file.Open(f)
                win_registry = dfwinreg_registry.WinRegistry()
                key_path_prefix = win_registry.GetRegistryFileMapping(reg_file)
                reg_file.SetKeyPathPrefix(key_path_prefix)
                ze_key = reg_file.GetKeyByPath(
                    "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist",
                )
                self._parse_key(ze_key, artefact)
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Error while parsing %s : %s", artefact.name, e)
