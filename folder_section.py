# Copyright (c) 2025 M. Fairbanks
#
# This source code is licensed under the Apache License, Version 2.0, found in the
# LICENSE file in the root directory of this source tree.

from m9lib import uConfigSection

import os

from sync_utils import *

class FolderSection:
    def __init__(self, Section:uConfigSection):
        self.valid = True
        self.id = Section.GetId()
        self.path = Section.GetValue('Path')
        self.reset_children()
        self.exclude_folder_rules = []
        self.folder_tag_rules = []
        self.include_file_rules = []
        self.exclude_file_rules = []
        self.default_rule = "INCLUDE"
        self.target_path = None
        if self.path is not None and self.path != '':
            self.path = SyncUtils.NormalizePath(self.path)
            if os.path.isdir(self.path) is False:
                SyncUtils.Logger.WriteError(f"Path specified does not exist in [SourceFolder:{self.id}]: {self.path}")
                self.valid = False
        else:
            SyncUtils.Logger.WriteError(f"Path not specified for [SourceFolder:{self.id}]")
            self.valid = False
        if Section.HasValue("ExcludeFolders"):
            self.exclude_folder_rules = SyncUtils.CombineFolderSetRules(Section.GetConfig(), Section.GetValue("ExcludeFolders"))
        if Section.HasValue("FolderTags"):
            self.folder_tag_rules = SyncUtils.CombineFolderSetRules(Section.GetConfig(), Section.GetValue("FolderTags"))
        ds = Section.GetValue("DefaultRule")
        if isinstance(ds, str) and ds.upper() == "EXCLUDE":
            self.default_rule = "EXCLUDE"
        if Section.HasValue("IncludeFiles"):
            self.include_file_rules = SyncUtils.CombineFileSetRules(Section.GetConfig(), Section.GetValue("IncludeFiles"))
        if Section.HasValue("ExcludeFiles"):
            self.exclude_file_rules = SyncUtils.CombineFileSetRules(Section.GetConfig(), Section.GetValue("ExcludeFiles"))

        self.scan_results = None

    def __repr__(self):
        return self.path

    def IsValid(self)->bool:
        return self.valid

    def GetId(self)->str:
        return self.id

    def GetPath(self)->str:
        return self.path
    
    def GetChildren(self)->list:
        return self.children
    
    def GetExcludeFolderRules(self)->list:
        return self.exclude_folder_rules
    
    def GetFolderTagRules(self)->list:
        return self.folder_tag_rules
    
    def GetDefaultSetting(self)->list:
        return self.default_rule
    
    def GetIncludeFileRules(self)->list:
        return self.include_file_rules
    
    def GetExcludeFileRules(self)->list:
        return self.exclude_file_rules
    
    def PathExists(self)->bool:
        return self.path and os.path.isdir(self.path)
    
    def IsUnder(self, Folder)->bool:
        try:
            if Folder is self:
                return False
            this_path = self.GetPath()
            that_path = Folder.GetPath()
            if this_path != that_path:
                common_path = os.path.commonpath([this_path, that_path])
                if common_path == that_path:
                    return True
        except:
            pass
        return False
    
    def GetParent(self):
        return self.parent
    
    def AddChild(self, Folder):
        self.children.append(Folder)
        Folder.__set_parent(self)

    def __set_parent(self, Folder):
        if self.parent is None or Folder.IsUnder(self.parent):
            self.parent = Folder

    def reset_children(self):
        self.parent = None
        self.children = []

    def SetTargetPath(self, TargetPath):
        self.target_path = TargetPath

    def GetTargetPath(self):
        return self.target_path

    # SCAN RESULTS

    def SetScanFolders(self, Folders:list)->None:
        # expects list of {folder, tags}
        if isinstance(Folders, list):
            self.scan_results = Folders
            for fdict in self.scan_results:
                if self.target_path is None:
                    fdict['target'] = None
                else:
                    relpath = os.path.relpath(fdict['folder'], self.path)
                    if relpath=='.':
                        fdict['target'] = self.target_path
                    else:
                        fdict['target'] = os.path.join(self.target_path, relpath)

    def GetScanResults(self, SourceFolder=None, TargetFolder=None)->list:
        if SourceFolder:
            for results in self.scan_results:
                if results['folder'] == SourceFolder:
                    return results['files']
            return None
        elif TargetFolder:
            for results in self.scan_results:
                if results['target'] == TargetFolder:
                    return results['files']
            return None
        
        return self.scan_results
    
    def AddScanFiles(self, Folder, Files, CalcStat=True):
        if self.scan_results is not None:
            for folder in self.scan_results:
                if folder['folder']==Folder:
                    if CalcStat is False:
                        folder['files'] = Files
                    else:
                        files = []
                        for file in Files:
                            stat = 'NEW'
                            target_filepath = os.path.join(folder['target'], file[0])
                            if os.path.isfile(target_filepath):
                                filesize = os.path.getsize(target_filepath)
                                if file[1] == filesize:
                                    stat = 'SAME'
                                else:
                                    stat = 'MOD'
                            files.append((file[0], file[1], stat))
                        folder['files'] = files
                    return
