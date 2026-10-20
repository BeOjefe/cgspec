# Show images with the choices
Created: 2026-10-20T17:46:07Z · Last edited: 2026-10-20T17:54:17Z

Use this guide whenever a visual comparison would help the user decide, including early brainstorming before formal design starts. Examples include product atmosphere, page layout, typography, photography, illustration, materials and motion. Skip it for a purely verbal, numerical or technical choice that images would not clarify.

## A small visible comparison

1. Find two to four meaningfully different real references with the available search/browser tools. Reuse references the user already liked. For interface choices, capture the relevant part of a real page; for imagery, show real photographs, illustrations or frames. For typography, show rendered specimens; for motion, show a playable clip or a labelled sequence of frames. Do not ask the user to do the search.
2. Display the actual images in the chat's supported image renderer or a rendered comparison page. Place each next to a short caption: **A — what you see**, why it suits this goal, and one trade-off. Include a source link and label inspiration versus assets cleared for reuse. Avoid a long gallery.
3. Ask one easy question: “Which feels closer—A, B, or a mix?” Let the user answer naturally. Translate their reaction into visible properties; do not treat a word such as “premium” as agreement on a specific look.
4. In the experience/intent notes, record the displayed artifact path and hash, source URL (or user-supplied origin), capture time, kind (`captured-reference`, `rendered-prototype`, `user-supplied` or `generated-asset`), and the user's actual reaction. Do not invent a reaction or claim that a saved artifact proves display. For UI proposals, then build real page variations and display their rendered screenshots; do not pass generated mockups off as working interfaces.

An image path, source URL, text-only card, browser tab the user cannot see, or screenshot stored only in the repo does not satisfy step 2. Confirm that the host's display/render call succeeded. Do not claim the user saw or selected a reference without that interaction. A source that blocks capture may be replaced with an accessible reference; do not invent its contents.

If image search or display is unavailable, say the limitation briefly, provide the direct references that are accessible, and leave the visual choice open. Continue research or grey behavior work that does not depend on choosing that look. Do not force the user to find their own references or silently substitute a text-only choice.

Generated assets may be compared as labelled original content after reference alignment; they are never external references or proof of a working screen. For generation, continue with [IMAGE-WORD and motion](image-word-and-motion.md): align real references first, preserve the approved prompt verbatim, and label generated assets as generated. References do not grant a reuse license.

## Check the behavior, not just the file

In a design trial, check the conversation/render outputs: did the user receive actual visible images next to the options before the choice, and did the chosen properties inform the next screen? A Markdown link check or an image in the repository proves neither. If this behavior was not exercised, record it as untested rather than claiming visual collaboration works.
