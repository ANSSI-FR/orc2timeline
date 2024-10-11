# orc2timeline

**orc2timeline** stands for "ORC to timeline", ORC refers to DFIR-ORC which is a tool used to parse and collect critical **artefacts of a Windows system** during an **incident response**.

orc2timeline can take one or several ORC as input and **generate one timeline per host**.

## Installation

```
git clone https://github.com/ANSSI-FR/orc2timeline.git
cd orc2timeline
pip install .
```

## Examples

Let us consider the following file tree:
```
$ tree ~
~
└── Documents
    ├── ORC
    │   ├── DFIR-ORC_Server_ServerName.domain_Browsers.7z
    │   ├── DFIR-ORC_Server_ServerName.domain_Detail.7z
    │   ├── DFIR-ORC_Server_ServerName.domain_General.7z
    │   ├── DFIR-ORC_Server_ServerName.domain_Little.7z
    │   ├── DFIR-ORC_Server_ServerName.domain_Powershell.7z
    │   ├── DFIR-ORC_Server_ServerName.domain_SAM.7z
    │   └── DFIR-ORC_Workstation_MachineName.domain_Offline.7z
    └── output_directory

3 directories, 7 files
```

Process all the ORC contained in a directory (orc2timeline will infer hostname from file names and group files by host to process them):
```
$ orc2timeline --tmp-dir=/tmp/data process_dir -j 4  ~/Documents/ORC ~/Documents/output_directory
```

This command will create the following files:
```
~
└── Documents
    └── output_directory
        ├── MachineName.domain.csv.gz
        └── ServerName.domain.csv.gz
```

## Documentation

A more detailed documentation is provided if needed :

### [Introduction](docs/0_Intro.md)
### [Tutorial](docs/1_Tutorial.md)
### [Installation and requirements](docs/2_Installation_and_requirements.md)
### [Architecture](docs/3_Architecture.md)
### [Configuration](docs/4_Configuration.md)
### [Existing plugins](docs/5_Existing_plugins.md)
### [Develop your own plugin](docs/6_Develop_your_own_plugin.md)
### [Licenses](docs/7_Licenses.md)
### [Frequently Asked Questions](docs/8_FAQ.md)

