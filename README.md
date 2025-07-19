# sync-files
 
## Summary

This project performs a rule-based file backup or file synchronization.

The project is a demonstration of how to use [**m9lib**](https://github.com/MarcusNyne/m9lib) as a batch processing framework.

This project does NOT delete files.  It only copies and moves files.  Files to be deleted are moved to a "clean" folder.

Although there has been a good-faith effort to provide a functional example that might be used for file maintenance, this project is provided <code style="color: red">**AS IS**</code> with no warranty expressed or implied. <code style="color: red">**USE AT YOUR OWN RISK**</code>

$${\large\textcolor{black}{\spadesuit}\textcolor{red}{\space DEMONSTRATION \space PROJECT \space}\textcolor{black}{\spadesuit}\textcolor{red}{\space USE \space AT \space YOUR \space OWN \space RISK \space}\textcolor{black}{\spadesuit}}$$

Other pages in this document:
- [Folder Rules](docs/folder-rules.md): Rules for excluding folders and applying folder tags.
- [File Rules](docs/file-rules.md): Rules for including and excluding files.

## Control Basics

This application uses the [**m9lib**](https://github.com/MarcusNyne/m9lib) batch processing framework.  Basic elements of this framework are:

**Configuration**.  A configuration file drives application behavior.  This includes a "control section" and "command section".
- A path to the configuration file can be passed into file_sync.py as an argument.  If not specified, it defaults to "sync-files.ini".

**Control**.  A **uControl** object is constructed with two parameters:
- The name of the control section in configuration
- A filepath to the configuration file

Within the control section of the configuration file (`[FileSync]`), you will find application-level settings that are typical of **m9lib** projects.
- **Logfile**: Path to a log file.  This can be made unique per run by using placeholders such as `{YMD}`, `{LTS}`, and/or `{TSM}`.
- **Execute**: The command(s) to run.  Can be one or more section ids (comma-delimited).

**Command**.  The command(s) to execute.
- The command name identifies the command class, in this case `[FileSyncCommand]`.
- Command parameters are specific to the command.

## Configuration Basics

[**m9ini**](https://github.com/MarcusNyne/m9ini) is an object-oriented INI format that allows sections to contain a section name and section id in the format `[{name}:{id}]`.  This project relies on sections of known names such as `[FileSyncCommand]`, `[SourceFolder]`, `[[FolderSet]]`, and `[[FileSet]]`.  When an id references another section, the section name is presumed based on context.  For example, when specifying the id for folder rules, the section name is assumed to be `[[FolderSet]]`.

There are two types of INI sections: property based sections with name value pairs, and "text blocks". A text block section contains double-square-brackets (`[[ ]]`) in the section header.  These sections do not have named properties, but are simply lines of text.

In this example, `[FileSyncCommand].SourceFolders` contains an id to a `[SourceFolder]` and `[SourceFolder].ExcludeFolders` contains an id to a `[[FolderSet]]`, which is a text block.

```ini
# control section
[FileSync]
Logfile={YMD}-MyLogfile.txt
Execute=run

# command section
[FileSyncCommand:run]
SourceFolders=folder_a

[SourceFolder:folder_a]
ExcludeFolders=bad_folders

[[FolderSet:bad_folders]]
temp
tmp
bin*
```

## Command Section

The command section for a job is `[FileSyncCommand]`. This section provides run-level configuration and specifies the source folders to include in the operation.

The operation **Mode** may be one of:
- ***REVIEW***: Scan folders and files; Use with **OutputCSV** or check the log for a preview of files to process
- ***BACKUP***: Files are copied from source folders to the target location
- ***SYNC***: Files are copied from source folders to the target location; any files on the target that are not found in the source are marked for deletion
- ***SYNCREVIEW***: Similar to ***REVIEW*** but includes files that would be removed in a ***SYNC*** operation

| Config | Meaning | Default |
| --- | --- | --- |
| **Mode** | Operation mode | ***REVIEW*** |
| **SourceFolders** | A list of source folders ids to use in this operation | *required* |
| **TargetPath** | Root path of target location | *required* |
| **CleanPath** | Root path for removed files | *required* for *SYNC* mode |
| **ExcludeFolders** | Global rules for excluding folders | No global exclusion rules |
| **OutputCSV** | Create a CSV file detailing files included in the operation | Do not create CSV output |
| **DisableMover** | Mover looks for misplaced files on the target path before copying a source file | *False* |
| **LogSkippedFiles** | Report on skipped files in log/csv | *False* |

**TargetPath** must be accessible for ***BACKUP***, ***SYNC***, and ***SYNCREVIEW***.

```ini
[FileSyncCommand:run]
SourceFolders=folder_a, folder_b
TargetPath=E:\
ExcludeFolders=tmp, temp

[SourceFolder:folder_a]
Path=D:\Games\Data

[SourceFolder:folder_b]
Path=D:\Games\Data\Adventure\Quest
```

## Target Folders

**TargetPath** specifies the root target folder for the operation.  Files from source folders will be copied under this path.
- Source folders that are under other source folders will follow the same structure in the target location
- If there is exactly one source folder (or all other source folders are under this one), then source folder files will be placed directly under the **TargetPath**
- If there are multiple top-level source folders, then source folder files will be placed in the **TargetPath** under a folder based on the original folder name

```ini
# in this example, there is only one top-level source folder since folder_b is nested under folder_a
[FileSyncCommand:run]
SourceFolders=folder_a, folder_b
TargetPath=E:\

[SourceFolder:folder_a]
Path=D:\Games\Data
# target root for folder_a will be E:\

[SourceFolder:folder_b]
Path=D:\Games\Data\Adventure\Quest
# target root for folder_b will be E:\Adventure\Quest
```

```ini
# in this example, there are two top-level source folders (they are not nested)
[FileSyncCommand:run]
SourceFolders=folder_a, folder_b
TargetPath=E:\

[SourceFolder:folder_a]
Path=D:\Games\Data
# target root will be E:\Data

[SourceFolder:folder_b]
Path=D:\Fun\Information
# target root will be E:\Information
```

## Clean Folder

A "clean folder" is specified by **CleanFolder** in configuration.  A clean folder is only required for ***SYNC*** and ***BACKUP*** modes.

The difference between ***SYNC*** and ***BACKUP*** is that ***SYNC*** will identify and "remove" files in the target location that are not in the source location.  No files are actually deleted by this application.  Instead, they are moved into the clean folder.

In both cases if a file is being copied to the target where the file name is the same, but the size is difference, the file will be copied to the clean folder instead of being overwritten.

The path of the removed file in the clean folder will mimic the original path of the file.  If a file of this name already exists in the clean folder, it will be given a numerical postfix so that it has a unique name.

The clean folder must be on the same device as the target path.

## Generate CSV Output

Generating CSV output is helpful in testing synchronization rules.  The CSV file will contain a list of files found and their status.

The output filename may include **uStringFormat.String()** tokens such as *{YMD}*, *{LTS}*, and *{TSM}*.

## Source Folder Configuration

A source folder contains files to be synced.  Configuration provides rules for:
- Excluding folders from synchronization
- Tagging folders with labels that can be used in file inclusion rules
- Including and excluding files

If source folder is nested within the path of another source folder, then the any configuration or rules applicable to the parent source folder are not applicable to the child source folder and subfolders.

| Config | Meaning | Default |
| --- | --- | --- |
| **Path** | Root path of source folder | *required* |
| **ExcludeFolders** | Rules for excluding folders under **Path** | All folders are included |
| **FolderTags** | Rules for applying folder tags | No tags are applied |
| **DefaultRule** | Are files included by default, or excluded by default? | *INCLUDE* |
| **IncludeFiles** | Rules for including files | Relies on **DefaultRule** |
| **ExcludeFiles** | Rules for excluding files | Relies on **DefaultRule** |

By default, all subfolders of **Path** are included in syncronization until a subfolder is found to be the root of another "source folder".

**ExcludeFolders** specifies rules for excluding subfolders from synchronization.  See [Folder Rules](docs/folder-rules.md).

**FolderTags** specifies rules for tagging subfolders.  A folder tag can be used in file rules.
- The format of these rules are the same as [Folder Rules](docs/folder-rules.md).
- Folder tags are not applied to excluded folders.

**DefaultRule** controls how file rules are applied.
- Can be set to *INCLUDE* or *EXCLUDE*.  The default is *INCLUDE*.
- If set to *INCLUDE*, then files are included by default => exclusion rules are applied => inclusion rules are applied.
- If set to *EXCLUDE*, then files are excluded by default => inclusion rules are applied => exclusion rules are applied.

**IncludeFiles**, and **ExcludeFiles** are [File Rules](docs/file-rules.md) that determine if files should be included in a sync job.  Files in excluded folders are not considered.

When **LogSkippedFiles** is *True*, information about skipped files will be calculated and included in reports. A file is "skipped" if it is present in an excluded folder, or the file is excluded based on file rules. Reporting includes:
- Log summary of files based on status (you may also see this in console output depending on log settings).
- File will be present in CSV output with a stat of "SKIP".

"Mover" is a feature of ***SYNC*** operations that is enabled by default.  Before copying a file from the source that is not in the target location, the file will be searched for across the target and clean locations to see if it is present, but in the wrong location.  If it is found, it is moved the the correct location.  The file is considered the same if the name and size match.  This makes a ***SYNC*** operation more efficient when files in the source location have been reorganized.  Rather than copy all the files again, the target folder structure is reorganized to match the source
- To disable this feature, set **DisableMover** to *True*.  You may wish to do this if the assumption about file name and size is not correct for your files.
- This may be referred to as a "misplaced" file in logs.

```ini
# by default, all subfolders and files are included
[SourceFolder:folder_a]
Path=D:\Games\Data

# because folder_b is within folder_a, folder_a rules do not apply under this path
# certain folders will be excluded
# by default, exclude files, but include image files, and MPG files less than 2mb in size
[SourceFolder:folder_b]
Path=D:\Games\Data\Adventure\Quest
ExcludeFolders=tmp,temp,$*
DefaultRule=EXCLUDE
IncludeFiles=image_files,*.mpg|SIZE_LT:2mb

# include PNG, GIF, JPG, and JPEG files
[[FileSet:image_files]]
REGEX:.+\.jpe?g
*.png
*.gif
```

This example demonstrates folder tagging.  The purpose of applying a tag is to include the tag in a file rule.

```ini
# include all subfolders (no exclusion rules)
# the tag "blood" is applied to folders named horror (but not any subfolders)
# the tag "blades" is applied to any folder starting with "adv" and applies to all subfolders (by default)
# because we only want files that match rules, use the EXCLUDE default rule
# include JPG files in folders tagged with "blood" folder (which is the horror folder)
# include files in folders tagged with "blades" that match "*.m*" and are less than 5mb in size
# include all "txt" files
[SourceFolder:my_folder]
Path=D:\Games\Data
TagFolders=horror|TAG=blood|NORECURSE, adv*|TAG=blades
DefaultRule=EXCLUDE
IncludeFiles=TAG:blood|*.jpg, TAG:blades|*.m*|SIZE_LT:5mb, *.txt
```
