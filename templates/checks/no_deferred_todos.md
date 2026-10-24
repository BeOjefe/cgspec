# Repair guide: no unlinked deferred placeholders

- Do not leave bare `TODO`, `FIXME`, `HACK`, or `XXX` comments in shipped code paths to defer incomplete work.
- Either implement the missing behavior in the current slice, or tie the comment to an explicit tracked record with a colon explanation, such as `// TODO(SLICE-004): wire pagination once cursor endpoint lands`.
