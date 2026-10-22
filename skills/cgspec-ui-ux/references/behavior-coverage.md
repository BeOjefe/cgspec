# Behavior coverage for a designed screen

Use this only when defining layer 4 journeys or verifying a layer 6–7 implementation. Choose states from the actual task and profile; a static page does not need an invented offline or permission state.

For every action in the approved task map, record the starting state, input, expected visible state, persistence or navigation effect, and a stable test ID. Include meaningful empty, loading, error, denied and success states when the product can reach them. Test the critical journey in a real browser or supported simulator with user-like interaction and assertions on results. A synthetic event dispatched to a handler, a static screenshot, and a console-free load do not establish that the control works.

Give each reachable state a name and a direct address in the prototype, for example `?state=pending-as-manager`, so a reviewer can open it without clicking through the flow. This is a prototype convention; `journey.py` still reaches states by walking the journey. These named states are the test fixtures for journeys and screenshots; review non-default states too, because many defects only show there. Where several people act on the same record, also cover these cases:

- **A repeated action:** a double click or a retry must record one result.
- **A stale view:** someone else changed the record after it was opened. The view must say so, and the safe action becomes the main action.
- **A decision about an earlier version:** an approval or signature applies to the exact version it was given for. A later edit that matters cancels it, and the record shows which version was decided.

Check focus order, keyboard activation, visible focus, Escape and focus return where dialogs exist, screen-reader names, color-independent status, and touch targets appropriate to the platform. Verify responsive layout at the viewports actually supported. For native mobile, label web preview, simulator and physical-device evidence separately.

Store each result with the revision, environment, exact journey and outcome, labelled Executed (actually run here) or Specified (written down, not run). In an evidence file, Specified checks go in `not_run`. A check that someone else claims to have run is Specified until you run it. Logic that runs only in the browser (role switchers, permission checks) does not establish server enforcement. A missing browser, simulator or device is untested coverage, not a passing result. If a locked baseline changes, show the difference and obtain approval for the new baseline through the project path.
