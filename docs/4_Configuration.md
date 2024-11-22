# Configuration file

### Introduction

Depending on the **Orc configuration** you use, you may have to **customize the configuration**. The given configuration works with the configuration of DFIR-ORC that is published on [GitHub](https://github.com/DFIR-ORC/dfir-orc-config).

The configuration file is a **yaml file** that is read every time orc2timeline is run during the preliminary phase of the execution. The file can be modified, but **must stay inplace**. To know the path where to find this file the following command can be used : `orc2timeline show_conf_file`. To validate the modifications, `orc2timeline show_conf` command can be used to view the configuration that will be used.

### Explanations

The following snippet of the configuration file will be explained:
```
Plugins:
  - EventLogsToTimeline:
      archives: ["General", "Little"]
      sub_archives: ["Event.7z", "Event_Little.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"

  - NewPlugin:
[...]
```

The file begins with the keyword `Plugins`, it contains a list of plugin. In this example `EventLogsToTimeline` is configured, it means that `src/orc2timeline/plugins/EventLogsToTimeline.py` file will be loaded (a complete guide to write a plugin exists [here](6_Develop_your_own_plugin.md)).

The plugin has **four attributes**:
  - `archives`: list of archive types to dissect (example: from `General`, the `DFIR-ORC_Server_MACHINENAME_General.7z` will be used);
  - `sub_archives`: list of archives to decompress from the primary archive (the final artefacts are inside these sub\_archives), if the files are directly contained in the primary archive this attribute **can be omitted**;
  - `match_pattern`: regex pattern used to filter which files must be processed;
  - `sourcetype`: string that will be used for the column SourceType for this plugin.

All the combinations between `archives` and `sub_archives` will be used to create plugin instances. With the previous example, the following instances will be created:
  - `EventLogsToTimeline(archives="General", sub_archives="Event.7z", ...)`;
  - `EventLogsToTimeline(archives="General", sub_archives="Event_Little.7z", ...)`;
  - `EventLogsToTimeline(archives="Little", sub_archives="Event.7z", ...)`;
  - `EventLogsToTimeline(archives="Little", sub_archives="Event_Little.7z", ...)`.

Considering the following layout:

```
DFIR-ORC_Server_MACHINENAME_General.7z
├── Event.7z
│   └── file1.evtx
└── Other.7z
    └── file5.evtx
DFIR-ORC_Server_MACHINENAME_Little.7z
├── Event.7z
│   └── file2.evtx
└── Event_Little.7z
    ├── file3.evtx
    └── file4.evt
```

The files `file1.evtx`, `file2.evtx`, `file3.evtx` will be processed. `file4.evt` will not be processed because it does not match the `match_pattern`, `file5.evtx` will not be processed because `Other.7z` is not mentioned in the `sub_archives` list.

The **same plugin can be described many times** in the configuration file. The following snippet or configuration is equivalent to the previous one:
```
Plugins:
  - EventLogsToTimeline:
      archives: ["General"]
      sub_archives: ["Event.7z", "Event_Little.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"

  - EventLogsToTimeline:
      archives: ["Little"]
      sub_archives: ["Event.7z", "Event_Little.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"

  - NewPlugin:
[...]
```

**Warning !** The following snippet is **NOT** equivalent to the first one:
```
Plugins:
  - EventLogsToTimeline:
      archives: ["General"]
      sub_archives: ["Event.7z", "Event_Little.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"

  - EventLogsToTimeline:
      archives: ["Little"]
      sub_archives: ["Event_Little.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"

  - NewPlugin:
[...]
```

Because `file2.evtx` from precedent example **would not be parsed anymore**.

### Syntactic sugar

For **readability** purpose, it may be useful to split the configuration of a plugin in two **distinct** configuration specifications. For example, the Offline configuration could be detached from the "live" configuration. The two following snippets are equivalent :

**All in one** configuration:
```
[...]
  - EventLogsToTimeline:
      archives: ["General", "Little", "Offline"]
      sub_archives: ["Event.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"
[...]
```

**Two-piece** configuration:
```
[...]
  - EventLogsToTimeline:
      archives: ["General", "Little"]
      sub_archives: ["Event.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"

  - EventLogsToTimeline:
      archives: ["Offline"]
      sub_archives: ["Event.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"
[...]
```

### One configuration to rule them all.

orc2timeline's configuration allows the user to **set multiple DFIR-ORC configurations in the same file**. As long as parameters are **narrow enough** and the two configurations **do not conflict** with each other, they can live in the same file.

Of course this will result in multiple plugin instances that will not match any artefact, but this should not deteriorate performance and the final result will remain valid.
