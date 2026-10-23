"""Pull request visual proof job appended to the consumer CI workflow for GUI profiles (spec 7).

It runs the trusted release's journeys and visual audit at the exact PR head, with Playwright installed at a
pinned version outside the checkout, and builds the summary from structured results (visual_summary.py).

All proof output (screenshots, video, logs, evidence.json) is written only under $RUNNER_TEMP, never inside
the checkout, and only the proof step itself writes there. The upload step is gated on that step's own
`outcome`, so a proof step skipped (not a pull_request event) or never reached (an earlier required step,
such as governance, failed) uploads nothing: a PR branch that commits a forged artifacts/cgspec-visual/
directory can never have it published under the CI artifact name.

The proof runs against a fresh `git worktree` checked out at the exact PR head and verified clean
(`git status --porcelain` empty, HEAD equal to that SHA) before testing anything: `git checkout --detach`
in the existing checkout can leave compatible uncommitted changes in place, which would test content that
was never committed while evidence.json still claimed that commit's SHA as `revision`. A checkout that is
not clean is BLOCKED, never PASS.
"""

from __future__ import annotations

# Exact Playwright release the CI visual proof installs outside the checkout (spec 7). The trusted engine
# loads it only from CGSPEC_PLAYWRIGHT_DIR, never from the pull request's node_modules.
PLAYWRIGHT_VERSION = "1.64.1"
# actions/upload-artifact v4.6.2: tag v4.6.2 resolves to this commit, whose package.json says 4.6.2.
UPLOAD_ARTIFACT_VERSION = "4.6.2"
UPLOAD_ARTIFACT_SHA = "ea165f8d65b6e75b540449e92b4886f43607fa02"
# The id of the proof step: the upload step is gated on this step's own outcome (spec 7).
PROOF_STEP_ID = "cgspec-visual-proof"
VISUAL_WORKFLOW = """      - name: Install pinned Playwright outside the checkout
        if: github.event_name == 'pull_request'
        run: |
          set +e
          D="$RUNNER_TEMP/cgspec-playwright"
          B="$RUNNER_TEMP/cgspec-playwright-browsers"
          # Point the engine at this directory first: if anything below fails, browser checks report BLOCKED
          # instead of falling back to modules from the pull request. PLAYWRIGHT_BROWSERS_PATH keeps Chromium
          # out of the runner's default user cache too (docs/STATUS.md).
          echo "CGSPEC_PLAYWRIGHT_DIR=$D" >> "$GITHUB_ENV"
          echo "PLAYWRIGHT_BROWSERS_PATH=$B" >> "$GITHUB_ENV"
          export PLAYWRIGHT_BROWSERS_PATH="$B"
          rm -rf "$D" && mkdir -p "$D" "$B" && cd "$D" || exit 0
          printf '{"private": true}\\n' > package.json
          npm install --ignore-scripts --no-audit --no-fund --save-exact "playwright@@PLAYWRIGHT_VERSION@" &&
            ./node_modules/.bin/playwright install --with-deps chromium ||
            echo "CGSpec: pinned Playwright could not be installed; browser checks will be BLOCKED"
          exit 0
      - name: CI visual proof (PR head)
        id: @PROOF_STEP_ID@
        if: github.event_name == 'pull_request'
        env:
          PR_HEAD: ${{ github.event.pull_request.head.sha }}
        run: |
          set +e
          export PLAYWRIGHT_BROWSERS_PATH="$RUNNER_TEMP/cgspec-playwright-browsers"
          OUT="$RUNNER_TEMP/cgspec-visual-proof-$PR_HEAD"
          TREE="$RUNNER_TEMP/cgspec-proof-tree-$PR_HEAD"
          rm -rf "$OUT" "$TREE" && mkdir -p "$OUT"
          # A fresh worktree at the exact PR head, never the existing checkout: `git checkout --detach`
          # there can leave compatible uncommitted changes in place, testing bytes nobody reviewed.
          CLEAN=0
          if git worktree add --detach -q "$TREE" "$PR_HEAD" > "$OUT/checkout.log" 2>&1 &&
             [ -z "$(git -C "$TREE" status --porcelain)" ] &&
             [ "$(git -C "$TREE" rev-parse HEAD)" = "$PR_HEAD" ]; then
            CLEAN=1
          else
            echo "CGSpec: $PR_HEAD did not check out clean; visual proof BLOCKED" >> "$OUT/checkout.log"
          fi
          J="$OUT/journeys.json"
          A="$OUT/visual-audit.json"
          # Exit 2 with no structured result is recorded as BLOCKED for each command that could not run.
          JOURNEY_CODE=2
          AUDIT_CODE=2
          if [ "$CLEAN" = 1 ]; then
            python3 "$CGSPEC_RELEASE/engine/journey.py" --root "$TREE" --video --json-out "$J" > "$OUT/journeys.log" 2>&1
            JOURNEY_CODE=$?
            python3 "$CGSPEC_RELEASE/engine/visual_audit.py" --root "$TREE" --video --json-out "$A" > "$OUT/visual.log" 2>&1
            AUDIT_CODE=$?
            cp -R "$TREE/.cgspec-scratch/journeys/." "$OUT/" 2>/dev/null || true
            cp -R "$TREE/.cgspec-scratch/visual/." "$OUT/" 2>/dev/null || true
          fi
          git worktree remove --force "$TREE" 2>/dev/null || true
          rm -rf "$TREE"
          # The summary reads only the structured results above; each command is judged on its own exit code.
          python3 "$CGSPEC_RELEASE/engine/visual_summary.py" --revision "$PR_HEAD" \\
            --artifact "cgspec-visual-$PR_HEAD" --evidence "$OUT/evidence.json" \\
            --summary "$GITHUB_STEP_SUMMARY" \\
            --result journeys "$JOURNEY_CODE" "$J" \\
            --result "visual audit" "$AUDIT_CODE" "$A" ||
            echo "CGSpec visual proof: BLOCKED, the summary could not be built" >> "$GITHUB_STEP_SUMMARY"
          exit 0
      - uses: actions/upload-artifact@@UPLOAD_ARTIFACT_SHA@  # v@UPLOAD_ARTIFACT_VERSION@
        # A skipped or never-reached proof step (an earlier required step such as governance failed, or
        # this is not a pull_request event) must publish nothing: never upload whatever happens to sit in
        # the checkout, such as a PR-committed artifacts/cgspec-visual/ (spec 7).
        if: always() && github.event_name == 'pull_request' && steps.@PROOF_STEP_ID@.outcome == 'success'
        with:
          name: cgspec-visual-${{ github.event.pull_request.head.sha }}
          path: ${{ runner.temp }}/cgspec-visual-proof-${{ github.event.pull_request.head.sha }}
          retention-days: 14
          if-no-files-found: warn
""".replace("@PLAYWRIGHT_VERSION@", PLAYWRIGHT_VERSION).replace(
    "@UPLOAD_ARTIFACT_SHA@", UPLOAD_ARTIFACT_SHA).replace("@UPLOAD_ARTIFACT_VERSION@", UPLOAD_ARTIFACT_VERSION).replace(
    "@PROOF_STEP_ID@", PROOF_STEP_ID)
