"""Plugin to parse hives."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from threading import Lock

    from orc2timeline.config import PluginConfig

from dfwinreg import definitions as dfwinreg_definition
from dfwinreg import regf as dfwinreg_regf
from dfwinreg import registry as dfwinreg_registry

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline

Type = {}
Type[0x0001] = "RegSZ"
Type[0x0002] = "RegExpandSZ"
Type[0x0003] = "RegBin"
Type[0x0004] = "RegDWord"
Type[0x0007] = "RegMultiSZ"
Type[0x000B] = "RegQWord"
Type[0x0000] = "RegNone"
Type[0x0005] = "RegBigEndian"
Type[0x0006] = "RegLink"
Type[0x0008] = "RegResourceList"
Type[0x0009] = "RegFullResourceDescriptor"
Type[0x000A] = "RegResourceRequirementsList"
Type[0x0010] = "RegFileTime"


def _decode_utf16le(s: bytes) -> str:
    if b"\x00\x00" in s:
        index = s.index(b"\x00\x00")
        if index > 2:  # noqa: PLR2004
            if s[index - 2] != b"\x00"[0]:  # py2+3 # noqa: SIM108
                #  61 00 62 00 63 64 00 00
                #                    ^  ^-- end of string
                #                    +-- index
                s = s[: index + 2]
            else:
                #  61 00 62 00 63 00 00 00
                #                 ^     ^-- end of string
                #                 +-- index
                s = s[: index + 3]
    if (len(s) % 2) != 0:
        s = s + b"\x00"
    res = s.decode("utf16", errors="ignore")
    return res.partition("\x00")[0]


def _readable_multi_sz(value: bytes) -> str:
    new_value = value[:-4]
    res = ""
    for word in new_value.split(b"\x00\x00\x00"):
        res += _decode_utf16le(word)
        res += "|"

    return res[:-1]


def _readable_reg_value(value: dfwinreg_regf.REGFWinRegistryValue) -> bytes | str:
    simple_types = {dfwinreg_definition.REG_EXPAND_SZ, dfwinreg_definition.REG_SZ, dfwinreg_definition.REG_LINK}
    if value.data_type in simple_types:
        return _decode_utf16le(value.data)
    if value.data_type == dfwinreg_definition.REG_MULTI_SZ:
        return _readable_multi_sz(value.data)

    return bytes(value.data)


class RegistryToTimeline(GenericToTimeline):
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

        self.file_header = bytes([0x72, 0x65, 0x67, 0x66])

        self.importantKeysFile = Path(Path(__file__).parent) / "RegistryToTimeline-important-keys.txt"
        self.importantKeys = self._parse_important_keys_file(self.importantKeysFile)

    def _parse_important_keys_file(self, file_path: Path) -> list[str]:
        result = []
        if file_path.exists():
            with Path(file_path).open() as f:
                for line in f:
                    my_line = line.strip()
                    if my_line.startswith("#") or len(my_line) == 0:
                        continue

                    result.append(my_line)
        return result

    def _print_only_key(self, key: dfwinreg_regf.REGFWinRegistryValue, artefact: Path) -> None:
        try:
            event = Event(
                timestamp_str=key.last_written_time.CopyToDateTimeString()[:-4],
                source=self._get_original_path(artefact),
                description=str(key.path),
            )
            self._add_event(event)
        except Exception as e:  # noqa: BLE001
            key_path = "Unknown"
            if key_path:
                key_path = key.path
            self.logger.critical("Unable to print key %s from %s. Error: %s", key_path, artefact, e)

    def _print_all_keyvalues(self, key: dfwinreg_regf.REGFWinRegistryValue, artefact: Path) -> None:
        for value in key.GetValues():
            readable_type = Type[value.data_type]
            readable_data = _readable_reg_value(value)
            event = Event(
                timestamp_str=key.last_written_time.CopyToDateTimeString()[:-4],
                source=self._get_original_path(artefact),
                description=(
                    f"KeyPath: {key.path} - ValueName: {value.name} - "
                    f"ValueType: {readable_type} - ValueData: {readable_data!s}"
                ),
            )
            self._add_event(event)

    def _parse_key(self, key: dfwinreg_regf.REGFWinRegistryValue, artefact: Path) -> None:
        if key is not None:
            self._print_only_key(key, artefact)
            if key.path in self.importantKeys:
                self._print_all_keyvalues(key, artefact)

            for subkey_index in range(key.number_of_subkeys):
                try:
                    subkey = key.GetSubkeyByIndex(subkey_index)
                    self._parse_key(subkey, artefact)
                except OSError as e:
                    self.logger.debug("Error while parsing registry keys: %s", e)

    def _parse_artefact(self, artefact: Path) -> None:
        with Path(artefact).open("rb") as f:
            try:
                reg_file = dfwinreg_regf.REGFWinRegistryFile(emulate_virtual_keys=False)
                reg_file.Open(f)
                win_registry = dfwinreg_registry.WinRegistry()
                key_path_prefix = win_registry.GetRegistryFileMapping(reg_file)
                reg_file.SetKeyPathPrefix(key_path_prefix)
                root_key = reg_file.GetRootKey()
                self._parse_key(root_key, artefact)
            except Exception as e:  # noqa: BLE001
                self.logger.warning(
                    "Error while parsing %s: %s",
                    Path(artefact).name,
                    e,
                )
