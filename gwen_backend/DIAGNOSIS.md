# Qwen desktop control diagnosis — 28 October 2026

## Save-dialog foreground and text-mention errors

The repeated foreground messages came from Gwen's input guard. A disabled Excel owner and its active owned save popup have different HWNDs. Focusing/comparing only the owner fails even when its dialog is the correct target. The old OCR fallback also selected whichever window was foreground after an accessibility failure, allowing it to scan the chat instead of the intended dialog. Its partial-label score could accept prose mentioning the requested words. Exact Save was also treated as ambiguous with near labels Don't Save and AutoSave.

The controller now resolves the visible enabled popup of a disabled owner and pins observations/actions to that target. Native actions refocus and validate the observed window/control, and a changed dialog gets one fresh observation. OCR never switches to a different foreground app mid-lookup. Save/Don't Save/Cancel/Yes/No/OK queries require actual native buttons with an exact canonical alias match and never use arbitrary OCR screen text. A unique blocking dialog may supply that button when the selected window only contains a textual mention; multiple actual matching windows require clarification. Exact matches take precedence over partial labels, Save negation is preserved, and long prose cannot stand in for a short label. Diagnostics record bound/foreground handles on failures.

The isolated native fixture invoked Don't Save and Save correctly while its owner was disabled, and verified both real dialog responses and successful action results. Its action guard prohibited invoking a control outside its own scratch dialog. No user workbook was saved or discarded. Results are in `diagnostics/dialog-native-verification.json`. Regression tests cover owned-popup routing, strict button roles, opposite Save labels, chat mentions, bound-window reacquisition and stale dialog observations. Font-size changes and table removal are separate command-coverage gaps; this patch does not implement them.

## Follow-up: video requests changing behavior

Analysis of `session-20261028-214759-125488.jsonl` used JSON traces and filesystem/window metadata only; no media was viewed or played.

- Successful blue/red/green image requests used filesystem routing. Video formats were absent from the resolver's extension set, so video requests took the less reliable visual route. Video/audio extensions are now included in exact-name/stem lookup.
- Both process-inspection errors occurred while focusing remembered Media Player handles, before Qwen was called. Those handles no longer exist now; their current PID/thread IDs are zero. Stale handles after closing the player are the likely explanation, although the old log omitted Windows error codes and cannot prove the state at the exact failure time. Snapshots now include PID, remembered targets are validated, closed/reused handles are skipped, and live-process permission errors include the Windows error code. Genuine higher-integrity restrictions still stop; no elevation or permission bypass was added.
- The timestamped recording exists in the active Bandicam directory. Suggestions matched unrelated numeric date fragments while MP4 files were excluded. Dates alone no longer generate suggestions, and the real recording now resolves by name without playback.
- A later explicit open request generated the preceding recording's target. The prompt included recent filenames. Explicit single-item open targets are now bound to the user's current label in the schema and grounding query, and unrelated previous-task context is excluded for those requests. Requested extensions cannot be silently changed; a matching stem with another extension is suggested for clarification.

75 regression tests passed, including fake media files, numeric suggestion rejection, extension mismatch, previous-target contamination, closed-window fallback and PID/handle reuse. No claim is made here about playback or the contents of any recording.

## Current capture and visible-open behavior

