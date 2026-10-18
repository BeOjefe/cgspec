# Behavior coverage for a designed screen

Use this only when defining layer 4 journeys or verifying a layer 6–7 implementation. Choose states from the actual task and profile; a static page does not need an invented offline or permission state.

For every action in the approved task map, record the starting state, input, expected visible state, persistence or navigation effect, and a stable test ID. Include meaningful empty, loading, error, denied and success states when the product can reach them. Test the critical journey in a real browser or supported simulator with user-like interaction and assertions on results. A synthetic event dispatched to a handler, a static screenshot, and a console-free load do not establish that the control works.

Check focus order, keyboard activation, visible focus, Escape and focus return where dialogs exist, screen-reader names, color-independent status, and touch targets appropriate to the platform. Verify responsive layout at the viewports actually supported. For native mobile, label web preview, simulator and physical-device evidence separately.

Store each result with the revision, environment, exact journey and outcome. A missing browser, simulator or device is untested coverage, not a passing result. If a locked baseline changes, show the difference and obtain approval for the new baseline through the project path.
