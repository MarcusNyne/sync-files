# Copyright (c) 2025 M. Fairbanks
#
# This source code is licensed under the Apache License, Version 2.0, found in the
# LICENSE file in the root directory of this source tree.

from m9lib import uCommand, uCommandRegistry, uStringFormat, uCSV, uCSVFormat, uTimer

from folder_section import *
from folder_scan import *
from folder_set import *

import shutil

# Your command class name must match the section name in your config file
#   and be registered for uControl to create an instance of your command
#   object.
class FileSyncCommand(uCommand):
    
    def __init__(self):
        super().__init__()
        
    def imp_execute(self, in_preview):
        result = self.GetResult()
        config = self.GetConfig()

        # pre-format
        self._ymd = uStringFormat.String("{YMD}")
        self._lts = uStringFormat.String("{LTS}")
        self._tsm = uStringFormat.String("{TSM}")

        # initialize settings
        self.config_error_count = 0
        self.exclude_folder_rules = []

        self.mode = self.GetParam("Mode")
        if self.mode is None:
            self.mode = "REVIEW"
        self.mode = self.mode.upper()
        valid_modes = ["REVIEW", "BACKUP", "SYNC", "SYNCREVIEW"]
        if self.mode in valid_modes:
            self.LogParamString(f"Mode is [+VIOLET]{self.mode}[+]")
        else:
            self.__config_warning(f"Mode must be one of: {','.join(valid_modes)}")

        self.LogParam("TargetPath")
        self.target_path = self.GetParam("TargetPath")
        if self.target_path is None:
            if self.mode in ["REVIEW"]:
                self.LogParamString(f"TargetPath was not specified")
            else:
                self.__config_warning(f"TargetPath must specify a target location")
        elif uFolder.ConfirmFolder(self.target_path, self.mode!="REVIEW") is False:
            if self.mode in ["REVIEW"]:
                self.LogParamString(f"TargetPath does not exist: {self.target_path}")
            else:
                self.__config_warning(f"TargetPath does not exist: {self.target_path}")
        else:
            self.target_path = SyncUtils.NormalizePath(self.target_path)

        self.LogParam("CleanPath")
        self.clean_path = self.GetParam("CleanPath")
        if self.clean_path is None:
            if self.mode in ["SYNC", "BACKUP"]:
                self.__config_warning(f"CleanPath must specify a location for removed files")
        elif uFolder.ConfirmFolder(self.clean_path, self.mode=="SYNC") is False:
            if self.mode in ["SYNC", "BACKUP"]:
                self.__config_warning(f"CleanPath does not exist: {self.clean_path}")
            else:
                self.LogParamString(f"CleanPath does not exist: {self.clean_path}")
        else:
            self.clean_path = SyncUtils.NormalizePath(self.clean_path)
            if self.mode in ["SYNC", "BACKUP"] and self.target_path:
                try:
                    target_device = os.path.splitdrive(self.target_path)[0]
                    clean_device = os.path.splitdrive(self.clean_path)[0]
                    if target_device!=clean_device:
                        self.__config_warning(f"CleanPath must be on the same device as TargetPath: {clean_device} is not {target_device}")
                except:
                    self.__config_warning(f"Problem confirming CleanPath device: {self.clean_path}")

        self.LogParam("SourceFolders")
        self.source_folders = self.GetListParam("SourceFolders")
        if self.source_folders is None or len(self.source_folders)==0:
            self.__config_warning(f"No SourceFolders specified")

        self.LogParam("ExcludeFolders")
        self.exclude_folder_rules = SyncUtils.CombineFolderSetRules(config, self.GetParam("ExcludeFolders"))

        self.skip_files = self.GetBoolParam("LogSkippedFiles", False)
        self.LogParam("LogSkippedFiles", self.skip_files)

        self.disable_mover = self.GetBoolParam("DisableMover", False)
        self.LogParam("DisableMover", self.disable_mover)

        self.LogParam("OutputCSV")
        self.output_csv = self.GetParam("OutputCSV")
        self.output_csv = self.__string_format(self.output_csv)

        sections = []
        if self.source_folders is not None:
            for source_id in self.source_folders:
                section = config.GetSection("SourceFolder", source_id)
                if section is None:
                    self.__config_warning(f"SourceFolder {source_id} not found")
                else:
                    sections.append(section)

        SyncUtils.Logger = self.GetLogger()
        self.folderscan = FolderScan()

        folder:FolderSection = None
        for section in sections:
            folder = FolderSection (section)
            if folder.IsValid() is False:
                self.__config_warning(f"Folder configuration is invalid: {section}")
            elif folder.PathExists() is False:
                self.__config_warning(f"Folder path does not exist: {folder.GetPath()}")
            else:
                self.folderscan.AddFolder(folder)

        if self.config_error_count > 0:
            self.LogError(f"There were {self.config_error_count} configuration failures. Please correct configuration and run again.")
            return "Configuration failure"
        
        # establish target folders
        if self.target_path is not None:
            self.GetLogger().WriteSubHeader("Source Folders")
            top_count=0
            for folder in self.folderscan.GetFolders():
                if folder.GetParent() is None:
                    top_count += 1

            for folder in self.folderscan.GetFolders():
                target_path = self.target_path
                parent:FolderSection = folder.GetParent()
                if parent:
                    while True:
                        pparent = parent.GetParent()
                        if pparent is None:
                            break
                        parent = pparent
                    if top_count>1:
                        target_path = os.path.join(target_path, os.path.basename(parent.GetPath()))
                    target_path = os.path.join(target_path, os.path.relpath(folder.GetPath(), parent.GetPath()))
                else:
                    if top_count>1:
                        target_path = os.path.join(target_path, os.path.basename(folder.GetPath()))
                folder.SetTargetPath(target_path)
                self.LogMessage(f"[+BLUE][SourceFolder:{folder.GetId()}]: [+][+CYAN]{folder.GetPath()} => {target_path}[+]")
            self.GetLogger().WriteSubDivider()

        if self.exclude_folder_rules:
            if self.target_path:
                self.exclude_folder_rules.append(self.target_path)
            if self.clean_path:
                self.exclude_folder_rules.append(self.clean_path)
            self.folderscan.SetGlobalExclude(self.exclude_folder_rules)

        # scan folders    
        sf_ret = self.folderscan.ScanFolders()
        if sf_ret is False:
            self.LogError("Fatal error while scanning folders")
            return "Failed to scan folders"
        
        skip_files = None
        skip_folders = None
        if self.skip_files:
            skip_files,skip_folders = self.__calc_skip_files()

        remove_files = None
        remove_folders = None
        if self.mode in ["SYNC", "SYNCREVIEW"]:
            remove_files,remove_folders = self.__calc_remove_files()
            if self.disable_mover is False:
                self.__calc_mover_files(remove_files)
        
        # generate csv output
        self.__generate_csv(skip_files, skip_folders, remove_files, remove_folders)

        # write summary
        self.__write_summary(skip_files, remove_files)

        if self.mode in ["SYNC", "BACKUP"]:
            self.__perform_synchronization(self.mode, remove_files)

        # Return True, "Success", or a failure string.
        return "Success"
    
    def __config_warning(self, in_message):
        self.config_error_count += 1
        self.LogWarning(in_message)

    def __calc_skip_files(self):
        # generate a list of skipped source files, organized by folder
        skip_files = {}
        skip_folders = {}

        timer = uTimer()
        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Scanning skipped files...[+]")

        # only process top folders
        folder:FolderSection = None
        for folder in self.folderscan.GetFolders():
            if folder.GetParent() is None:
                source_path = folder.GetPath()
                all_files = uFolder.FindFiles(source_path, Recurse=True)
                all_files = uFolder.OrganizeFilesByPath(all_files)
                for folder_files in all_files:
                    folder_path = folder_files[0]
                    if self.__ignore_path(folder_path) is False:
                        results = folder.GetScanResults(SourceFolder=folder_path)
                        for file in folder_files[1]:
                            if results == None or self.__file_in_tuple_list(file, results) is False:
                                if folder_path not in skip_files:
                                    skip_files[folder_path] = []
                                    skip_folders[folder_path] = folder.GetId()
                                filepath = os.path.join(folder_path, file)
                                skip_files[folder_path].append((file, os.path.getsize(filepath), 'SKIP'))

        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Completed skipped file scan ({timer.GetElapsedString()})[+]")

        return (skip_files, skip_folders)

    def __calc_remove_files(self):
        # generate a list of files to remove from the target path, organized by folder
        remove_files = {}
        remove_folders = {}

        timer = uTimer()
        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Scanning files to remove ...[+]")

        # only process top folders
        folder:FolderSection = None
        for folder in self.folderscan.GetFolders():
            if folder.GetParent() is None:
                target_path = folder.GetTargetPath()
                all_files = uFolder.FindFiles(target_path, Recurse=True)
                all_files = uFolder.OrganizeFilesByPath(all_files)
                for folder_files in all_files:
                    folder_path = folder_files[0]
                    if self.__ignore_path(folder_path, IncludeTarget=True) is False:
                        results = folder.GetScanResults(TargetFolder=folder_path)
                        for file in folder_files[1]:
                            if results == None or self.__file_in_tuple_list(file, results) is False:
                                if folder_path not in remove_files:
                                    remove_files[folder_path] = []
                                    remove_folders[folder_path] = folder.GetId()
                                filepath = os.path.join(folder_path, file)
                                remove_files[folder_path].append((file, os.path.getsize(filepath), 'REMOVE'))

        SyncUtils.Logger.WriteLine(f"[+GREEN]=== Completed removed file scan ({timer.GetElapsedString()})[+]")

        return (remove_files, remove_folders)
    
    def __calc_clean_files(self):
        # generate a list of files to clean from the clean path, organized by folder
        # the clean list is used to calculate move
        clean_files = {}
        if self.clean_path is not None and uFolder.ConfirmFolder(self.clean_path, False):
            timer = uTimer()
            SyncUtils.Logger.WriteLine(f"[+GREEN]=== Scanning clean folder ...[+]")

            clean_path = self.clean_path
            all_files = uFolder.FindFiles(clean_path, Recurse=True)
            all_files = uFolder.OrganizeFilesByPath(all_files)
            for folder_files in all_files:
                clean_files[folder_files[0]] = []
                for file in folder_files[1]:
                    filepath = os.path.join(folder_files[0], file)
                    clean_files[folder_files[0]].append((file, os.path.getsize(filepath), 'CLEAN'))

            SyncUtils.Logger.WriteLine(f"[+GREEN]=== Completed clean file scan ({timer.GetElapsedString()})[+]")

        return clean_files
    
    def __calc_mover_files(self, remove_files):
        # updates scan results when a file has been moved
        if isinstance(remove_files, dict) and self.disable_mover is False:
            clean_files = self.__calc_clean_files()
            clean_files_folders = list(clean_files.keys())

            remove_files_folders = list(remove_files.keys())
            if len(remove_files_folders)>0:
                timer = uTimer()
                SyncUtils.Logger.WriteLine(f"[+GREEN]=== Scanning for misplaced files ...[+]")

                for folder in self.folderscan.folders:
                    results = folder.GetScanResults()
                    for folder in results:
                        for file_index in range(len(folder['files'])):
                            # first search in removed files
                            file = folder['files'][file_index]
                            if file[2]=='NEW':
                                find_file = (file[0],file[1],'REMOVE')
                                for remove_folder in remove_files_folders:
                                    try:
                                        index = remove_files[remove_folder].index(find_file)
                                        self.LogDetails(f"Found missing file \"{file[0]}\": {os.path.join(remove_folder,file[0])}")
                                        remove_files[remove_folder][index] = (file[0],file[1],'MOVE', folder['target'])
                                        folder['files'][file_index] = (file[0],file[1],"*MOVE")
                                        break
                                    except:
                                        pass

                            # then search in clean files
                            file = folder['files'][file_index]
                            if file[2]=='NEW':
                                find_file = (file[0],file[1],'CLEAN')
                                for clean_folder in clean_files_folders:
                                    try:
                                        index = clean_files[clean_folder].index(find_file)
                                        self.LogDetails(f"Found missing file \"{file[0]}\": {os.path.join(clean_folder,file[0])}")
                                        clean_files[clean_folder][index] = (file[0],file[1],'*CLEAN')
                                        folder['files'][file_index] = (file[0],file[1],"*MOVE")
                                        if clean_folder not in remove_files:
                                            remove_files[clean_folder] = []
                                            remove_files_folders.append(clean_folder)
                                        remove_files[clean_folder].append((file[0],file[1],'MOVE', folder['target']))
                                        break
                                    except:
                                        pass

                SyncUtils.Logger.WriteLine(f"[+GREEN]=== Completed misplaced file scan ({timer.GetElapsedString()})[+]")
        pass
    
    def __ignore_path(self, in_path, IncludeTarget=False):
        if not IncludeTarget and self.target_path and SyncUtils.PathIsUnder(self.target_path, in_path, True):
            return True
        if self.clean_path and SyncUtils.PathIsUnder(self.clean_path, in_path, True):
            return True
        return False

    def __file_in_tuple_list(self, in_file, in_list):
        for tup in in_list:
            if tup[0]==in_file:
                return True
        return False
    
    def __generate_csv(self, skip_files:dict=None, skip_folders:dict=None, remove_files:dict=None, remove_folders:dict=None):
        if self.output_csv is not None:
            timer = uTimer()
            SyncUtils.Logger.WriteLine(f"[+GREEN]=== Generating CSV ...[+]")

            filepath = uStringFormat.String(self.output_csv)
            uFolder.ConfirmFolder(os.path.dirname(filepath))
            self.LogMessage(f"Writing CSV output: {filepath}")
            format = uCSVFormat()
            format.SetColumns("Source, File, Size, Status, Source, Target")
            csv = uCSV(format)
            folder:FolderSection = None
            for folder in self.folderscan.folders:
                results = folder.GetScanResults()
                for result_folder in results:
                    for file in result_folder['files']:
                        if file[2].startswith('*') is False:
                            self.__csv_addrow(csv, [folder.GetId(), file[0], file[1], file[2] if len(file)>2 else "", result_folder['folder'], result_folder['target']])

            if skip_files:
                for skip_folder in list(skip_files.keys()):
                    for file in skip_files[skip_folder]:
                        self.__csv_addrow(csv, [skip_folders[skip_folder] if (skip_folders is not None and skip_folder in skip_folders) else "", file[0], file[1], file[2] if len(file)>2 else "", skip_folder, ""])

            if remove_files:
                for remove_folder in list(remove_files.keys()):
                    for file in remove_files[remove_folder]:
                        self.__csv_addrow(csv, [remove_folders[remove_folder] if (remove_folders is not None and remove_folder in remove_folders) else "", file[0], file[1], file[2] if len(file)>2 else "", remove_folder, file[3] if len(file)>3 else ""])

            ret = csv.WriteFile(filepath)
            if ret is False:
                self.LogError(f"Failed writing CSV output: {filepath}")
            else:
                self.LogMessage(f"Wrote {ret} rows to CSV output")

            SyncUtils.Logger.WriteLine(f"[+GREEN]=== Wrote CSV file ({timer.GetElapsedString()})[+]")

            return ret
        
        return None
    
    def __csv_addrow(self, csv:uCSV, row:list):
        row = [f"\"{r}\"" if (isinstance(r, str) and ',' in r) else r for r in row]
        if csv.AddRow(row) is False:
            pass
    
    def __write_summary(self, skip_files:dict=None, remove_files:dict=None):
        all_folders = 0
        all_files = 0
        all_stats = ['NEW', 'MOD', 'SAME']
        if skip_files is not None:
            all_stats.append('SKIP')
        if remove_files is not None:
            if self.disable_mover is False:
                all_stats.append('MOVE')
            all_stats.append('REMOVE')
        sum_stat = {}
        for stat in all_stats:
            sum_stat[stat] = {'files':0, 'size':0}

        folder:FolderSection = None
        for folder in self.folderscan.folders:
            results = folder.GetScanResults()
            for folder in results:
                all_folders += 1
                for file in folder['files']:
                    all_files += 1
                    if len(file)>2 and file[2] in all_stats:
                        sum_stat[file[2]]['files'] += 1
                        sum_stat[file[2]]['size'] += file[1]

        if skip_files:
            for remove_folder in list(skip_files.keys()):
                all_folders += 1
                for file in skip_files[remove_folder]:
                    all_files += 1
                    sum_stat['SKIP']['files'] += 1
                    sum_stat['SKIP']['size'] += file[1]

        if remove_files:
            for remove_folder in list(remove_files.keys()):
                all_folders += 1
                for file in remove_files[remove_folder]:
                    all_files += 1
                    sum_stat[file[2]]['files'] += 1
                    sum_stat[file[2]]['size'] += file[1]

        color = "CYAN"
        self.LogMessage(f"[+{color}]Scan Summary:[+]")
        self.LogMessage(f"[+{color}]- {all_files} files found in {all_folders} folders[+]")
        for stat in all_stats:
            if sum_stat[stat]['files']==0:
                self.LogMessage(f"[+{color}]- [+BLUE]{stat}[+{color}]: [+GREY]No files[+]")
            else:
                self.LogMessage(f"[+{color}]- [+BLUE]{stat}[+{color}]: {sum_stat[stat]['files']} files; {uStringFormat.Bytes(sum_stat[stat]['size'])}[+]")

    def __perform_synchronization(self, Mode:str, RemoveFiles:dict):
        try:
            timer = uTimer()
            source_folder:FolderSection = None
            total_file_size = 0
            total_file_count = 0
            for source_folder in self.folderscan.folders:
                results = source_folder.GetScanResults()
                for folder in results:
                    for file in folder['files']:
                        if file[2] in ['NEW', 'MOD']:
                            total_file_count += 1
                            total_file_size += file[1]

            total_move_file_count = 0
            total_remove_file_count = 0
            if RemoveFiles is not None:
                for folder in list(RemoveFiles.keys()):
                    for file in RemoveFiles[folder]:
                        match file[2]:
                            case 'MOVE':
                                total_move_file_count += 1
                            case 'REMOVE':
                                total_remove_file_count += 1

            if total_file_count+total_move_file_count+total_remove_file_count==0:
                self.LogMessage(f"[+GREEN]=== No files found to synchronize[+]")
                return True

            self.LogMessage(f"[+GREEN]=== Performing {Mode} operation[+]")
            self.LogMessage(f"{total_file_count} files to copy")
            self.LogMessage(f"Copying {uStringFormat.Bytes(total_file_size).replace(' ', '')} total bytes")
            target_device = os.path.splitdrive(self.target_path)[0]
            _,_,bytes_free = shutil.disk_usage(target_device)
            self.LogMessage(f"Target device is {target_device} ({uStringFormat.Bytes(bytes_free).replace(' ', '')} bytes free)")
            if total_file_size>(bytes_free*0.95):
                self.LogError(f"Not enough space on device to continue {Mode} operation")
                return False

            if total_file_count>0:
                progress_size = 0
                progress_step = 20
                progress_next = progress_step
                for source_folder in self.folderscan.folders:
                    results = source_folder.GetScanResults()
                    for folder in results:
                        for file in folder['files']:
                            if file[2]=='MOD':
                                self.__clean_file(folder['target'], file[0])

                            if file[2] in ['NEW', 'MOD']:
                                source_file = os.path.join(folder['folder'], file[0])
                                target_file = os.path.join(folder['target'], file[0])
                                self.LogDetails(f"Copying source file: {source_file}")
                                if uFolder.ConfirmFolder(folder['target'], True) is False:
                                    self.LogError(f"Unable to create target folder: {folder['target']}")
                                retry = 9
                                while retry>0:
                                    try:
                                        shutil.copyfile(source_file, target_file)
                                        progress_size += file[1]
                                        if (progress_size*100)/total_file_size>progress_next:
                                            print(f"{progress_next}%..")
                                            progress_next += progress_step
                                        break
                                    except Exception as e:
                                        self.LogError(f"Unexpected failure while copying \"{os.path.basename(source_file)}\" (retry={10-retry}): {str(e)}")
                                    retry -= 1
                                if retry==0:
                                    self.LogError(f"Unable to copy file after retries:{source_file}")
                                    return False

            if total_move_file_count+total_remove_file_count>0:
                for folder in list(RemoveFiles.keys()):
                    for file in RemoveFiles[folder]:
                        if file[2]=='MOVE':
                            source_file = os.path.join(folder, file[0])
                            target_file = os.path.join(file[3], file[0])
                            if uFolder.ConfirmFolder(file[3], True) is False:
                                self.LogError(f"Unable to create target folder: {file[3]}")
                                self.LogError(f"=== {timer.GetElapsedString()}")
                                return False
                            else:
                                self.LogDetails(f"Moving misplaced file: {source_file}")
                                try:
                                    shutil.move(source_file, target_file)
                                except Exception as e:
                                    self.LogError(f"Failed to move misplaced file:{source_file}: {str(e)}")
                                    self.LogError(f"=== {timer.GetElapsedString()}")
                                    return False
                        elif file[2]=='REMOVE':
                            if self.__clean_file(folder, file[0]) is False:
                                self.LogError(f"Failed attempting to clean file: {os.path.join(folder, file[0])}")
                                self.LogError(f"=== {timer.GetElapsedString()}")
                                return False
                            
            # remove empty folders
            for source_folder in self.folderscan.folders:
                empty_folders = uFolder.DestroyEmptyFolders(source_folder.GetTargetPath())
                for folder in empty_folders:
                    self.LogDetails(f"Destroyed empty folder: {folder}")

            self.LogMessage(f"[+GREEN]=== Completed {Mode} operation ({timer.GetElapsedString()})[+]")

        except Exception as e:
            self.LogError(f"Unexpected failure: {str(e)}")
            self.LogError(f"=== {timer.GetElapsedString()}")
            return False

        return True
    
    def __clean_file(self, TargetFolder, FileName):
        if self.clean_path is None:
            self.LogError(f"CleanPath was not configured")
            return False

        rel_path = os.path.relpath(TargetFolder, self.target_path)
        clean_path = os.path.join(self.clean_path, rel_path)
        confirmed = uFolder.ConfirmFolder(clean_path,Create=True)
        if confirmed is False:
            self.LogError(f"Unable to create clean folder: {clean_path}")
        clean_file = os.path.join(clean_path, FileName)
        sext = os.path.splitext(clean_file)
        if os.path.exists(clean_file):
            sext = os.path.splitext(clean_file)
            index = 0
            while os.path.exists(clean_file):
                index += 1
                clean_file = f"{sext[0]}-{index:03d}{sext[1]}"
            self.LogDetails(f"Clean file exists, using temporary filename: {clean_file}")
        target_file = os.path.join(TargetFolder, FileName)
        self.LogDetails(f"Cleaning target file: {target_file}")
        shutil.move(target_file, clean_file)
        return True
    
    def __string_format(self, inString):
        inString = inString.replace("{YMD}", self._ymd)
        inString = inString.replace("{LTS}", self._lts)
        inString = inString.replace("{TSM}", self._tsm)
        return inString

uCommandRegistry.RegisterCommand(FileSyncCommand)
