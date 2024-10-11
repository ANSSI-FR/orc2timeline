# Tutorials

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

## Process a single ORC

#### Process one ORC (input files must belong to the same execution of DFIR-ORC.exe for a single host):
```
$ orc2timeline process Documents/ORC/DFIR-ORC_Server_ServerName.domain_Powershell.7z Documents/ORC/DFIR-ORC_Server_ServerName.domain_Little.7z Documents/ORC/DFIR-ORC_Server_ServerName.domain_Browsers.7z Documents/ORC/DFIR-ORC_Server_ServerName.domain_General.7z Documents/ORC/DFIR-ORC_Server_ServerName.domain_Detail.7z Documents/ORC/DFIR-ORC_Server_ServerName.domain_SAM.7z Documents/output_directory/ServerName.domain.csv.gz
```

or

```
$ orc2timeline process ~/Documents/ORC/DFIR-ORC_Server_ServerName.domain_*.7z ~/Documents/output_directory/ServerName.domain.csv.gz
```

If you try to process archives that do not belong to the same host, an exception will be raised and program will exit:
```
$ orc2timeline process --overwrite Documents/ORC/DFIR-ORC_* Documents/output_directory/ServerName.domain.csv.gz
[2012-12-21 23:59:59,999] WARNING  - --jobs option was not given, thus only one thread will be used. Therefore processing could take a while. 
Usage: orc2timeline process [OPTIONS] [FILE_LIST]... OUTPUT_PATH
Try 'orc2timeline process --help' for help.

Error: Invalid value: Bad file list, all files must belong to the same host. Parsed hosts : {'ServerName.domain', 'MachineName.domain'}
```

#### Use multiple threads

Use 4 threads to process one ORC, overwrite output file if it already exists, use ~/temp as temporary directory:
```
$ TMPDIR=~/temp orc2timeline process -j 4 --overwrite Documents/ORC/DFIR-ORC_Server_ServerName.domain_* Documents/output_directory/ServerName.domain.csv.gz
```

## Process many ORC with a single command

Process all the ORC contained in a directory (orc2timeline will infer hostname from file names and group files by host to process them):
```
$ orc2timeline --tmp-dir=/tmp/data process_dir -j 4  ~/Documents/ORC ~/Documents/output_directory
```

This previous command will create the following files:
```
~
└── Documents
    └── output_directory
        ├── MachineName.domain.csv.gz
        └── ServerName.domain.csv.gz
```

## Show configuration

Command that show the path to configuration file :
```
orc2timeline show_conf_file
```

Command that shows the configuration (content of configuration file) that will be used :
```
orc2timeline show_conf
```

**NB** : if you want to run orc2timeline with a custom configuration, you **must** modify the configuration file inplace, there is no way to give a custom path to another configuration file.

## Command that combine a lot of options

This command will process all the ORC contained in `./Documents/ORC` and write the timelines in `./Documents/`. Four threads will be used, if a timeline already exists it will be overwritten. `/tmp/data/` will be used as temporary directory and output log level is DEBUG (maximum value).
```
$ orc2timeline --log-level=DEBUG --tmp-dir=/tmp/data process_dir --overwrite -j 4  ./Documents/ORC ./Documents/output_directory
```
