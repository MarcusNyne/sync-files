# Copyright (c) 2025 M. Fairbanks
#
# This source code is licensed under the Apache License, Version 2.0, found in the
# LICENSE file in the root directory of this source tree.

from m9lib import uFolder

from folder_section import *
from folder_scan import *

import re, fnmatch
from enum import IntEnum

'''
A FolderSet rule is some combination of the following parts, pipe delimited.  A part that doesn't match a known token is the rule itself:
- {rule}
- RECURSE: outcome of the rule applies recursively (this is the default)
- NORECURSE: do not apply outcome recursively
- TAG={tag}: apply tag to this folder (and possibly child folders based on RECURSE)

A rule is one of the following:
- A full path to a folder; eg. "c:\myfolder\subfolder\a"
- A terminating path, meaning a subpath at the end of a path; eg. "subfolder\a"
- A filemask, applied to the folder name; eg. "venv", "lo*"
- A regular expression, applied to the folder name; eg. "\w+-\d+"

Note that once a recursive trigger is satisfied, additional filters will not be evaluated
- So, if a tag is applied to a parent folder recursively, the filter will not be evaluated for child folders
- If multiple tags are found
'''

class FolderSetCondition(IntEnum):
    PATH = 1        # full path to folder
    MATCH = 2       # folder name match
    REGEX = 3       # folder name regex
    LASTLY = 4      # end of a path?
    TRUE = 5        # always True

