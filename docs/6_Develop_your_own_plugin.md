# Develop your own plugin

orc2timeline works with plugins in order to ease features integration. Therefore, adding the parsing of an artefact can be done by modifying only two files. First the plugin file must be created, then the plugin configuration must be appended to the configuration file.

## MyPlugin.py

### File path and file name

The first file **must** be named by the plugin name: if your plugin will process LNK files, it could be named `LNKToTimeline`, therefore the file will be named `LNKToTimeline.py`.

The location of this file must be `<orc2timeline_directory>/src/orc2timeline/plugins/LNKToTimeline.py`.

In the following example, we assume that we have a very convenient library named `magic_lnk_library` that contains all the functions and class we need to parse lnk files.

## One plugin equals one class

### GenericToTimeline

This file, is a python module that can contain multiple classes. This module **must contain a class that is named after the file name**, this class **must inherit** from `GenericToTimeline`.

`GenericToTimeline` is a module that contains two classes:
  - `Event` (describes an event that represents one line in the final timeline);
  - `GenericToTimeline` (implements a collection of functions that will be useful during the plugin development).

Example:
```
from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline

class LNKToTimeline(GenericToTimeline):
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

```

### Event

As stated above, `Event` class **must** be used to add an event to the final timeline. It is a very simple class but all the attributes of this class must be completed.

The event object **must** be added with the function `_add_event` of the class `GenericToTimeline`.

How to add an event :
```
event = Event()
event.description = "Good description"
event.timestamp = datetime.now()
# the following line could replace the previous line
# event.timestamp_str = "2012-12-21 23:59:59.999"
event.source = "/path/to/artefact"
self._add_event(event)
```

## Helpful and mandatory functions

One function of your class that is **absolutely mandatory to override** is `_parse_artefact`, because the original one does **nothing**.

Another function that **must** be called is `_add_event`, it take an Event as argument, and **adds it to the final timeline**.

Based on the configuration, the artefact files will be extracted accordingly to GenericToTimeline's mechanisms. These files will then be passed one by one as argument to the function `_parse_artefact`.

`self._get_original_path` can be used to retrieve the path of the artefact as it was on the original filesystem. If an error occurs, this function returns the path inside the archive instead.

Example:
```
def _parse_artefact(self, artefact: Path) -> None:
    timestamp = magic_lnk_library.get_relevant_timestamp_from_file(artefact)
    source=self._get_original_path(artefact)
    description = magic_lnk_library.get_relevant_description_from_file(artefact)

    event = Event(
        timestamp=timestamp,
        source=source,
        description=description,
    )

    self._add_event(event)
```

## File header filter

In your plugin class (LNKToTimeline in our example), it is possible to add an optional attribute called `file_header`. It is a byte array that is an additional filter on files that should be processed.

If the file header matches the byte array, it will be processed, otherwise the file will be ignored.

For our example, LNK files begin with the length of the header (0x4c) followed by the GUID {00021401-0000-0000-c000-000000000046}. Therefore, the header of the LNK files is `4c00 0000 0114 0200 0000 0000 c000 0000 0000 0046`.

Example:
```
self.file_header = bytes([0x4c, 0x00, 0x00, 0x00, 0x01, 0x14, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46])
```

## Plugin configuration

DFIR-ORC configuration analysis shows that lnk files are collected:
  - in `General` archive in `Artefacts.7z`;
  - in `Offline` archive in `Artefacts.7z`.

All the collected files contain `lnk` is their names.

We could add the following snippet to orc2timeline's configuration:
```
  - LNKToTimeline:
      archives: ["General", "Offline"]
      sub_archives: ["Artefacts.7z"]
      match_pattern: "^.*lnk.*$"
      sourcetype: "LNK"
```

## Final example

Considering all the above, here is the final result of our example plugin.

### LNKToTimeline.py
```
#######################################
# Following lines are only for typing #
#######################################
"""Plugin to parse LNK files."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from threading import Lock

    from orc2timeline.config import PluginConfig
#######################################


import magic_lnk_library

from orc2timeline.plugins.GenericToTimeline import Event, GenericToTimeline


class LNKToTimeline(GenericToTimeline):
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
        timestamp = magic_lnk_library.get_relevant_timestamp_from_file(artefact)
        source = self._get_original_path(artefact)
        description = magic_lnk_library.get_relevant_description_from_file(artefact)

        event = Event(
            timestamp=timestamp,
            source=source,
            description=description,
        )

        self._add_event(event)

```

