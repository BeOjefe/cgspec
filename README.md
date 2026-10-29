# CGSpec
Created: unknown · Last edited: 2026-10-29T13:37:17Z

CGSpec is a project method carried by the agent. You describe the goal, constraints and taste in ordinary language. The agent maps what exists, brings evidence and design references, implements bounded changes, runs checks, and records decisions and gaps. Machine checks enforce what they can; human judgment remains with you.

The canonical [method specification](docs/METHOD.md) defines the contract, layout, design path, review rules, adoption flow and limits. The [short agent contract](engine/CONTRACT.md) is installed into each project. Skills under `skills/` load only for the work at hand. The engine under `engine/` is copied once into each project under `docs/_cgspec/01-engine/`.

## Start here

CGSpec v0.3.0 is the current package release. [Current implementation status](docs/STATUS.md) separates implemented checks from outcomes that still need live proof. A passing source check does not establish runtime behavior, design quality or deployment readiness.

| If you want to... | Read |
| --- | --- |
| Understand the method | [Current method specification](docs/METHOD.md) |
| See what is implemented or still limited | [Implementation status](docs/STATUS.md) |
| Install, upgrade or validate a project | [Engine formats and commands](engine/FORMATS.md) |
| Contribute to this repository | [Contributor entry](AGENTS.md) |
| Find historical decisions and research | [Documentation map](docs/00-INDEX.md) |

The package has nine workflows: init, adopt, forge, ui-ux, council, slice, migrate, operate and team-review. `cgspec-pivot` is a compatibility alias. The eight role definitions support bounded team work; routine changes use only the workers that add value.

## Try it in a disposable project

```bash
mkdir -p /tmp/cgspec-example
python3 engine/install.py install --root /tmp/cgspec-example --profile web-workspace --topology single --tools git
python3 engine/doctor.py --root /tmp/cgspec-example
python3 engine/install.py verify --root /tmp/cgspec-example
```

`install.py upgrade --from-v1 --root <project>` produces a staged report for earlier v0.1 layouts before publication. The `--from-v1` flag retains its spelling for compatibility. It stops with a partial result where legacy material, links or decisions need review. Do not use `--apply` on a live project until the report, rollback and project ownership are settled.

For an installed v0.2 project, run `python3 <current-plugin>/engine/install.py upgrade --root <project>` after obtaining the newer plugin copy. This refreshes the vendored engine, Claude and Antigravity hooks, and Antigravity's workspace skills. Replaced skill copies are archived under `docs/_cgspec/_archive/agent-skills/`. Run `verify` and `doctor.py` afterward. Changes to protected GitHub CI wiring still need owner review before the new release can judge protected branches.

Keep the host plugin and the project copy in step: update or replace this plugin directory first, then run the project `upgrade` command above. Claude Code marketplace installs use `claude plugin update cgspec@<marketplace>`; Antigravity can install the directory with `agy plugin install <plugin-directory>` (its CLI currently has no `update` command, so re-import/reinstall must be checked on the installed host). Codex can register this repository with `codex plugin marketplace add <plugin-directory>` and install `cgspec@cgspec-local`; for this local source, update the directory and restart the host. For a Git marketplace, `codex plugin marketplace upgrade <marketplace>` refreshes its snapshot. The root `plugin.json` and `.agents/plugins/marketplace.json` package the same ten skills for Codex and Antigravity. A host plugin update alone does not refresh a project's vendored engine or workspace hooks.

For this plugin repository:

```bash
python3 -m unittest discover -s tests -t .
claude plugin validate . --strict
```

First installation of governance on a GitHub repository needs an owner-reviewed baseline before the CGSpec check can be required. The exact trust sequence and the limits of local hooks are in [section 8](docs/METHOD.md#8-enforcement-engine). No local script proves a message came from the user when the agent controls the same shell.

CortexGate is optional and independent of CGSpec; using this method does not require that service.
