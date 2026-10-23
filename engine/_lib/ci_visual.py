"""Pull request visual proof job appended to the consumer CI workflow for GUI profiles (spec 7).

It runs the trusted release's journeys and visual audit at the exact PR head, with Playwright installed at a
pinned version outside the checkout, and builds the summary from structured results (visual_summary.py).
"""

from __future__ import annotations

# Exact Playwright release the CI visual proof installs outside the checkout (spec 7). The trusted engine
# loads it only from CGSPEC_PLAYWRIGHT_DIR, never from the pull request's node_modules.
PLAYWRIGHT_VERSION = "1.64.1"
# actions/upload-artifact v4.6.2: tag v4.6.2 resolves to this commit, whose package.json says 4.6.2.
UPLOAD_ARTIFACT_VERSION = "4.6.2"
UPLOAD_ARTIFACT_SHA = "ea165f8d65b6e75b540449e92b4886f43607fa02"
VISUAL_WORKFLOW = """      - name: Install pinned Playwright outside the checkout
        if: github.event_name == 'pull_request'
        run: |
          set +e
          D="$RUNNER_TEMP/cgspec-playwright"
          # Point the engine at this directory first: if anything below fails, browser checks report BLOCKED
          # instead of falling back to modules from the pull request.
          echo "CGSPEC_PLAYWRIGHT_DIR=$D" >> "$GITHUB_ENV"
          rm -rf "$D" && mkdir -p "$D" && cd "$D" || exit 0
          printf '{"private": true}\\n' > package.json
          npm install --ignore-scripts --no-audit --no-fund --save-exact "playwright@@PLAYWRIGHT_VERSION@" &&
            ./node_modules/.bin/playwright install --with-deps chromium ||
            echo "CGSpec: pinned Playwright could not be installed; browser checks will be BLOCKED"
          exit 0
      - name: CI visual proof (PR head)
        if: github.event_name == 'pull_request'
        env:
          PR_HEAD: ${{ github.event.pull_request.head.sha }}
        run: |
          set +e
          CHECKED_OUT=0
          git checkout --detach "$PR_HEAD" && CHECKED_OUT=1
          # Only files the trusted engine writes in this step may be published, never committed ones.
          rm -rf artifacts/cgspec-visual .cgspec-scratch/journeys .cgspec-scratch/visual
          mkdir -p artifacts/cgspec-visual
          J="$RUNNER_TEMP/cgspec-journeys.json"
          A="$RUNNER_TEMP/cgspec-visual-audit.json"
          rm -f "$J" "$A"
          # Exit 2 with no structured result is recorded as BLOCKED for each command that could not run.
          JOURNEY_CODE=2
          AUDIT_CODE=2
          if [ "$CHECKED_OUT" = 1 ]; then
            python3 "$CGSPEC_RELEASE/engine/journey.py" --root "$GITHUB_WORKSPACE" --video --json-out "$J" > "$RUNNER_TEMP/journeys.log" 2>&1
            JOURNEY_CODE=$?
            python3 "$CGSPEC_RELEASE/engine/visual_audit.py" --root "$GITHUB_WORKSPACE" --video --json-out "$A" > "$RUNNER_TEMP/visual.log" 2>&1
            AUDIT_CODE=$?
          fi
          cp -R .cgspec-scratch/journeys/. artifacts/cgspec-visual/ 2>/dev/null || true
          cp -R .cgspec-scratch/visual/. artifacts/cgspec-visual/ 2>/dev/null || true
          cp "$RUNNER_TEMP/journeys.log" "$RUNNER_TEMP/visual.log" artifacts/cgspec-visual/ 2>/dev/null || true
          # The summary reads only the structured results above; each command is judged on its own exit code.
          python3 "$CGSPEC_RELEASE/engine/visual_summary.py" --revision "$PR_HEAD" \\
            --artifact "cgspec-visual-$PR_HEAD" --evidence artifacts/cgspec-visual/evidence.json \\
            --summary "$GITHUB_STEP_SUMMARY" \\
            --result journeys "$JOURNEY_CODE" "$J" \\
            --result "visual audit" "$AUDIT_CODE" "$A" ||
            echo "CGSpec visual proof: BLOCKED, the summary could not be built" >> "$GITHUB_STEP_SUMMARY"
          exit 0
      - uses: actions/upload-artifact@@UPLOAD_ARTIFACT_SHA@  # v@UPLOAD_ARTIFACT_VERSION@
        if: always() && github.event_name == 'pull_request'
        with:
          name: cgspec-visual-${{ github.event.pull_request.head.sha }}
          path: artifacts/cgspec-visual/
          retention-days: 14
          if-no-files-found: warn
""".replace("@PLAYWRIGHT_VERSION@", PLAYWRIGHT_VERSION).replace(
    "@UPLOAD_ARTIFACT_SHA@", UPLOAD_ARTIFACT_SHA).replace("@UPLOAD_ARTIFACT_VERSION@", UPLOAD_ARTIFACT_VERSION)
