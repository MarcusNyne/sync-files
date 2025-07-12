# Copyright (c) 2025 M. Fairbanks
#
# This source code is licensed under the Apache License, Version 2.0, found in the
# LICENSE file in the root directory of this source tree.

from m9lib import uFolder, uStringFormat

from sync_utils import *
from folder_set import *

import re, fnmatch
from enum import IntEnum

'''
A FileSet rule is any number of pipe-separated conditions.  All conditions must be True for the filter to be satisfied.

Condition may be any number of:
- A filemask; eg. "venv", "lo*"
- A regular expression applied to the file name (not path); eg. "\w+-\d+"
- REGEX: If a condition doesn't satisfy conditions of a filemask it will be assumed to be a regular expression; to be explicit, prefix with REGEX:
- TAG: Folder has specified tag
- NTAG: Folder does not have specified tag
- NO_TAG: Folder does not have any tag
- PARENT: Parent folder name
- SIZE_GT: File size greater than
- SIZE_LT: File size less than or equal to
'''

class FileSetCondition(IntEnum):
    MASK = 1        # full path to folder
    REGEX = 2       # file name regex
    TAG = 3         # folder has specified tag
    NTAG = 4        # folder does not have specified tag
    NO_TAG = 5      # folder does not have any tag
    SIZE_GT = 6     # file size greater than
    SIZE_LT = 7     # file size less than or equal to
    PARENT = 8      # parent folder name

