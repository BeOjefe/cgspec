# Repair guide: code size and line-ending check

- **CRLF line endings:** normalize the file to Unix LF (`\n`) before staging or writing.
- **File exceeds 400 lines:** extract cohesive helpers, types, or sub-commands into a focused sibling module rather than compressing lines or removing docstrings.
- **Function exceeds 60 lines:** split validation, parsing, or formatting steps into small single-purpose helper functions with clear inputs and outputs.
