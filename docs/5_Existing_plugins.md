# Existing plugins

orc2timeline is designed to work with plugins. Plugin files are located in `src/orc2timeline/plugins/` directory, one file per plugin.

**One plugin** is meant to process **one type of artefact** collected by DFIR-ORC. The location of these artefacts **must be predictable**, so that the plugin can efficiently extract it from the archives.

Plugins may be divided in two categories: DFIR-ORC-artefact plugins and Windows-artefact plugins.

## DFIR-ORC-artefact plugins

These plugins are meant to process files that are **generated during DFIR-ORC execution**. Those files are not actual artefacts but **the result of DFIR-ORC parsers**, they gather information that are very relevant for forensics analysis.

### NTFSInfoToTimeline plugin

This plugin processes files located in:
  - the `Little` archive, inside `NTFSInfo_detail.7z`;
  - the `General` archive, inside `NTFSInfo_quick.7z`;
  - the `Detail` archive, inside `NTFSInfo_detail.7z`;
  - the `Offline` archive, inside `NTFSInfo_detail.7z`.

The treated csv file should be the result of DFIR-ORC's NTFSInfo command.

Configuration snippet:
```
[...]
  - NTFSInfoToTimeline:
      archives: ["Detail", "General", "Little", "Offline"]
      sub_archives: ["NTFSInfo_detail.7z", "NTFSInfo_quick.7z"]
      match_pattern: "^.*NTFSInfo[^/]*\\.csv$"
      sourcetype: "MFT"
[...]
```

For each entry in this csv file, one event is created per file and per different timestamp. This means that events with the same file\_path and timestamp will be grouped in a single event.

Output example:
```
2021-01-05 10:35:26.012,FAKEMACHINE,MFT,$SI: .A.B - $FN: MACB - Name: \Windows\System32\winevt\Logs\Microsoft-Windows-Bits-Client%4Operational.evtx - Size in bytes: 69632,NTFSInfo_00000000_DiskInterface_0xc87c5cca7c5cb542_.csv
2021-01-05 10:35:26.996,FAKEMACHINE,MFT,$SI: .A.B - $FN: MACB - Name: \Windows\System32\winevt\Logs\Microsoft-Windows-Diagnosis-DPS%4Operational.evtx - Size in bytes: 69632,NTFSInfo_00000000_DiskInterface_0xc87c5cca7c5cb542_.csv
2022-10-24 01:48:19.929,FAKEMACHINE,MFT,$SI: M.C. - $FN: .... - Name: \Windows\System32\winevt\Logs\Microsoft-Windows-Diagnosis-DPS%4Operational.evtx - Size in bytes: 69632,NTFSInfo_00000000_DiskInterface_0xc87c5cca7c5cb542_.csv
2022-10-24 14:12:54.482,FAKEMACHINE,MFT,$SI: M.C. - $FN: .... - Name: \Windows\System32\winevt\Logs\Microsoft-Windows-Bits-Client%4Operational.evtx - Size in bytes: 69632,NTFSInfo_00000000_DiskInterface_0xc87c5cca7c5cb542_.csv
```

### I30InfoToTimeline plugin

This plugin processes files located in:
  - the `Detail` archive, inside `NTFSInfo_i30Info.7z`;
  - the `Offline` archive, inside `NTFSInfo_i30Info.7z`.

The treated csv file should be the result of DFIR-ORC's NTFSInfo with `/i30info` argument.

Configuration snippet:
```
[...]
  - I30InfoToTimeline:
      archives: ["Detail", "Offline"]
      sub_archives: ["NTFSInfo_i30Info.7z"]
      match_pattern: "^I30Info.*\\.csv$"
      sourcetype: "I30"
[...]
```

For each entry in this csv file, one event is created per file and per different timestamp. This means that events with the same file\_path and timestamp will be grouped in a single event.