Computer-control Qwen calls now receive the whole current primary screen, not a foreground-window crop. Desktop planning and grounding use the same full-frame image; visible/background browser planning also receives that screen image while retaining DOM IDs for browser actions. Images preserve aspect ratio and retain up to 1920×1200 pixels (the current screen's native size). Foreground metadata helps identify the app but does not crop the image.

Desktop VLM coordinates map across the whole physical screen. Foreground bounds are stored separately and still checked for movement before input. Single-step visual `open` requests constrain the point action to double-click for any visible item type, including PDF, PNG, Markdown, folders, shortcuts, and unfamiliar extensions. Missing local document names may fall back to full-screen vision; file-like names cannot be mistaken for a fuzzy installed-app name. Existing exact file/folder/app routes remain available.

68 regression tests passed after the capture and action changes, including an offset/small foreground window, full-screen click mapping, browser DOM and chat answers with a screen image, and open contracts for PDF/PNG/MD/custom extensions. When Qwen's locator reports a target missing, an exact, unique, confident OCR text match on the same full-screen image can recover its point. This does not inject an OCR label dump into the model. Missing/ambiguous OCR matches still stop without guessing.

The final live full-screen fixture passed: Qwen-selected BETA clicked at normalized `(398,468)` / physical `(764,562)` and activated once. `Open SAMPLE.pdf` planned a double-click; OCR recovered the visible label at normalized `(165,501)` / physical `(317,601)`, and the fixture's double-click/open callback fired exactly once. Both model images were the entire 1920×1200 display, while the foreground test window occupied only `(100,100,1022,856)`. This verifies a visible PDF-named test item, not a real PDF viewer. Full-screen visual recognition remains a model capability limit; the 2B model may still fail to recognize a visible object.

## Follow-up: PDFs and named files

Session `session-20261028-211622-991155.jsonl` confirms that `open Canva certificate.pdf` used a 351×171 crop of `System tray overflow window.`. Its saved model-input.png is blank/black, not a view of the desktop. The exact filename could not compensate for the wrong window being supplied. The preceding `open canva marketing certificate` request used a real desktop screenshot, but the planner conflated the distinct Canva and Marketing certificates. The visible `task_after_1.png` was also missed in a real Explorer image: visual recognition remains imperfect.

File opening had no filesystem route, although folder opening did. Consequently `README.md` reached fuzzy app lookup and launched an entry named Readme. Named documents/images now resolve from current Explorer and known folder entries before app/VLM routing. Exact filenames and unambiguous extension-free stems are supported; conflicting names ask for clarification. File launch reports a request to the default app, not a verified viewer state. File contents are not inspected for resolution.

The typing panel now excludes Gwen, the taskbar, tray overflow and tooltip windows when remembering the selected target. Relative `first folder` requests no longer get misinterpreted as a literal folder called first. 64 tests passed, including file/app precedence and target-filter regressions. A read-only check resolved the real Canva PDF, desktop README, and screenshot PNG paths. Tests mocked the OS launch call; they do not establish PDF-viewer rendering or universal visual reliability.

The failing FYP log contains valid, executable JSON. `(271,122)` is a legal normalized point, but maps to roughly `(520,146)` on the user's 1920-wide desktop, far from FYP. Repeating it cannot open the folder. The original logs did not retain the actual input image or prompt, so the exact historical inference cannot be reconstructed.

Offline tests used the user's attached desktop image, without sending any computer input:

| Input to the original visual planner | Model action |
| --- | --- |
| Screenshot without control dump | `double_click (77,545)` — FYP |
| Same image with OCR control names | `click (100,100)` — wrong target |
| Same image with simulated native names plus OCR names | `click (184,182)` — wrong target |

Two synthetic images with the target in different positions also changed the model's predicted click appropriately. Image input works; the model is not universally blind. The coordinate mapping tests account for window offsets and normalized coordinates. Larger image input preserves small desktop labels better, but resolution alone does not fix action selection.

A live fixture exposed a second problem: the model located the BETA button but chose double-click despite a single-click task. Prompt wording alone did not fix it. Restricting a large action/coordinate grammar to single-click produced `(0,0)` instead. These failed test inputs were blocked by the fixture's target/type guard.

A separate, short grounding query on the same saved fixture image produced `(688,580)` without a schema and `(680,588)` with a small point-only schema. This motivated separating action planning from target grounding.

## Implementation

- Desktop Qwen planning receives the screenshot, task and recent feedback, without the confusing UIA/OCR name dump. Existing named-control routes still use accessibility/OCR; browser planning still receives DOM IDs.
- The model first returns an action plus a description of its target. A second small visual query returns that target's normalized point. The executor validates and maps the point to the observed app window. This is general model-driven control, not a folder-specific shortcut.
- Explicit single/double/right-click requirements constrain the action types. Multi-step requests retain the full action set.
- Model images retain up to 1280×800 pixels instead of 640×400, preserving aspect ratio.
- An unchanged screenshot provides failure feedback; the same unchanged action is blocked before repeating it.
- A single requested click ends after that input instead of repeatedly asking the model for another click. Initial app focus is established once; later steps observe the current foreground result instead of repeatedly restoring the original window.
- Each task/step saves the exact image, planner prompt/schema, raw plan, grounding prompt/output and resulting action under the session's trace directory. The JSONL records window bounds and mapped screen coordinates. Traces stay local and may contain visible private screen information.

The 2B INT4 model can still misinterpret tasks or visual targets. Valid JSON is not evidence that an action is semantically correct, and passing small fixtures is not proof of reliability across arbitrary apps.

## Final verification

59 regression tests passed. `diagnostics/live-vlm-verification.json` records two live, bounded Agent.run tests using the actual local GPU model, real window screenshots, and real mouse input. Neither task matches the named-click, folder, direct-input, or OCR routes:

- `Select BETA using a single click.` → model plan + grounding → click `(679,600)` → physical point `(726,554)` → exactly one BETA activation.
- `Select the amber SAMPLE tile with a double click.` → model plan + grounding → double-click `(200,630)` → physical point `(284,576)` → exactly one SAMPLE-open event.

Both passed after the fixes. Earlier failed attempts and their model inputs remain in session traces. The fixture guards prevented executing wrong-target and wrong-click-type proposals; passing results required the real widget callbacks to fire exactly once. Multi-step behavior across arbitrary applications has not been comprehensively verified.
