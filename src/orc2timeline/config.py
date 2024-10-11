"""Module for configuration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import yaml

DEFAULT_CONFIG_FILE = "Orc2Timeline.yaml"
ROOT_DIR = Path(__file__).resolve().parent


class Orc2TimelineConfigError(Exception):
    pass


class Config:
    def __init__(self) -> None:
        """Create Config object."""
        self.plugin_conf_list: list[PluginConfig] = []
        config_file = ROOT_DIR / "conf" / DEFAULT_CONFIG_FILE

        if not config_file.exists():
            logging.error('Cannot read configuration file "%s" (file does not exist)', config_file)
            error_str = f'Cannot read configuration file "{config_file}" (file does not exist)'
            raise Orc2TimelineConfigError(error_str)

        if not config_file.is_file():
            logging.error('Cannot read configuration file "%s" (is not a file)', config_file)
            error_str = f'Cannot read configuration file "{config_file}" (is not a file)'
            raise Orc2TimelineConfigError(error_str)

        try:
            with config_file.open("r") as conf_file:
                self.global_config = yaml.safe_load(conf_file)
                self._parse_global_config()
        except yaml.error.MarkedYAMLError:
            logging.critical("An error occured while parsing configuration (file: %s)", str(config_file))
            raise

        self.config_file = config_file

    def _parse_global_config(self) -> None:
        for plugin_conf_text in self.global_config["Plugins"]:
            for plug in plugin_conf_text:
                if plugin_conf_text[plug]["archives"] is None or len(plugin_conf_text[plug]["archives"]) == 0:
                    msg = f"Plugin {plug}: configuration describes plugin without any archive."
                    raise Orc2TimelineConfigError(msg)
                for archive in plugin_conf_text[plug]["archives"]:
                    if (
                        plugin_conf_text[plug].get("sub_archives") is None
                        or len(plugin_conf_text[plug].get("sub_archives")) == 0
                    ):
                        plugin_conf = PluginConfig(
                            plug,
                            [archive],
                            plugin_conf_text[plug]["match_pattern"],
                            plugin_conf_text[plug]["sourcetype"],
                            [],
                        )
                        self.plugin_conf_list.append(plugin_conf)
                    else:
                        if not isinstance(plugin_conf_text[plug].get("sub_archives", []), list):
                            msg = f"Plugin {plug}: sub_archives is not a list."
                            raise Orc2TimelineConfigError(msg)

                        for sub_archive in plugin_conf_text[plug].get("sub_archives", []):
                            plugin_conf = PluginConfig(
                                plug,
                                [archive],
                                plugin_conf_text[plug]["match_pattern"],
                                plugin_conf_text[plug]["sourcetype"],
                                [sub_archive],
                            )
                            self.plugin_conf_list.append(plugin_conf)
        if len(self.plugin_conf_list) == 0:
            logging.critical("Plugin list seems empty, exiting.")
            sys.exit(1)


class PluginConfig:
    def __init__(
        self,
        plugin_name: str,
        archives: list[str],
        match_pattern: str,
        sourcetype: str,
        sub_archives: list[str],
    ) -> None:
        """Create PluginConfig object."""
        self.plugin_name = plugin_name
        self.archives = archives
        self.sub_archives = sub_archives
        self.match_pattern = match_pattern
        self.sourcetype = sourcetype

        if self.sub_archives is None:
            self.sub_archives = []

        if self.plugin_name == "":
            msg = "Empty plugin name in configuration is not allowed."
            raise Orc2TimelineConfigError(msg)
        if not Path(ROOT_DIR, "plugins", self.plugin_name + ".py").is_file():
            msg = (
                f"Plugin {self.plugin_name}: {Path(ROOT_DIR, 'plugins', self.plugin_name + '.py').as_posix()}"
                f" does not exist."
            )
            raise Orc2TimelineConfigError(msg)
        if len(self.archives) == 0:
            msg = f"Plugin {self.plugin_name}: archives should not be empty."
            raise Orc2TimelineConfigError(msg)
        if self.sourcetype == "":
            msg = f"Plugin {self.plugin_name}: empty sourcetype is not allowed."
            raise Orc2TimelineConfigError(msg)
        if self.match_pattern == "":
            msg = (
                f"Plugin {self.plugin_name}: empty match_pattern is not allowed. "
                'Hint: ".*" can be used to match all the files.'
            )
            raise Orc2TimelineConfigError(msg)