Output example:
```
2009-07-14 03:20:08.961,FAKEMACHINE,I30,Entry in slackspace - $FN: ...B - Name: Windows - MFT segment num: 379 - Parent FRN: 0x0005000000000005 ,I30Info_00000000_DiskInterface_0xc87c5cca7c5cb542_.csv
2021-01-05 19:24:19.796,FAKEMACHINE,I30,Entry in slackspace - $FN: MACB - Name: WinPEpge.sys - MFT segment num: 54 - Parent FRN: 0x0005000000000005 ,I30Info_00000000_DiskInterface_0xc87c5cca7c5cb542_.csv
2021-01-05 19:24:33.593,FAKEMACHINE,I30,Entry in slackspace - $FN: MAC. - Name: Windows
```

### USNInfoToTimeline plugin

This plugin processes files located in:
  - the `Little` archive, inside `USNInfo.7z`;
  - the `Detail` archive, inside `USNInfo.7z`;
  - the `Offline` archive inside `USNInfo.7z`.

The treated csv file should be the result of DFIR-ORC's USNInfo command.

Configuration snippet:
```
[...]
  - USNInfoToTimeline:
      archives: ["Detail", "Little", "Offline"]
      sub_archives: ["USNInfo.7z"]
      match_pattern: "^USNInfo.*\\.csv$"
      sourcetype: "USN journal"
[...]
```

For each entry in this csv file, one event is created per file and per different timestamp. This means that events with the same file\_path and timestamp will be grouped in a single event.

Output example:
```
2023-11-30 16:12:58.609,W11-22H2U,USN journal,\ProgramData\Microsoft\Windows Defender\Scans\mpenginedb.db-wal - CLOSE|DATA_EXTEND|DATA_OVERWRITE|DATA_TRUNCATION|FILE_CREATE|SECURITY_CHANGE - MFT segment num : 77487,USNInfo_00000000_DiskInterface_0x48f2eac0f2eab0fc_.csv
2023-11-30 16:12:58.609,W11-22H2U,USN journal,\ProgramData\Microsoft\Windows Defender\Scans\mpenginedb.db-wal - CLOSE|FILE_DELETE - MFT segment num : 77487,USNInfo_00000000_DiskInterface_0x48f2eac0f2eab0fc_.csv
2023-11-30 16:17:52.133,W11-22H2U,USN journal,\ProgramData\Microsoft\Windows Defender\Scans\mpenginedb.db-wal - FILE_CREATE - MFT segment num : 2259,USNInfo_00000000_DiskInterface_0x48f2eac0f2eab0fc_.csv
2023-11-30 16:17:52.242,W11-22H2U,USN journal,\ProgramData\Microsoft\Windows Defender\Scans\mpenginedb.db-wal - DATA_EXTEND|FILE_CREATE - MFT segment num : 2259,USNInfo_00000000_DiskInterface_0x48f2eac0f2eab0fc_.csv
```

## Windows-artefact plugins

DFIR-ORC collects files that may help DFIR analysis. Extracting the relevant pieces of data out of those files can be tricky since they are not meant to be parsed, and can be in proprietary format. orc2timeline **relies on opensource parsers**, the choice was made not to redevelop all the parsers and **take advantage of existing libraries**.

The plugins to parse Registry Hives and Event Logs are released. Many more could be developed for processing other types of artefacts such as LNK files, Jumplists... Developing these plugins is left as an exercise to the reader (contributions are welcome).


### RegistryToTimeline plugin

This plugin processes registry hives, it creates one event per registry key, the last modification date of the key is used as a timestamp.

The file named `RegistryToTimeline-important-keys.txt` allows to specify keys for which an event will be printed in the final timeline for each key value. The **key path must be exact**, regex are not supported.

For more sophisticated treatments on key paths or key values, a new plugin must be developed. This new plugin could inherit `RegistryToTimeline` to benefit from existing functions.

This plugin processes files located in:
  - the `Little` archive, inside `SystemHives_little.7z`;
  - the `Detail` archive, inside `SystemHives.7z` and `UserHives.7z`;
  - the `SAM` archive, inside `SAM.7z`;
  - the `Offline` archive inside `SystemHives.7z`, `UserHives.7z`, `SAM.7z`.

