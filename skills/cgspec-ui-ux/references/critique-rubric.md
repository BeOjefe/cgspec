# Critique rubric

A fixed rubric for judging screenshots, used before locking layer 6 and at every design review. The reviewer is a different agent from the author (a different model when available) and must be able to see images. It gets:

- the desktop and phone screenshots (from `visual_audit.py`, `.cgspec-scratch/visual/`),
- the locked register (`docs/spines/03-EXPERIENCE.md` `## Register`),
- the screenshot of the reference the register names first,

and **never** the author's explanation of the design. Explanations make reviewers grade the intent instead of the pixels.

## Score each criterion 1–5

| # | Criterion | 1 | 3 | 5 |
| --- | --- | --- | --- | --- |
| 1 | One clear focal point | Nothing stands out, or several things compete | A focal point exists but something else competes | The main need is the first thing seen, nothing competes |
| 2 | Hierarchy, readable in greyscale | One or two flat levels | Three levels, but some blur together | Three or more levels, distinct in greyscale |
| 3 | Alignment to one grid | Edges everywhere | Mostly aligned, a few strays | Everything sits on a few clear lines |
| 4 | Density fits the content | Far too sparse or cramped for the task | Acceptable, some wasted or crowded areas | Exactly as dense as the task needs, with realistic data |
| 5 | Surfaces and colour roles | Levels indistinguishable or accent everywhere | Levels visible, accent mostly disciplined | Levels clear and quiet, accent only for its job, status colours only for status |
| 6 | Signature element present | Absent | Present on some screens or weak | Present, consistent, serves the main task |
| 7 | Likeness to the references | Unrelated, or a near copy | Some resemblance | Clearly in the spirit of the references, clearly its own |

## Output

```markdown
Screen: <name> · revision <short sha> · reviewer <model>
Scores: 1=_ 2=_ 3=_ 4=_ 5=_ 6=_ 7=_  (mean _._)
Verdict: PASS (no score below 3 and mean at least 3.5) | FAIL
Fix first: <the single change that would raise the lowest score>
Notes: <one line per score below 4, pointing at a visible element>
```

Record the result as evidence in `docs/_cgspec/06-evidence/design-review/<screen>.json` with `covers` set to the screen's source files, so a later change marks it stale. A FAIL blocks locking layer 6 for that screen. Fix the "fix first" item and re-review; do not argue with the score.
