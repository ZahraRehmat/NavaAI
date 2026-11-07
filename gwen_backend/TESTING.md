# Delivery checks

## Version 2.0 voice and resident command loop

- Added offline faster-whisper tiny.en recognition, sounddevice microphone capture, and Windows SAPI spoken replies. The 75 MB speech weights live in this project's models folder. An incompatible automatic PyAV 19 dependency was detected during real decoding and replaced with pinned PyAV 15.1.0.
- `verify_voice.py` uses real local inference on synthesized WAVs for wake, scroll down/up, click here, a conversational question, and sleep. Session activation, unprefixed commands, question admission, and sleep are checked from recognized text. The default Microphone Array opened and provided 4,800 real audio samples. These checks do not establish recognition of the user's own voice or accent.
- Resident window state was inspected after hiding chat: the main window was hidden, the dock remained visible, and relaunch restored the same main-window handle (3934458), confirming the session was reused rather than a second model process being launched.
- `verify_live_input.py` passed against an actual test window: scroll position moved from 0 to 0.060606 and back to 0; click-at-pointer activated exactly one test button; typing produced `Gwen typed this.`. Qwen was never loaded. The first fixture attempt exposed wheel input going to the focused button instead of the pane under the pointer; pane-directed native wheel delivery corrected it and the rerun passed.
- Twelve new unit tests pass for typo-tolerant direct input, saved pointer coordinates, moved-window refusal, wake/session controls, global stop, speech segmentation, single-instance signaling, and ambient-fragment rejection. Including the background-browser typing test and previous regression checks, 49 tests pass.
- Live listening during development exposed background fragments (`And`, `Amen`, `reset`) being forwarded to the planner. The app was stopped, speech hints were reduced to names, confidence filtering was tightened, and both voice admission and the action executor now reject incomplete fragments before model inference. Plain `reset` is handled as conversation reset. Recording starts off until Hands-free or F9 is enabled, rather than recording while the user is setting up the app.
- Resident UI smoke test passes. Closing the main window now hides it; the dock provides Speak, Chat, Stop, microphone control and Quit. F9 arms one voice command, F10 toggles the chat, and F8 cancels both task and speech queues. The dock hides during input and does not activate the foreground app.
- Live microphone audio is not written to disk. `voice_test_audio` contains only synthesized test utterances. Transcript/action logs remain local. English is the initial voice language. No Windows startup entry or scheduled task was installed.

## Version 1.6 browser layer and integrity checks

- The user log proved that Dailymotion's `popin-overlay` intercepted clicks on the underlying `Log in` button, including after an `I understand` request. Browser observations now omit occluded controls, enumerate visible frames, clear old element markers, and bind locators to one observation token. Explicit named clicks require a matching reachable label.
- Seven added tests pass: a modal's `I understand` is exposed while the background button is excluded; dismissing it leaves the background button untouched; framed controls are reachable; unrelated labels are refused; old markers do not create duplicate IDs; stale observations cannot click replacement buttons; Task Manager search uses a field or stops on denied access.
- The actual Task Manager process was confirmed at higher Windows integrity than Gwen using Windows token information. No process was ended or changed. Input is blocked before inference, with a permission-specific message. No automatic elevation was added.
- Browser navigation and background DOM controller integration checks still pass. Authentication was not tested or completed.

## Version 1.5 model-path diagnosis

- The user's Word and missing-space chat requests failed at window-bound capture before inference, despite the old message blaming Qwen. This was confirmed from the session log. Window focus and geometry now use explicit Win32 argument and return types independently of COM/UIA; transient null foreground windows are retried briefly.
- Accessibility observation exceptions now permit OCR fallback. Missing spaces such as `opengull chat` are recognized. Twenty-nine regression tests pass, including the COM exception and capture-stage message cases.
- A live unconstrained Qwen run on Word returned malformed coordinate arrays (`x` and `y` were both `[270,140]`), demonstrating a real model-format failure separately from the earlier capture failures.
- The runtime supports JSON-schema-constrained VLM generation. `verify_constrained.py --device GPU` passed with a real model-generated click at `(208,336)` in normalized coordinates, inside the first synthetic recent-file label. A separate CPU run produced `(219,322)`, also inside that label. No desktop input is executed by this diagnostic. This tests format and a small grounding task; it does not establish general task reliability.
- **Actual Qwen-controlled Word test passed:** entered `open first file on word` through Gwen's GUI with a one-action bound. The model received the Word window screenshot and chose `{"action":"click","x":270,"y":482}`. That action executed, and independent window inspection showed `Proposal Plan - FYP ( Nava AI ).docx - Word`, matching the first recent file. No deterministic first-file routine was used. This was a real model inference/action test; no text was entered into the document and no edits were saved.

## Version 1.4 visual target checks

- The user-reported WhatsApp action was rejected because screenshot clicks were required to match an incomplete accessibility-control list. That restriction was removed. Click coordinates now map to the target-window crop, while scalar/range and foreground/position checks remain.
- Twenty-seven unit/regression checks pass, including crop-coordinate mapping, the chat-opening intent, OCR fallback when UIA is incomplete, and rejection of ambiguous/low-confidence OCR names.
- Real local CPU OCR recognized the synthetic text `Kashaf Uni` with confidence 0.999.
- **Live GUI check passed:** entered `open kashaf uni chat` into Gwen 1.4 and ran it. WhatsApp subsequently displayed `Kashaf Uni` in the conversation header. The before/after window screenshots were independently inspected through Computer Use. No message was typed into WhatsApp or sent. This check demonstrates that specific visible-chat workflow, not arbitrary chat search or message sending.
- `rapidocr-onnxruntime==1.4.4` and its CPU dependencies were added only to this assistant's virtual environment. OCR runs locally; screenshots are not uploaded to an OCR service.

