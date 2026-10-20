# Aligning image words, generated media and motion
Created: 2026-10-20T15:19:11Z · Last edited: 2026-10-20T17:48:52Z

For general brainstorming and visual comparisons, use [visual choices](visual-choices.md). Use this reference only when a product needs original imagery, video, or a coordinated media moment. For a text-only app or a screen where real product data is the visual focus, skip it.

## 1. Find the visual direction before generation

Before asking an image or video model to create an asset:

1. Browse and show the user a small set of real references: the actual sites, photographs, film frames, illustrations or motion examples that express different directions. Prefer two to four useful examples, reusing an already chosen direction rather than reopening it. Include source links and label whether an item is inspiration only or can be reused under its license.
2. Let the user react in their own words or point at a reference. Name the visual qualities they appear to mean, but do not assume a word such as “premium”, “calm” or “bold” has one fixed visual meaning.
3. Prepare an **IMAGE-WORD card** that pairs the user's words with the visible reference and a plain-language reading of both. Show the card. Resolve only a real mismatch; do not make the user fill out a technical brief.
4. Propose the asset and where it will appear in the real page. Generate after the direction is aligned. A generated picture is page content, never a substitute for a working screen or a reference.

An IMAGE-WORD card contains only fields relevant to the asset:

```text
What the user said: <their words>
Reference(s): <image or video, source URL, and the detail they reacted to>
What we understand: <the feeling and visible qualities in plain words>
Subject and moment: <what is happening>
Composition: <camera/viewpoint, framing, focal point, negative/text-safe space>
Light, colour and material: <only the qualities that matter>
Use in the page: <location, crop/aspect ratio, responsive treatment>
Avoid: <the things the user rejected or that would harm the product>
Motion, if any: <sequence, timing, camera move, cut points, text relationship>
Fallback: <still image, poster, or no-media behavior>
```

## 2. Preserve the approved prompt

The lead model writes a complete prompt packet using the card, then shows it to the user in readable form. Include subject, scene, composition, camera, light, palette, texture, aspect ratio, resolution, text-safe area, intended crop, motion or duration when relevant, exclusions, and reference provenance. Do not ask a user to translate the visual direction into prompt jargon.

After alignment, pass the prompt packet to the generator **verbatim**. Do not have another language model paraphrase, summarize, embellish, or “improve” it between approval and generation. If the selected tool adds a required wrapper, preserve the packet as a clearly delimited unchanged block and record the wrapper separately. Save the exact approved prompt, tool/provider, model and version, generation time, output path and known rights with the asset. If the generator or its version cannot be identified, record that limit.

Use the media generator that the current session can actually reach. If Antigravity's image or video generation is connected, the lead model may pass the approved packet through it even when a different model leads the conversation. Otherwise use a directly available generation tool (for example, Codex image generation) with the packet unchanged. If no generator is callable, offer the prompt for a supported tool and say generation has not happened. Never claim a remote provider is available based only on an installed skill or a remembered model list. Ask first before a paid service or a new service that sends project material to another provider.

For public stock or other existing assets, verify the reuse license, required attribution, commercial restrictions and provenance before including the asset in the product. A reference screenshot does not grant permission to reuse the image or code.

## 3. Make media work with the page

Treat a high-quality image as part of the page's composition, not a decorative background added after layout. Reserve the needed crop and text-safe area in the real screen, check mobile crops, loading behavior and contrast, and use responsive modern formats or an optimized poster where the stack supports them. Keep descriptive alt text for meaningful images; decorative images get empty alt text.

For a landing page or immersive space where video and text tell one story, propose a short storyboard before implementation. Give each shot a purpose and time range; mark cuts, camera movement, text entry/exit and UI transition timings against the clip's actual timeline. Align the text with the visual beat instead of overlaying unrelated animation. Preserve the source clip's native frame rate unless there is an evidenced reason to convert it. Keep interface motion smooth within the browser's measured frame budget, prefer transform/opacity animation, stop or simplify off-screen playback, honor reduced-motion preferences, and provide a still or lightweight fallback. Motion is purposeful only when it improves meaning or atmosphere.

The deliverable is still a working page. Integrate the asset in the actual frontend, then show the rendered page at desktop and phone widths. A generated image by itself does not count as a completed design, a screenshot does not prove video playback, and a browser preview does not prove performance on every device.
