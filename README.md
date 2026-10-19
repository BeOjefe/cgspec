# CGSpec

CGSpec is a project method carried by the agent. You describe the goal, constraints and taste in ordinary language. The agent maps what exists, brings evidence and design references, implements bounded changes, runs checks, and records decisions and gaps. Machine checks enforce what they can; human judgment remains with you.

The canonical [method specification](docs/METHOD-v0.2.md) defines the contract, layout, design path, review rules, adoption flow and limits. The [short agent contract](engine/CONTRACT.md) is installed into each project. Skills under `skills/` load only for the work at hand. The engine under `engine/` is copied once into each project under `docs/_cgspec/01-engine/`.

## Development status

This `claude/design-craft` branch is a CGSpec v0.2 candidate, not a published release. The version marker is `0.2.0` for compatibility testing; the plugin release tag and its CI trust bootstrap are pending. The installer, doctor, ledger, hooks, source ingestion and v0.1 adoption path are under test. Browser journeys, visual audit, prototype bundling and change impact checks are implemented but still need browser-backed and agent-driven review. A passing source check does not establish runtime behavior, design quality, or deployment readiness.

The current package has nine workflows: init, adopt, forge, ui-ux, council, slice, migrate, operate and team-review. `cgspec-pivot` is a compatibility alias. The eight role definitions support bounded team work; routine changes use only the workers that add value.

## Try it in a disposable project

```bash
mkdir -p /tmp/cgspec-example
python3 engine/install.py install --root /tmp/cgspec-example --profile web-workspace --topology single --tools git
python3 engine/doctor.py --root /tmp/cgspec-example
python3 engine/install.py verify --root /tmp/cgspec-example
```

`install.py upgrade --from-v1 --root <project>` produces a staged report for earlier v0.1 layouts before publication. The `--from-v1` flag retains its spelling for compatibility. It stops with a partial result where legacy material, links or decisions need review. Do not use `--apply` on a live project until the report, rollback and project ownership are settled.

For this plugin repository:

```bash
python3 -m unittest discover -s tests -t .
claude plugin validate . --strict
```

First installation of governance on a GitHub repository needs an owner-reviewed baseline before the CGSpec check can be required. The exact trust sequence and the limits of local hooks are in [section 8](docs/METHOD-v0.2.md#8-enforcement-engine). No local script proves a message came from the user when the agent controls the same shell.

CortexGate is optional and independent of CGSpec; using this method does not require that service.
