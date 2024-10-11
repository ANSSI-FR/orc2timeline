# Architecture

## Language

orc2timeline is written in **python (version 3)**. Since the goal of this tool is **to rely on external dependencies** to parse artefacts, it seemed relevant to choose a **widely adopted language** to take advantage of the **large amount of libraries** available.

Moreover considering the adoption of python it seems perfect to **ease maintenance and evolutions** of the project.

## Plugin

orc2timeline works with plugins. This means that when launched, orc2timeline will **read configuration** to know the **list of plugins** (and the configuration for every plugin) to run. After that list is built, every plugin instance (there **can be several plugin instances for one plugin**) will be run using **all the available threads** given.

Each plugin writes a temporary intermediate file that contains an extract of the final timeline (csv file ordered by date). Once all the plugins are executed, all the **plugin timelines for a given host are consolidated into a final host timeline**. All lines are **deduplicated and sorted by date**. During this consolidation, **one thread can be used per host** treated.
