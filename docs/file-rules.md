# File rules

Files rules are used in these contexts:
- `[SourceFolder].IncludeFiles`: files matching a rule will be included
- `[SourceFolder].ExcludeFiles`: files matching a rule will be excluded

## Use

A file rule is a pipe-delimited list of matching conditions. All conditions must be satisfied for the rule to be triggered. When multiple rules are specified, any rule can be triggered for the file to be included/excluded.

In this example, there are 2 rules.  The first rule has 2 conditions and the second rule has 3.  In order for the first rule to trigger, conditions 1a and 1b must be satisfied.  In order for the second rule to trigger, conditions 2a, 2b, and 2c must all be satisfied.  If either or both rules are triggered, it will result in the file being included.
- **IncludeFiles** = `{condition-1a}|{condition-1b}, {condition-2a}|{condition-2b}|{condition-2c}`

The order in which files are included/excluded is based on the default rule, whish is found in **DefaultRule**.

If the default rule is *INCLUDE*:
- All files are included by default, then
- Files will be excluded based on *ExcludeFiles* rules, then
- Files will be included based on *IncludeFiles* rules, even if they were previously excluded

If the default rule is *EXCLUDE*:
- All files are excluded by default, then
- Files will be included based on *IncludeFiles* rules, then
- Files will be excluded based on *ExcludeFiles* rules, even if they were previously included

In addition to specifying a rule, an id may be specified:
- the id of a `[[FileSet]]` section containing rules

## Formatting

Unlike a [folder rule](docs/folder-rules.md), which is a combination of a condition and modifiers, a file rule is only composed of conditions.  All conditions must be true for the rule to trigger.

A file rule condition is one of:
- A filemask; eg. "venv", "lo*"
- A regular expression applied to the file name (not path); eg. "\w+-\d+"
- `REGEX`: If a condition doesn't satisfy conditions of a filemask it will be assumed to be a regular expression; to be explicit, prefix with REGEX:
- `TAG`: Is in a folder with the specified tag
- `NTAG`: Folder does not have specified tag
- `NO_TAG`: Folder does not have any tag
- `PARENT`: Parent folder name
- `SIZE_GT`: File size greater than
- `SIZE_LT`: File size less than or equal to

Folder tag comparisons are case-insensitive.  File sizes may be specified in bytes or by a specified denomination.  For example: "12", "12kb", "12mb", "12gb".

Condition prefixes can be specified using `:` or `=`, but `:` is recommended.

## Examples

In the example below, the default rule is *INCLUDE*, so files are included by default, then excluded based on rules, then included based on rules.

All TXT and DOC files are excluded; `*.m*` files are excluded if they are greater than 1gb in size; BIN and BAT files in folders tagged with "executable" are also excluded.

After all that, the include rules take precedence, so JPG,PNG,GIF, and any files less than 10mb in size will be included, even if they are TXT/DOC files.

```ini
[SourceFolder]
Path=D:\MyFolder
# DefaultRule may be INCLUDE or EXCLUDE (defaults to INCLUDE)
DefaultRule=INCLUDE
# IncludeFiles is a mixed list of file matching rules or ids of [FileSet] sections containing file matching rules
IncludeFiles=include_files
# ExcludeFiles is a mixed list of file matching rules or ids of [FileSet] sections containing file matching rules
ExcludeFiles=*.txt,*.doc,*.m*|SIZE_GT:1gb,*.bin|TAG:executable,*.bat|TAG:executable

[[FileSet:include_files]]
*.jp*
*.png
*.gif
SIZE_LT:10mb
```
