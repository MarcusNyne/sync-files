# Folder rules

Folder rules are used in these contexts:
- `[FileSyncCommand].ExcludeFolders`: folders matching a rule will be excluded from all source folders
- `[SourceFolder].ExcludeFolders`: folders matching a rule will be excluded from this source folder
- `[SourceFolder].FolderTags`: tag folders with a custom label that match a rule

## Use

Folder rules is a comma-delimited list of:
- a rule
- the id of a `[[FolderSet]]` section containing rules

## Formatting

An individual folder rule is a pile-delimited combination of a matching condition and optional rule modifiers, specified in any order.

A matching condition may be one of:
- A full path to a folder; eg. "c:\myfolder\subfolder\a"
- A terminating path, meaning a subpath at the end of a path; eg. "subfolder\a"
- A filemask, applied to the folder name; eg. "venv", "lo*"
- A regular expression, applied to the folder name; eg. "\w+-\d+"

Available modifiers are:
- `RECURSE`: outcome of the rule applies recursively (this is the default)
- `NORECURSE`: do not apply outcome recursively
- `TAG={tag}`: apply tag to this folder (and possibly child folders based on `RECURSE`)

When a match is found, if `RECURSE` is used (this is the default), then the outcome will be applied to all child folders of the matching folder.

There are some differences with how this is applied based on context:
- ***ExcludeFolders***: a condition is required; `TAG` modifiers will be ignored
- ***FolderTags***: a condition is optional (when not specified, all folders are tagged); A `TAG` modifier is expected

## Examples

```ini
# folders named "bad*" will be excluded, including all subfolders
# folders named "temp" will be excluded, but subfolders may be included as long as they don't match other exclusion rules
[FileSyncCommand:run]
SourceFolders=folder_a, folder_b
TargetPath=E:\
ExcludeFolders=bad*,temp|NORECURSE

# exclude folders that match rules from: [FileSyncCommand].ExcludeFolders and [SourceFolder:folder_a].ExcludeFolders
# give folders named "img" the "image" tag, including all subfolders of "img"
# give folders named "model*" the "image" tag; this does not apply to subfolders
[SourceFolder:folder_a]
Path=D:\Games\Data
ExcludeFolders=binary, venv
FolderTags=img|TAG=image,model*|TAG=image|NORECURSE

# because folder_b is within folder_a, folder_a rules do not apply under this path
# exclude folders that match rules from: [FileSyncCommand].ExcludeFolders and [SourceFolder:folder_b].ExcludeFolders,
# which includes [[FolderSet:skip_folders]]
[SourceFolder:folder_b]
Path=D:\Games\Data\Aventure\Quest
ExcludeFolders=skip_folders,docs

# this list of folder rules are used for exclusion in folder_b
# note that the TAG modifier will be ignored in this context (doesn't apply to rules used for exclusion)
[[FolderSet:skip_folders]]
t*
~*|TAG=bad
venv\Scripts|NORECURSE
```
