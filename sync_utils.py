# Copyright (c) 2025 M. Fairbanks
#
# This source code is licensed under the Apache License, Version 2.0, found in the
# LICENSE file in the root directory of this source tree.

from m9lib import uConfig, uLogger, uConfigSection

import os, pathlib

class SyncUtils:
    Logger:uLogger = None

    @staticmethod
    def NormalizePath(Path:str|tuple)->str:
        if isinstance(Path, tuple):
            Path = os.path.join(Path[1], Path[0])
        return str(pathlib.Path(Path).resolve())

    @staticmethod
    def PathIsUnder(RootPath:str, ChildPath:str, SameIsUnder=False)->bool:
        try:
            RootPath = SyncUtils.NormalizePath(RootPath)
            ChildPath = SyncUtils.NormalizePath(ChildPath)
            if RootPath == ChildPath:
                return SameIsUnder
            else:
                common_path = os.path.commonpath([RootPath, ChildPath])
                if common_path == RootPath:
                    return True
        except:
            pass
        return False
    
    @staticmethod
    def CombineConfigurationList(Config:uConfig, List:str|list, SectionName:str)->list:
        '''
        Takes a list or comma delimited string that contains a combination of strings and section ids
        Returns a list of strings combined from the original list:
        - if a list element is the id of a section of type **SectionName**, include the contents of the list
        - otherwise, the list element is included in the new list
        '''
        combined_rules = []
        rules_list = List
        if isinstance(rules_list, str):
            rules_list = List.split(",")
        if isinstance(rules_list, list):
            for r in rules_list:
                r = r.strip()
                if r!="":
                    section = Config.GetSection(SectionName, r)
                    if isinstance(section, uConfigSection):
                        if section.IsTextBlock():
                            combined_rules.extend(section.GetTextBlock())
                    else:
                        combined_rules.append(r)
        return combined_rules

    @staticmethod
    def CombineFolderSetRules(Config:uConfig, Rules:str|list):
        return SyncUtils.CombineConfigurationList(Config, Rules, "FolderSet")

    @staticmethod
    def CombineFileSetRules(Config:uConfig, Rules:str|list):
        return SyncUtils.CombineConfigurationList(Config, Rules, "FileSet")
