# Introduction

**orc2timeline** stands for "ORC to timeline", ORC refers to DFIR-ORC which is a tool used to parse and collect critical **artefacts of a Windows system** during an **incident response**.

While DFIR-ORC allows to gather all the data needed to operate a successfull incident response, no opensource tool was released to **help analyst to dissect archives that result of DFIR-ORC.exe** execution.

As a reminder, in the following we will use the term ORC to refer to a set of archives that is the output of DFIR-ORC.exe for a single host.

orc2timeline can take one or several ORC as input and generate one timeline per host.

This means that **orc2timeline decompresses targeted files** contained in ORC archives, **parses them** to extract interesting information and creates one or many event for a given artefact. One event must contain a timestamp. A **timeline** will then be created, **sorted by date** and **compressed in gzip** format to allow forensics analysis.

The **output timeline** is a **csv file** with the four following columns:
  - `Timestamp` (Time when the event occured);
  - `Hostname` (Name of the host, this can be useful when merging two or more timelines);
  - `SourceType` (Type of event) ;
  - `Description` (Description and details about the event);
  - `SourceFile` (Original path of the artefact if it exists, path in ORC archive otherwise).

orc2timeline can be run with a **list of file as input** and a **path to result file as output**. Files mentioned in input list must belong to the **same ORC run** (for a single host).

To process multiple ORC, it is also possible to specify an **input directory**, it is then necessary to specify an **output directory**. The **list of hosts** to process will be **infered** from the **recursive list of files** in the given directory. For now orc2timeline can not process a directory if two ORC of the same host are in different subdirectories. The **subtree** of the input directory will be **reproduced** in the output directory. One output file per host will be created in the given output directory.

Since artefact processing can be **time and resource consuming**, orc2timeline was designed to run on **multiple threads**. The usage of orc2timeline **could cause disk space or RAM exhaustion**, therefore testing its impact in your own environment is necessary and it **should not be run in a critical production environment**.

The goal of orc2timeline is the provide a framework that **knows how to extract specific pieces of data from an ORC collection** and create at least one event from it. **Plugins rely on external dependencies, that are deliberately not redevelop.**