## Version 1.3 native routing checks

- The reported session log confirmed the model was observing **Gwen's own window**, explaining the invalid desktop click proposals. Desktop model tasks now focus the selected app first and reject Gwen as a target.
- Real `gwen.py --task "oepn store"` normalized the launch verb and launched Microsoft Store without loading the model.
- Twenty-three unit/regression tests pass. New tests cover launch typos, named native control selection, duplicate/missing labels, target-app focus routing, and avoiding model/coordinate fallback for named native clicks.
- Native app-card matching now includes named groups, text, and images at a deeper UIA tree depth. Selection of an actual Netflix card is not guaranteed: the app must expose a matching visible control. A missing target is reported honestly instead of guessed.
- Rejected desktop proposals terminate the task without a traceback in chat. Unexpected exceptions are recorded to the session log and summarized in the UI.

## Version 1.2 reliability checks

- Sixteen unit/regression tests pass, covering site-specific YouTube routing, typo-tolerant first-result commands, CAPTCHA follow-up blocking, bounded large-page prompts, text preservation, and GPU-session disposal with a single CPU retry.
- Live isolated Chrome sequence: `search mr beast on youtube`, then `open first video` reached a YouTube watch URL without loading Qwen or using Google. No result was clicked through a CAPTCHA.
- Recovery unit tests inject allocation failures to verify GPU is discarded and CPU is tried once; these are not evidence that every hardware/driver failure can be recovered.
- `verify_runtime.py` also passed with real local inference: a large-page input was reduced to 1,369 text tokens and ran on GPU; an injected GPU allocation exception then caused a new CPU pipeline to load and generate the exact quoted test text. The original hardware allocation fault was simulated for the recovery check. This verifies the recovery path, not universal model accuracy. An initial unquoted multiword test phrase was shortened by the model, which remains a documented accuracy limitation.
- `verify.py --model` includes a real large-page model-inference check with the model tokenizer enforcing at most 1,600 text tokens. Screenshots are reduced to at most 640 by 400 for inference; visual tokens are additional to the measured text limit. Output generation is capped at 128 tokens.
- No software was installed from the Store during these fixes. Arbitrary Store installation and desktop workflows are still model-dependent and must not be treated as proven by the browser tests.

## Version 1.1 regression checks

- Nine automated regressions cover the user's exact search commands, app context changes, Store query encoding, typo correction, invalid coordinates, and repeated-action fingerprints. Invalid coordinate arrays were verified to never reach mouse input.
- Real `search youtube.com on chrome` navigated to `https://www.youtube.com/` using an isolated test browser, without loading the VLM or issuing desktop clicks.
- Real `search youtube on chrome` selected browser search correctly. Google presented a CAPTCHA on this network; Gwen reported the block and did not switch to desktop clicking. Search results were not verified through that CAPTCHA.
- Real `search instgarm on store` opened the Store's Instagram results. The Store window screenshot showed the Instagram product card and search term, independently inspected through the Computer Use skill.
- Background browser DOM controller checks still pass. Original model checks below describe the earlier delivery; arbitrary native-app grounding remains unproven. Windows accessibility controls supplement screenshot input but do not make this 2B model universally reliable.

Run `python -m unittest test_regressions -v` and `python verify_searches.py` using this folder's virtual environment to repeat the regression checks. Test browsers use separate profiles from the user's running Gwen browser.

Checked on this Windows computer on 27 October 2026.

- Copied model: 51 files, 1,787,546,217 bytes; SHA-256 comparison found zero mismatches against the original model directory.
- Separate Python environment: dependency check passed; source compilation passed.
- App directory: 580 launch entries including duplicates. Store, Chrome, VS Code, and Visual Studio Insiders alias resolution checked. Unrecognized names are rejected.
- Native launch: `gwen.py --task "open store"` launched Microsoft Store; `WinStore.App` was running afterward.
- GUI: startup and shutdown smoke test passed.
- Real background Chrome: navigation to a local fixture, page text/control observation, fill, click, tab creation and tab selection passed.
- Local Qwen inference on GPU: browser field selection and text entry passed. Vision encoder located a blue button away from the center of a synthetic screenshot using normalized coordinates.
- Sequential user turns: fill a field, then request a button click; checked the resulting page contents and retained task memory.

The model occasionally repeated actions and prematurely reported completion during combined-task trials. The controller now stops repeated loops and validates the target label for simple explicit browser button/link clicks, finishing these requests after the successful click. This does not eliminate model errors on arbitrary tasks. The latest reproducible suite result is in `verification.txt`.

Physical desktop click/type/drag behavior was implemented with PyAutoGUI but was not exercised against arbitrary installed apps during delivery. Screenshot grounding was tested with the real VLM; Store launch was tested separately. No claim is made that every desktop application or website is supported.