Configuration snippet:
```
[...]
  - RegistryToTimeline:
      archives: ["SAM", "Little", "Detail", "Offline"]
      sub_archives: ["SAM.7z", "SystemHives_little.7z", "UserHives.7z", "SystemHives.7z"]
      match_pattern: ".*data$"
      sourcetype: "Registry"
[...]
```

Output example:
```
2009-07-14 04:49:35.659,FAKEMACHINE,Registry,HKEY_CURRENT_USER\Environment,\Windows\ServiceProfiles\LocalService\NTUSER.DAT
2009-07-14 04:49:35.659,FAKEMACHINE,Registry,KeyPath: HKEY_CURRENT_USER\Environment - KeyName: TEMP - KeyType: RegExpandSZ - KeyValue: %USERPROFILE%\AppData\Local\Temp,\Windows\ServiceProfiles\LocalService\NTUSER.DAT
2009-07-14 04:49:35.659,FAKEMACHINE,Registry,KeyPath: HKEY_CURRENT_USER\Environment - KeyName: TMP - KeyType: RegExpandSZ - KeyValue: %USERPROFILE%\AppData\Local\Temp,\Windows\ServiceProfiles\LocalService\NTUSER.DAT
2009-07-14 04:49:35.674,FAKEMACHINE,Registry,HKEY_CURRENT_USER\Software\Microsoft\Windows NT\CurrentVersion\Winlogon,\Windows\ServiceProfiles\LocalService\NTUSER.DAT
2009-07-14 04:49:35.674,FAKEMACHINE,Registry,KeyPath: HKEY_CURRENT_USER\Software\Microsoft\Windows NT\CurrentVersion\Winlogon - KeyName: ExcludeProfileDirs - KeyType: RegSZ - KeyValue: AppData\Local;AppData\LocalLow;$Recycle.Bin,\Windows\ServiceProfiles\LocalService\NTUSER.DAT
```


### EventLogsToTimeline plugin

This plugin processes Windows log events, for each `evtx` file, this plugin parses all the events to create one line per event in the final timeline.

The file `EventLogsToTimeline-eventmap.txt` allows the analyst to specify tuples (Channel/Event ID) for which events description will be prefixed with a custom string.

This plugin processes files located in:
  - the `General` archive, inside Event.7z;
  - the `Little` archive, inside Event.7z;
  - the `Offline` archive, inside Event.7z.

Configuration snippet:
```
[...]
  - EventLogsToTimeline:
      archives: ["General", "Little", "Offline"]
      sub_archives: ["Event.7z"]
      match_pattern: ".*evtx.*"
      sourcetype: "Event"
[...]
```

Output example:
```
2021-02-12 15:56:30.372,FAKEMACHINE,Event,Microsoft-Windows-Servicing:1 S-1-5-18 (KBWUClient-SelfUpdate-Aux Staged Installed WindowsUpdateAgent),\Windows\System32\winevt\Logs\Setup.evtx
2021-02-12 15:56:32.512,FAKEMACHINE,Event,Microsoft-Windows-Servicing:4 S-1-5-18 (KBWUClient-SelfUpdate-Aux Installed 0x0 WindowsUpdateAgent),\Windows\System32\winevt\Logs\Setup.evtx
2022-10-24 01:46:29.681,FAKEMACHINE,Event,Microsoft-Windows-Servicing:2 S-1-5-18 (KBWUClient-SelfUpdate-Aux Installed 0x0 WindowsUpdateAgent),\Windows\System32\winevt\Logs\Setup.evtx
```

### FirefoxHistoryToTimeline plugin

This plugin processes Firefox history file by extracting information from `moz_places` and `moz_historyvisits` tables to create relevant events.

Configuration snippet:
```
  - FirefoxHistoryToTimeline:
      archives: ["Browsers", "General", "Offline"]
      sub_archives: ["Browsers_history.7z", "GetBrowsers_History.7z", "Browsers_complet.7z"]
      match_pattern: ".*places\\.sqlite.*data$"
      sourcetype: "FirefoxHistory"
```

