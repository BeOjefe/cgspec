# Repair guide: code size, atomicity, and line-ending check

- **CRLF line endings:** normalize the file to Unix LF (`\n`) before staging or writing.
- **File exceeds 400 lines or 350 non-comment code lines:** extract cohesive helpers, types, or sub-commands into a focused sibling module rather than compressing lines or removing docstrings.
- **Missing top-of-file header comment:** files with more than 15 code lines require a top-of-file docstring (Python) or leading comment (JS/TS) explaining their atomic responsibility.
- **Function exceeds 60 lines:** split validation, parsing, or formatting steps into small single-purpose helper functions with clear inputs and outputs.
- **Function lacks documentation:** functions longer than 20 lines require a docstring (Python) or leading comment / JSDoc (JS/TS).
- **Return statement exceeds 12 lines:** decompose complex multi-line return expressions into named intermediate variables, returning only the composed result.
- **Return statement contains nested inline logic or ternaries:** returns spanning more than 3 lines must not embed nested inline arrows, ternaries (`? :`), or `.map()` loops. Extract them into named variables before `return`.
- **Inline multi-statement JSX callback:** avoid multi-statement inline callbacks (`onClick={(e) => { stmt1; stmt2; }}`) in JSX. Extract named handler functions before the return statement.
