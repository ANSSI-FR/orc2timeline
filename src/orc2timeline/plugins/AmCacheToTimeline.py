"""Plugin to parse AmCache Registry Hives."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from dfwinreg import regf as dfwinreg_regf
from dfwinreg import registry as dfwinreg_registry

if TYPE_CHECKING:
    from pathlib import Path
    from threading import Lock

    from orc2timeline.config import PluginConfig

from orc2timeline.plugins.GenericToTimeline import Event
from orc2timeline.plugins.RegistryToTimeline import RegistryToTimeline

EPOCH_AS_FILETIME = 116444736000000000
HUNDREDS_OF_NANOSECONDS = 10000000


class AmCacheToTimeline(RegistryToTimeline):
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

    def _parse_inventory_application_file(self, key: Any, artefact: Path) -> None:  # noqa: ANN401
        event = Event(
            timestamp_str=key.last_written_time.CopyToDateTimeString()[:-4],
            source=self.originalPath[artefact.name],
        )
        desc = [f"KeyPath: {key.path}"]
        filename = key.GetValueByName("Name")
        if filename:
            desc.append(f"Name: {filename.GetDataAsObject()}")
        path = key.GetValueByName("LowerCaseLongPath")
        if path:
            desc.append(f"ExecPath: {path.GetDataAsObject()}")
        file_id = key.GetValueByName("FileId")
        if file_id:
            desc.append(f"SHA1: {file_id.GetDataAsObject()[4:]}")
        file_size = key.GetValueByName("Size")
        if file_size:
            desc.append(f"FileSize: {file_size.GetDataAsObject()}")
        event.description = "Key last modified timestamp - " + " - ".join(desc)
        self._add_event(event)
        # check if there is a compilation date to add another line
        lnkdate = key.GetValueByName("LinkDate")
        if lnkdate:
            epoch_timestamp = datetime.strptime(
                lnkdate.GetDataAsObject(),
                "%m/%d/%Y %H:%M:%S",
            ).replace(tzinfo=timezone.utc)
            eventlnk = Event(
                timestamp=epoch_timestamp,
                source=self.originalPath[artefact.name],
            )
            eventlnk.description = "Compilation timestamp - " + " - ".join(desc)
            self._add_event(eventlnk)

    def _parse_inventory_driver_binary(self, key: Any, artefact: Path) -> None:  # noqa: ANN401
        event = Event(
            timestamp_str=key.last_written_time.CopyToDateTimeString()[:-4],
            source=self.originalPath[artefact.name],
        )
        desc = [f"KeyPath: {key.path}"]
        filename = key.GetValueByName("DriverName")
        if filename:
            desc.append(f"Name: {filename.GetDataAsObject()}")
        path = key.GetValueByName("LowerCaseLongPath")
        if path:
            desc.append(f"DriverPath: {path.GetDataAsObject()}")
        file_id = key.GetValueByName("DriverId")
        # sha1 can be either in one of the value or the name of the key
        if file_id:
            desc.append(f"SHA1: {file_id.GetDataAsObject()[4:]}")
        elif key.name.startswith("0000"):
            desc.append(f"SHA1: {key.name[4:]}")
        file_size = key.GetValueByName("ImageSize")
        if file_size:
            desc.append(f"FileSize: {file_size.GetDataAsObject()}")
        event.description = "Key last modified timestamp - " + " - ".join(desc)
        self._add_event(event)
        # check if there is a compilation date to add another line
        dlwt = key.GetValueByName("DriverLastWriteTime")
        if dlwt:
            eventlnk = Event(
                timestamp=datetime.strptime(dlwt.GetDataAsObject(), "%m/%d/%Y %H:%M:%S").replace(tzinfo=timezone.utc),
                source=self.originalPath[artefact.name],
            )
            eventlnk.description = "Driver Last Write time - " + " - ".join(desc)
            self._add_event(eventlnk)

    def _parse_file_key(self, key: Any, artefact: Path) -> None:  # noqa: ANN401
        event = Event(
            timestamp_str=key.last_written_time.CopyToDateTimeString()[:-4],
            source=self.originalPath[artefact.name],
        )
        desc = [f"KeyPath: {key.path}"]
        path = key.GetValueByName("15")
        if path:
            desc.append(f"ExecPath: {path.GetDataAsObject()}")
        file_id = key.GetValueByName("101")
        if file_id:
            desc.append(f"SHA1: {file_id.GetDataAsObject()[4:]}")
        file_size = key.GetValueByName("6")
        if file_size:
            desc.append(f"FileSize: {file_size.GetDataAsObject()}")
        event.description = "Key last modified timestamp - " + " - ".join(desc)
        self._add_event(event)
        # check if there is a modification date to add another line
        moddate = key.GetValueByName("17")
        if moddate:
            epoch_timestamp = (int(moddate.GetDataAsObject()) - EPOCH_AS_FILETIME) / HUNDREDS_OF_NANOSECONDS
            eventmod = Event(
                timestamp=datetime.fromtimestamp(epoch_timestamp, tz=timezone.utc),
                source=self.originalPath[artefact.name],
            )
            eventmod.description = "Modification time - " + " - ".join(desc)
            self._add_event(eventmod)
        # check if there is a creation date to add another line
        moddate = key.GetValueByName("12")
        if moddate:
            epoch_timestamp = (int(moddate.GetDataAsObject()) - EPOCH_AS_FILETIME) / HUNDREDS_OF_NANOSECONDS
            eventbirth = Event(
                timestamp=datetime.fromtimestamp(epoch_timestamp, tz=timezone.utc),
                source=self.originalPath[artefact.name],
            )
            eventbirth.description = "Creation time - " + " - ".join(desc)
            self._add_event(eventbirth)
        # check if there is a compilation date to add another line
        lnkdate = key.GetValueByName("f")
        if lnkdate:
            eventlnk = Event(
                timestamp=datetime.fromtimestamp(int(lnkdate.GetDataAsObject()), timezone.utc),
                source=self.originalPath[artefact.name],
            )
            eventlnk.description = "Compilation time - " + " - ".join(desc)
            self._add_event(eventlnk)

    def _parse_programs_key(self, key: Any, artefact: Path) -> None:  # noqa: ANN401
        event = Event(
            timestamp_str=key.last_written_time.CopyToDateTimeString()[:-4],
            source=self.originalPath[artefact.name],
        )
        desc = [f"KeyPath: {key.path}"]
        name = key.GetValueByName("0")
        if name:
            desc.append(f"Name: {name.GetDataAsObject()}")
        version = key.GetValueByName("1")
        if version:
            desc.append(f"Version: {version.GetDataAsObject()}")
        publisher = key.GetValueByName("2")
        if publisher:
            desc.append(f"Publisher: {publisher.GetDataAsObject()}")
        event.description = "Key last modified timestamp - " + " - ".join(desc)
        self._add_event(event)
        # check if there is an installation date to add another line
        installdate = key.GetValueByName("a")
        if installdate:
            eventinst = Event(
                timestamp=datetime.fromtimestamp(int(installdate.GetDataAsObject()), timezone.utc),
                source=self.originalPath[artefact.name],
            )
            eventinst.description = "Installation time - " + " - ".join(desc)
            self._add_event(eventinst)
        # check if there is a creation date to add another line
        uninstalldate = key.GetValueByName("b")
        if uninstalldate and int(uninstalldate.GetDataAsObject()) != 0:
            eventuninst = Event(
                timestamp=datetime.fromtimestamp(int(uninstalldate.GetDataAsObject()), timezone.utc),
                source=self.originalPath[artefact.name],
            )
            eventuninst.description = "Uninstallation time - " + " - ".join(desc)
            self._add_event(eventuninst)

    def _parse_artefact(self, artefact: Path) -> None:
        with artefact.open("rb") as f:
            try:
                reg_file = dfwinreg_regf.REGFWinRegistryFile(emulate_virtual_keys=False)
                reg_file.Open(f)
                win_registry = dfwinreg_registry.WinRegistry()
                key_path_prefix = win_registry.GetRegistryFileMapping(reg_file)
                reg_file.SetKeyPathPrefix(key_path_prefix)
                inventory_application_file = reg_file.GetKeyByPath(
                    "\\Root\\InventoryApplicationFile",
                )
                if inventory_application_file:
                    for iaf in inventory_application_file.RecurseKeys():
                        self._parse_inventory_application_file(iaf, artefact)
                inventory_driver_binary = reg_file.GetKeyByPath(
                    "\\Root\\InventoryDriverBinary",
                )
                if inventory_driver_binary:
                    for idb in inventory_driver_binary.RecurseKeys():
                        self._parse_inventory_driver_binary(idb, artefact)
                file_key = reg_file.GetKeyByPath(
                    "\\Root\\File",
                )
                if file_key:
                    for disk_guid in file_key.RecurseKeys():
                        for entry in disk_guid.RecurseKeys():
                            self._parse_file_key(entry, artefact)
                programs_key = reg_file.GetKeyByPath(
                    "\\Root\\Programs",
                )
                if programs_key:
                    for entry in programs_key.RecurseKeys():
                        self._parse_programs_key(entry, artefact)
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Error while parsing %s : %s", artefact.name, e)
