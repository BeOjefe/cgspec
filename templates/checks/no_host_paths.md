# Repair guide: no hardcoded host paths

- Replace workstation-specific absolute paths (`/home/<user>/...`, `/Users/<user>/...`, `C:\Users\<user>\...`) with repository-relative paths resolved from the project root or runtime configuration passed via environment variables.
- In unit tests that need disposable directories, use `tempfile.TemporaryDirectory()` or a fixture helper rather than literal user paths.