class FileSetRules:
    def __init__(self, IncludeByDefault:bool=True, IncludeRules:uConfigSection|list=None, ExcludeRules:uConfigSection|list=None):
        # files are organized by folder [{path}]
        self.valid = False

        self.include_by_default = IncludeByDefault

        # establish rules
        self.include_rules = self.__process_filter_rules(IncludeRules)
        if self.include_rules is False:
            return

        # establish rules
        self.exclude_rules = self.__process_filter_rules(ExcludeRules)
        if self.exclude_rules is False:
            return

        self.valid = True

    def IsValid(self)->bool:
        return self.valid

    def GetFolders(self)->list:
        return self.folders
    
    def __process_filter_rules(self, Rules:uConfigSection|list, inTagsOnly=False)->list:
        rules = []
        lines = Rules
        if isinstance(lines, uConfigSection) and lines.IsTextBlock():
            lines = lines.GetTextBlock()
        if isinstance(lines, list):
            for line in lines:
                rule = self.__interpret_filter(line)
                if isinstance(rule, list) and len(rule)>0:
                    rules.append(rule)
                else:
                    SyncUtils.Logger.WriteWarning(f"File filter rule failed interpretation: {line}")
                    return False
        else:
            return False
        
        return rules

    def __interpret_filter(self, inFilter:str)->dict|bool:
        filters = []
        fsplit = [f.strip() for f in inFilter.split('|')]
        for f in fsplit:
            if f!="":
                fdict = self.parse_filter(f)
                if fdict is False:
                    SyncUtils.Logger.WriteWarning(f"Invalid file filter condition: {f}")
                    return False
                filters.append(fdict)

        return filters
    
    def is_fnmatch(self, inMatch)->bool:
        invalid_chars_pattern = r'[<>:"/\\|\x00-\x1F]'
        if re.search(invalid_chars_pattern, inMatch):
            return False
        
        return True
    
    def split_filter(self, inFilter):
        if inFilter.upper().strip()=="NO_TAG":
            return ("NO_TAG", None)
        colon = inFilter.find(":")
        if colon==-1:
            colon = inFilter.find("=")
        if colon==-1:
            return False
        part1 = inFilter[:colon].strip()
        part2 = inFilter[colon+1:].strip()
        return (part1,part2)

    def parse_filter(self, inFilter:str)->dict|bool:
        # parses a string filter and returns a dict describing the filter
        try:
            fsplit = self.split_filter(inFilter)
            if fsplit:
                match fsplit[0]:
                    case 'REGEX':
                        inFilter = fsplit[1]
                    case 'TAG':
                        return {'cond':FileSetCondition.TAG, 'tag':fsplit[1].upper()}
                    case 'NTAG':
                        return {'cond':FileSetCondition.NTAG, 'tag':fsplit[1].upper()}
                    case 'NO_TAG':
                        return {'cond':FileSetCondition.NO_TAG}
                    case 'PARENT':
                        return {'cond':FileSetCondition.PARENT, 'name':fsplit[1].lower()}
                    case 'SIZE_GT':
                        bytes = uStringFormat.ParseBytes(fsplit[1])
                        if bytes is False:
                            return False
                        return {'cond':FileSetCondition.SIZE_GT, 'bytes':bytes}
                    case 'SIZE_LT':
                        bytes = uStringFormat.ParseBytes(fsplit[1])
                        if bytes is False:
                            return False
                        return {'cond':FileSetCondition.SIZE_LT, 'bytes':bytes}
            elif self.is_fnmatch(inFilter):
                return {'cond':FileSetCondition.MASK, 'mask':inFilter}

            return {'cond':FileSetCondition.REGEX, 'regex':re.compile(inFilter)}
        except:
            pass
        
        return False
    
    def ScanFiles(self, inFolderPath, inFolderTags=None):
        # scans a folder, returning files that match the specified conditions
        # returns [(name, size)]
        SyncUtils.Logger.WriteDetails(f"[+VIOLET]***** SCAN FILES: {inFolderPath}{'' if inFolderTags is None else ' [+RED]'+str(inFolderTags)+'[+]'}[+]")
        if inFolderTags is None:
            inFolderTags = set()
        log_rules = False
        ret_files = []
        files = uFolder.FindFiles(inFolderPath)
        for fname,_ in files:
            if log_rules:
                SyncUtils.Logger.WriteDetails(f"[+GREEN]*** FILE: {fname}[+]")
            satisfied = self.include_by_default
            if self.include_by_default:
                if log_rules:
                    SyncUtils.Logger.WriteDetails(f"[+CYAN]+ Included by default[+]")
                test = self.test_filter_rules(self.exclude_rules, fname, inFolderPath, inFolderTags)
                if test:
                    if log_rules:
                        SyncUtils.Logger.WriteDetails(f"[+RED]- Excluded by rule: {test}[+]")
                    satisfied = False
                    test = self.test_filter_rules(self.include_rules, fname, inFolderPath, inFolderTags)
                    if test:
                        if log_rules:
                            SyncUtils.Logger.WriteDetails(f"[+CYAN]+ Included by rule: {test}[+]")
                        satisfied = True
            else:
                if log_rules:
                    SyncUtils.Logger.WriteDetails(f"[+RED]- Excluded by default[+]")
                test = self.test_filter_rules(self.include_rules, fname, inFolderPath, inFolderTags)
                if test:
                    if log_rules:
                        SyncUtils.Logger.WriteDetails(f"[+CYAN]+ Included by rule: {test}[+]")
                    satisfied = True
                    test = self.test_filter_rules(self.exclude_rules, fname, inFolderPath, inFolderTags)
                    if test:
                        if log_rules:
                            SyncUtils.Logger.WriteDetails(f"[+RED]- Excluded by rule: {test}[+]")
                        satisfied = False

            if satisfied:
                fsize = os.path.getsize(os.path.join(inFolderPath, fname))
                ret_files.append((fname, fsize))
            pass
            
        SyncUtils.Logger.WriteDetails(f"[+BLUE]* {len(ret_files)} files found[+]")
        return ret_files
    
    def test_filter_rules(self, filter_rules, file_name, path, tags:set=None):
        if len(filter_rules)==0:
            return False
        
        # returns true if any of the specified rules are satisfied
        # a rule is satisfied when all parts of the rule are satisfied

        filesize = None

        for rule in filter_rules:
            try:
                if len(rule)>1 or rule[0]!="":
                    success = True
                    for part in rule:
                        match part['cond']:
                            case FileSetCondition.MASK:
                                if fnmatch.fnmatch(file_name, part['mask']) is False:
                                    success = False
                                    break
                            case FileSetCondition.REGEX:
                                m = part['regex'].match(file_name)
                                if part['regex'].match(file_name) is None:
                                    success = False
                                    break
                            case FileSetCondition.TAG:
                                if part['tag'] not in tags:
                                    success = False
                                    break
                            case FileSetCondition.NTAG:
                                if part['tag'] in tags:
                                    success = False
                                    break
                            case FileSetCondition.NO_TAG:
                                if len(tags)>0:
                                    success = False
                                    break
                            case FileSetCondition.PARENT:
                                if fnmatch.fnmatch(os.path.basename(path).lower(), part['name']) is False:
                                    success = False
                                    break
                            case FileSetCondition.SIZE_GT:
                                if filesize is None:
                                    filesize = self.__filesize(path, file_name)
                                if filesize is False or filesize<=part['bytes']:
                                    success = False
                                    break
                            case FileSetCondition.SIZE_LT:
                                if filesize is None:
                                    filesize = self.__filesize(path, file_name)
                                if filesize is False or filesize>part['bytes']:
                                    success = False
                                    break
                            case _: # unknown condition
                                success = False
                                break

                    if success:
                        return rule
            except:
                pass
        
        return False       

    def __filesize(self, path, name):
        try:
            return os.path.getsize(os.path.join(path, name))
        except:
            return False
