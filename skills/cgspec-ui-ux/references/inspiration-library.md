# Personal inspiration library

A folder of references the user has liked, kept outside any one project so every new project starts from the user's own taste instead of a blank search. It is a plain folder; no service, no cost.

## Location

`$CGSPEC_INSPIRATION` if set, otherwise `~/.cgspec/inspiration/`. One sub-folder per reference:

```text
~/.cgspec/inspiration/
  2026-10-19-linear-issue-list/
    screenshot.png          (or several: desktop.png, phone.png, detail.png)
    ref.md
```

`ref.md`:

```markdown
# <Name>
Source: <URL or "user's own image">, captured <date>
Liked for: "<the user's words>"
Pattern: <one line: what to take, not the paint>
Tags: <density>, <mood>, <product type>, <element> (for example: dense, calm, dashboard, table)
License note: <reference only | free asset under ... | user-owned>
```

## How the agent uses it

1. At layer 0, before searching the web, list the library (`ls` the folder and read the `ref.md` files) and pick up to three entries whose tags fit the brief. Show them next to the new references and say which came from the library.
2. When the user reacts well to a new reference ("this one", "I like the table here"), ask once whether to save it to the library. Save only with a yes, including the user's own words.
3. Never copy a library reference's paint into a project; it informs the register and the measured values (see `reference-extraction.md`), like any reference.
4. The library belongs to the user. Do not delete or rewrite entries; add new ones.
5. If the folder does not exist, say so once and offer to create it when the first reference is liked.
