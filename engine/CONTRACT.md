# CGSpec contract (draft, completed in build step 3)

You carry the method; the user sets goals and judges results. Full spec: METHOD-v2.

1. Before editing, declare the change tier with `cgspec_hook.py tier set` (spec 3).
2. Write to the ledger only with `memlog.py`.
3. Never edit files listed in `07-state/frozen.json`; never create scripts outside `src/`,
   tests, `04-checks/` (after approval) or `.cgspec-scratch/`.
4. Tests first for T1+; record the failing test in `06-evidence/tests/`.
5. You never write approvals; only the user's own message or commit trailer counts.
6. End every report with "Decisions I made for you".
7. Run `doctor.py` before ending a turn.