class FolderSet:
    def __init__(self, RootPath:str|FolderSection, Rules:uConfigSection|list=None, Exclude:list=None, ApplyTags=True):
        # paths included in Exclude will be excluded from the scan
        # if Section is None, then all subfolders will be included
        self.root = SyncUtils.NormalizePath(RootPath) if isinstance(RootPath,str) else RootPath.GetPath()
        self.folders = []
        self.folder_tags = {}
        self.filters = []
        self.exclude = []
        if isinstance(Exclude, list):
            for path in Exclude:
                self.exclude.append(SyncUtils.NormalizePath(path))

        if Rules is None:
            self.__append_path(RootPath)
            subfolders = uFolder.FindFiles(RootPath, Recurse=True, Files=False, Folders=True)
            for subfolder in subfolders:
                self.__append_path(SyncUtils.NormalizePath(subfolder))
        else:
            self.filters = self.__process_filter_rules(Rules)
            self.start_filter_recursion()

            if ApplyTags:
                self.start_folder_tags_recursion()
        pass

    def ApplyFolderTags(self, Rules:uConfigSection|list=None):
        filters = self.__process_filter_rules(Rules, True)
        self.start_folder_tags_recursion(filters)

    def GetFolders(self)->list:
        return self.folders
    
    def GetFoldersWithTags(self)->list:
        return [{'folder':f, 'tags':self.GetFolderTags(f)} for f in self.folders]
    
    def GetFolderTags(self, inFolderPath)->set:
        if inFolderPath in self.folder_tags:
            return self.folder_tags[inFolderPath]
        return None
    
    def __process_filter_rules(self, Rules:uConfigSection|list, inTagsOnly=False)->list:
        filters = []
        lines = Rules
        if isinstance(lines, uConfigSection):
            lines = lines.GetTextBlock()
        if isinstance(lines, list):
            for line in lines:
                filter = self.__interpret_filter(line)
                if isinstance(filter, dict):
                    if inTagsOnly is False or filter['tag'] is not None:
                        filters.append(filter)
                else:
                    SyncUtils.Logger.WriteWarning(f"Folder filter failed interpretation: {line}")
        return filters

    def __in_exclude(self, inPath)->bool:
        for ex in self.exclude:
            # if SyncUtils.PathIsUnder(ex, inPath, SameIsUnder=True):
            if ex==inPath:
                return True
        return False
    
    def __append_path(self, inPath):
        if self.__in_exclude(inPath) is False:
            self.folders.append(inPath)

    def __apply_path_tag(self, inPath, inTag):
        if inPath in self.folder_tags:
            self.folder_tags[inPath].update({inTag})
        else:
            self.folder_tags[inPath] = {inTag}

    def __interpret_filter(self, inFilter)->dict|bool:
        split = self.split_filter(inFilter)
        if split is False:
            return False
        
        cond = split['cond']
        if cond is True:
            split['cond'] = FolderSetCondition.TRUE
            return split

        if '\\' in cond or '/' in cond:
            # test path
            try:
                if os.path.isabs(cond) is False:
                    cond = os.path.join(self.root, cond)
                cond = SyncUtils.NormalizePath(cond)
                if os.path.isdir(cond) is False:
                    # does not exist -- try other conditions
                    pass
                elif cond != self.root and SyncUtils.PathIsUnder(self.root, cond) is False:
                    # not within root -- try other conditions
                    pass
                else:
                    split['cond'] = FolderSetCondition.PATH
                    split['path'] = cond
                    return split
            except:
                pass

        cond = split['cond']
        if self.is_fnmatch(cond):
            split['cond'] = FolderSetCondition.MATCH
            split['match'] = cond
            return split
        
        lastly = cond.replace('/', '\\').casefold()
        if lastly.startswith('\\') is False:
            lastly = '\\' + lastly
        
        # try regex
        try:
            split['cond'] = FolderSetCondition.REGEX
            split['regex'] = re.compile(cond)
            split['lastly'] = lastly
            return split
        except:
            pass

        split['cond'] = FolderSetCondition.LASTLY
        split['lastly'] = lastly
        return split
    
    def is_fnmatch(self, inMatch)->bool:
        invalid_chars_pattern = r'[<>:"/\\|\x00-\x1F]'
        if re.search(invalid_chars_pattern, inMatch):
            return False
        
        return True

    def split_filter(self, inFilter:str)->dict|bool:
        # splits a string filter string into a dict describing the filter
        split = {'cond':None, 'recurse':True, 'tag':None}
        fsplit=inFilter.split('|')
        for x in range(len(fsplit)):
            part = fsplit[x].strip()
            pupper = part.upper()
            if part == "":
                pass # ignore empty condition
            elif pupper=="RECURSE":
                split['recurse'] = True
            elif pupper=="NORECURSE":
                split['recurse'] = False
            elif pupper.startswith("TAG=") and len(pupper)>4:
                split['tag'] = pupper[4:]
            elif split['cond'] is None:
                split['cond'] = fsplit[x]
            else:
                return False # extra condition in filter
        if split['cond'] is None:
            if 'tag' in split:
                split['cond'] = True
            else:
                return False # no condition specified
        
        return split

    def evaluate_filter(self, inPath, inFilter)->tuple|None:
        # returns: None: no match; True: match with recursion; False: match without recursion
        # returns ({recurse:bool}, {tag:str|None}) or None
        try:
            test = False
            match inFilter['cond']:
                case FolderSetCondition.TRUE:
                    test = True
                case FolderSetCondition.PATH:
                    if inFilter['path'] == inPath:
                        test = True
                case FolderSetCondition.MATCH:
                    if fnmatch.fnmatch(os.path.basename(inPath),inFilter['match']):
                        test = True
                case FolderSetCondition.REGEX:
                    if inFilter['regex'].match(os.path.basename(inPath)):
                        test = True
                    elif inPath.casefold().endswith(inFilter['lastly']):
                        test = True
                case FolderSetCondition.LASTLY:
                    if inPath.casefold().endswith(inFilter['lastly']):
                        test = True

            if test:
                return (inFilter['recurse'], inFilter['tag'])
        except:
            pass
        return None

    def start_filter_recursion(self)->list:
        if os.path.isdir(self.root):
            self.recurse_filter(self.root)

    def recurse_filter(self, inPath)->list:
        satisfied = False
        recurse = False
        for filter in self.filters:
            if satisfied is False or filter['recurse'] is True:
                test = self.evaluate_filter(inPath, filter)
                if test is not None:
                    satisfied = True
                    if test[0] is True:
                        recurse = True
                        break

        if satisfied:
            self.__append_path(inPath)
            if recurse:
                subfolders = uFolder.FindFiles(inPath, Recurse=True, Files=False, Folders=True)
                for subfolder in subfolders:
                    self.__append_path(SyncUtils.NormalizePath(subfolder))
                return

        subfolders = uFolder.FindFiles(inPath, Recurse=False, Files=False, Folders=True)
        for subfolder in subfolders:
            self.recurse_filter(SyncUtils.NormalizePath(subfolder))

    def start_folder_tags_recursion(self, inFilters=None):
        if inFilters is None:
            inFilters = self.filters
        for filter in inFilters:
            if filter['tag'] is not None:
                scan_folders = self.folders
                self.recurse_apply_tags(scan_folders, filter)

    def recurse_apply_tags(self, inFolders, filter):
        for x in range(len(inFolders)):
            path = inFolders[x]
            test = self.evaluate_filter(path, filter)
            if test is not None:
                if test[0] is False:
                    self.__apply_path_tag(path, test[1])
                else:
                    for path2 in inFolders:
                        if path2.startswith(path):
                            self.__apply_path_tag(path2, test[1])
                    folders = [inFolders[y] for y in range(len(inFolders)) if y>x and inFolders[y].startswith(path) is False]
                    self.recurse_apply_tags(folders, filter)
                    return
