# Copyright (c) 2025 M. Fairbanks
#
# This source code is licensed under the Apache License, Version 2.0, found in the
# LICENSE file in the root directory of this source tree.

from m9lib import uTimer

from folder_section import *
from folder_set import *
from file_set import *

from enum import Enum

class FolderScanStage(Enum):
    INIT = 0        # initialization
    HIERARCHY = 1   # calculated hierarchy
    FOLDER_SCAN = 2 # performed folder scan

class FolderScan:

    def __init__(self):
        self.stage = FolderScanStage.INIT
        self.folders = []
        self.global_exclude = None

    def AddFolder(self, Folder:FolderSection):
        # adds a folder to the scan operation
        if self.stage==FolderScanStage.INIT:
            self.folders.append(Folder)
            self.__calculate_children()

    def __calculate_children(self):
        # determine folder hierarchy
        # FolderUtils.Loggger.WriteLine(f"Scanning hierarchies...")
        folder:FolderSection = None
        for folder in self.folders:
            folder.reset_children()

        for folder in self.folders:
            for subfolder in self.folders:
                if folder != subfolder:
                    if subfolder.IsUnder(folder):
                        folder.AddChild(subfolder)

    def SetGlobalExclude(self, ExcludeFolders:list):
        # adds a global exclude section
        self.global_exclude = ExcludeFolders

    def GetFolders(self)->list:
        # list of FolderSection
        return self.folders

    def ScanFolders(self)->bool:
        if self.stage!=FolderScanStage.INIT:
            return False
        
        # types
        folder:FolderSection = None
        subfolder:FolderSection = None

        timer1 = uTimer()
        SyncUtils.Logger.WriteLine("")
        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Performing folder scan...[+]")
        SyncUtils.Logger.WriteLine(f"{len(self.folders)} folder sections")

        # collect folder paths
        self.stage = FolderScanStage.HIERARCHY
        for folder in self.folders:
            SyncUtils.Logger.WriteLine(f"[+VIOLET]Scanning {folder.GetPath()}...[+]")
            timer2 = uTimer()
            exclude_folders = []
            # child folders are always excluded
            for child in folder.GetChildren():
                exclude_folders.append (child.GetPath())

            # global exclude setting
            if isinstance(self.global_exclude, list) and len(self.global_exclude)>0:
                folder_set = FolderSet(folder.GetPath(), self.global_exclude, exclude_folders, ApplyTags=False)
                exclude_folders.extend(folder_set.GetFolders())

            # local exclude setting
            exclude_folder_rules = folder.GetExcludeFolderRules()
            if len(exclude_folder_rules)>0:
                folder_set = FolderSet(folder.GetPath(), exclude_folder_rules, exclude_folders, ApplyTags=False)
                exclude_folders.extend(folder_set.GetFolders())

            # finalize folder set
            final_set = FolderSet(folder.GetPath(), None, exclude_folders)

            # apply folder tags
            folder_tag_rules = folder.GetFolderTagRules()
            final_set.ApplyFolderTags(folder_tag_rules)

            SyncUtils.Logger.WriteLine(f"- {timer2.GetElapsedString()}")
            SyncUtils.Logger.WriteLine(f"- {len(final_set.GetFolders())} folders")

            folder.SetScanFolders(final_set.GetFoldersWithTags())

        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Completed folder scan ({timer1.GetElapsedString()})[+]")
        self.stage = FolderScanStage.FOLDER_SCAN

        timer1 = uTimer()
        SyncUtils.Logger.WriteLine("")
        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Performing file scan...[+]")
        SyncUtils.Logger.WriteLine(f"{len(self.folders)} folder sections")
        scan_file_count = 0
        for folder in self.folders:
            timer2 = uTimer()
            SyncUtils.Logger.WriteLine(f"[+VIOLET]Scanning {folder.GetPath()}...[+]")
            scan_folders = folder.GetScanResults()
            SyncUtils.Logger.WriteLine(f"Scanning {len(scan_folders)} folders for files...")
            fileset_rules = FileSetRules(folder.GetDefaultSetting()=="INCLUDE", folder.GetIncludeFileRules(), folder.GetExcludeFileRules())
            for scan_dict in scan_folders:
                scan_files = fileset_rules.ScanFiles(scan_dict['folder'], scan_dict['tags'])
                folder.AddScanFiles(scan_dict['folder'], scan_files)
                scan_file_count += len(scan_files)

            SyncUtils.Logger.WriteLine(f"- {timer2.GetElapsedString()}")
            SyncUtils.Logger.WriteLine(f"- {len(final_set.GetFolders())} folders")
            SyncUtils.Logger.WriteLine(f"- {scan_file_count} files")

        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Completed file scan ({timer1.GetElapsedString()})[+]")

        return True