Output example:
```
2024-11-12 13:19:37.932,FAKEMACHINE,FirefoxHistory,Url: https://www.mozilla.org/privacy/firefox/ - Title: None - Count: 1 - Typed: 0 - Referer: None,\Users\prestataire\AppData\Roaming\Mozilla\Firefox\Profiles\4hleai00.dev-edition-default\places.sqlite
2024-11-12 13:19:37.952,FAKEMACHINE,FirefoxHistory,Url: https://www.mozilla.org/fr/privacy/firefox/ - Title: Firefox - Politique de confidentialité — Mozilla - Count: 1 - Typed: 0 - Referer: https://www.mozilla.org/privacy/firefox/,\Users\prestataire\AppData\Roaming\Mozilla\Firefox\Profiles\4hleai00.dev-edition-default\places.sqlite
```

### RecycleBinToTimeline

This plugin relies on files that are located in RecycleBin directory, since these files are small, they are collected as resisdent files, They contains useful metadatas about the deleted items.

Configuration snippet:
```
  - RecycleBinToTimeline:
      archives: ["General"]
      sub_archives: ["Residents.7z"]
      match_pattern: "(.*fichiers_residents/.*_\\$I.*data$)"
      sourcetype: "RecycleBin"
```

Output example:
```
2024-05-06 15:56:56.626,FAKEMACHINE,RecycleBin,Deletion of file C:\Users\Admin\Downloads\prd-testzip-W7.zip - Filesize : 572,\$Recycle.Bin\S-1-5-21-2533359573-307034746-4050449962-1001\$ILX8009.zip
```

### UserAssistToTimeline

This plugin parses UserAssist registry keys from user hives to extract information about executables that have been run on the system.

Configuration snippet:
```
  - UserAssistToTimeline:
      archives: ["Detail", "Offline"]
      sub_archives: ["UserHives.7z"]
      match_pattern: ".*NTUSER\\.DAT.*"
      sourcetype: "UserAssist"
```

Output example:
```
2019-09-02 16:06:16.285,FAKEMACHINE,UserAssist,ExecPath: Microsoft.Windows.Explorer - RunCount: 2 - FocusTime: 20986 - RegistryTimestamp: 2019-09-05 17:31:35.056,\Users\Admin\NTUSER.DAT
2019-09-05 17:31:21.077,FAKEMACHINE,UserAssist,ExecPath: C:\Windows\System32\cmd.exe - RunCount: 2 - FocusTime: 140 - RegistryTimestamp: 2019-09-05 17:31:35.056,\Users\Admin\NTUSER.DAT
```

### AmCacheToTimeline

This plugin parses `AmCache.hve` hives to extract useful information about installed programs and drivers.

Configuration snippet:
```
  - AmCacheToTimeline:
      archives: ["Little", "Detail", "Offline"]
      sub_archives: ["SystemHives_little.7z", "SystemHives.7z"]
      match_pattern: ".*AmCache.hve.*data$"
      sourcetype: "AmCache"
```

Output example:
```
2019-01-08 12:20:14.000,FAKEMACHINE,AmCache,Installation time - KeyPath: \Root\Programs\0000b599e632970468f205d794760cf82dc70000ffff - Name: Microsoft Visual C++ 2017 Redistributable (x86) -
 14.12.25810 - Version: 14.12.25810.0 - Publisher: Microsoft Corporation,\Windows\appcompat\Programs\Amcache.hve
2019-12-07 09:52:17.000,FAKEMACHINE,AmCache,Driver Last Write time - KeyPath: \Root\InventoryDriverBinary\c:/windows/system32/drivers/wpdupfltr.sys - Name: wpdupfltr.sys - SHA1: 3445834e133a4bc386a15ff42dd4566bda3ad10a - FileSize: 57344,\Windows\appcompat\Programs\Amcache.hve
```

