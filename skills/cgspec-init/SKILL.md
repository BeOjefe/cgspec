---
name: cgspec-init
description: Install, verify, update, or uninstall the CGSpec v2 package and tool adapters in a project. For an existing unadopted project, use cgspec-adopt first.
---

# Initialize CGSpec

Read the [agent contract](../../engine/CONTRACT.md) and the installed `docs/_cgspec/project.json` if present. This skill manages the package; project discovery and content migration belong to `cgspec-adopt`.

For a new project, identify its profile (`website`, `web-workspace`, `mobile`, `cli`, `headless`, `small`), topology (`single`, `monorepo`, `large-monorepo`, `polyrepo-governance`, `polyrepo-member`), and tools actually present. Use the plugin copy of `engine/install.py` and its `--help` to confirm syntax. The current install command is `python3 engine/install.py install --root <path> --profile <profile> --topology <topology> [--tools <comma-separated-tools>]`. Install only into the authorized repository. The installer owns generated files and has an uninstall manifest; inspect conflicts before acting on a nonempty tree.

For an installed v2 project, run `python3 engine/install.py verify --root <path>` before `upgrade` or `uninstall`. `upgrade` refreshes the vendored engine; `uninstall` removes only unchanged owned files. Check `docs/_cgspec/01-engine/` and adapter wiring after the action, then run `python3 docs/_cgspec/01-engine/doctor.py --root <path>`. Record any adapter or CI capability that could not be verified. GitHub branch protection and remote approval settings require their own evidence; file creation alone does not activate them.

A v1 layout is an adoption upgrade: route to `cgspec-adopt` for a path map, rollback and content checks before updating the version marker.
