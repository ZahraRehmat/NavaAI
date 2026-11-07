# Expanded Office tools

Offline voice commands are available: say **Gwen listen** once, then **grid**, **F G**, **scroll down from F G**, **cell A two**, etc. Continuous listening stays on through tasks, errors and stop/F8; **Gwen sleep** or voice off ends it. Gwen runs hidden by default and does not restore its panel after actions; a short completion beep replaces that behavior. **Gwen show chat** or F10 opens the panel explicitly. The small local Vosk recognizer uses contextual code correction without an LLM rewrite. Uncertain commands are held for review with an attention cue. See [OFFLINE_VOICE.md](OFFLINE_VOICE.md).

Automatic startup: Gwen starts for this user after Windows sign-in through its Startup shortcut. Manage it with `.venv\Scripts\python.exe startup.py enable`, `disable` or `status`. Offline voice starts in wake-word mode when enabled. Password/PIN-screen voice control requires Windows Voice Access or a separately trusted accessibility component; see [STARTUP_AND_SIGN_IN.md](STARTUP_AND_SIGN_IN.md).

Adaptive smart grid is available across visible windows, taskbars, shell menus and exposed desktop icons: type `Gwen grid`. Type `A`, `press B`, `select Chrome`, `open C`, `click Windows button`, `scroll down on C`, or `drag A to B`. Taskbar names accompany labels. Windows change events trigger refreshes, unchanged roots are cached, and targets retain their labels as they move. `Gwen full grid` switches to the uniform pixel grid; `exit grid` restores the agent. See [SMART_GRID.md](SMART_GRID.md) for commands, refresh behavior and coverage limits. Voice remains off.

Full manual grid is now available: type `Gwen full grid`, then a cell such as `C3`, `double click C3`, `scroll down on G4`, `hold C3 and move right 100 and release`, or `drag C3 to E3`. `exit grid` restores normal agent commands; F8 always stops grid mode and releases the mouse. All physical display pixels belong to cells, with zoom and pixel nudges for fine targeting. Voice remains off. See [FULL_GRID.md](FULL_GRID.md) for commands, exact coverage, multi-monitor labels and test limits.

Browser tabs and video: `pause video`, `pause youtube`, `play video`/`resume video`, `open new tab`, `close current tab`, `next tab`, `previous tab`, `switch to the second tab`, and `switch to YouTube tab` have direct routes. Named tabs use partial matching and the A/B/C chooser on ties. Explicit tab/media commands can reuse the last selected browser or discover an existing browser window; multiple windows ask which one. App names still use app/window switching unless you say "tab". Managed browsers use DOM tabs and media state. Ordinary Chrome/Edge use their native tab-strip selection, standard new/close shortcuts, and exposed Play/Pause controls. Pause is not a blind toggle. Unsupported/hidden player controls ask you to show the controls rather than guessing a key; an unsaved-work tab-close prompt is not dismissed automatically. diagnostics/tab-media-ui-verification.json records a real typed-chat test in an isolated Chrome profile, with no personal tabs used.

Target choices: browser/native/OCR clicks and file lookup now use confidence-based matching in the typed GUI. A strong unique match proceeds automatically. Lower-confidence matches or close competitors show a popup with A/B/C choices; press a letter or click a card. Visible native/OCR targets get amber lettered outlines; managed browser targets get page outlines plus a preview. Duplicate files/folders show their full paths; file icons are outlined only when their paths can be tied to the current Explorer/Desktop view. Offscreen files appear as popup cards. Cancel/Esc/F8 executes no pending selection. Labels are checked again before clicking. Scores measure label similarity, not probability or unrestricted semantic understanding. Original conservative matching remains available in non-GUI callers without a chooser.

Existing-browser repair: a selected window titled Google Chrome/Microsoft Edge/Chromium is recognized before routing. `open youtube.com`, `open youtube website`, and `search cats` use deterministic browser routes. Ordinary existing browser windows navigate through Ctrl+L, the URL, and Enter with focus checks; this reuses the selected window without opening another profile. Gwen-owned browser sessions retain DOM control and are identified by process identity, not coincidentally matching page titles. An ordinary browser is not automatically a DOM-connected session. If its selected window changes during input, navigation stops. Files such as README.md remain file requests. See diagnostics/native-browser-ui-verification.json for a real chat-to-Chrome navigation/search test in an isolated profile; search traffic was intercepted locally and personal tabs were not used.

Window and table updates: `close this window` asks once before a graceful close; app save prompts stay for your choice. `switch to Word`/`switch to Chrome` activates an already running window. `delete E5` clears contents; `delete cells E5:F6 shift up` structurally deletes cells; `delete the table` removes table and contents. New Word tables have visible black lines. `change table outline colour to blue` changes inside/outside lines. See OFFICE_CAPABILITIES.md for distinctions and examples.

App launch routing restored: installed-app names, aliases and confident spelling matches are checked before approximate file lookup. `open microsoft word`, `open whats app`, `open steem`, `open chorme` and `open vs studio` use the app catalog. Explicit filenames/paths and folder requests retain file/folder routing. Near-tied app names ask for clarification. See diagnostics/app-resolution-verification.json for catalog-routing checks; those checks intercept launches rather than opening every app.

See [OFFICE_CAPABILITIES.md](OFFICE_CAPABILITIES.md) for the new native formatting, colors, lists, table, sheet and slide tools, command examples and measured limits. Type /office or /office search chart in the corner chat. Voice remains off.

## Owned dialog targeting

Save-dialog commands follow the selected app's visible owned popup. Save/Don't Save/Cancel/Yes/No/OK require actual native buttons and do not fall back to chat/screen prose. Exact labels beat partial matches such as Don't Save and AutoSave. Observations stay bound to the intended window; a changed dialog is observed again once before any further input. Font-size and table-removal tools are now included; see OFFICE_CAPABILITIES.md.

## Flexible matching and native Office commands

Short, reordered titles, common aliases, optional extensions and small typos now match actual visible labels and filenames using RapidFuzz and label_aliases.json. The closest unique match is used and reported; near ties ask for clarification. A unique matching title with a different year is reported explicitly. Example: click 2024 datesheet mahnoor can identify Datesheet+2023-Mahnoor_Karachi.Pdf and report the year difference.

Word, Excel and PowerPoint now have local native Office adapters for common formatting, text-entry and table actions. Select the intended Office document, then try bold Mahnoor, make it bold, write hello in A1 (Excel), or insert a table with three rows and four columns. Native commands do not automatically save. See OFFICE_AND_MATCHING.md for capabilities, verification and limits.

## Whole-screen visual control

Every computer-control model call now receives the whole current primary screen, including desktop, windows and taskbar. The model image retains up to 1920Ã—1200 pixels while preserving the whole frame. Desktop clicks use full-screen coordinates, with foreground bounds checked separately for movement. Browser DOM control remains available with the full physical-screen image as context.

For visible items, `open ...` uses a double-click regardless of file type: PDF, image, Markdown, folder, shortcut, or unfamiliar extension. A missing local file can fall back to full-screen vision. If Qwen misses a visible text target, an exact and unique OCR match on the same screen image may recover its location; ambiguous/missing matches stop. Existing exact filesystem and app launch routes remain available. Voice remains off.

## Visual planner repair (28 October 2026)

Qwen now plans an action and target description, then uses a separate short visual grounding query to locate that target. Desktop image input retains up to 1280Ã—800 pixels; UIA/OCR label dumps no longer mix into the visual planner. Named-control routes and browser DOM controls remain available. A single-click request ends after one input, and subsequent task steps observe the current window instead of refocusing the old one. Exact model inputs and mapped coordinates are saved locally beneath each session in logs/. See DIAGNOSIS.md for measured failures, fixes, and verification limits.

Folder commands now resolve exact directory names in Desktop (including OneDrive redirection), Documents, Downloads, and current Explorer locations before invoking Qwen. Example: `open FYP folder`. Duplicate names require a full path; missing explicit folder requests stop without visual guessing. Explorer location is checked after launching to verify that it opened.

## Current testing mode: typing only

Start Gwen.cmd opens one small corner chat. Voice recognition, microphone capture, and spoken replies do not start. Type in the bottom box and press Enter or Send. Select the target app before entering a command; Gwen remembers that app while you type. The panel hides during execution and returns with the result without forcing keyboard focus. F8 stops; F10 shows/hides the panel; Quit or the close button exits.

A thick cyan cursor halo starts with the app and turns amber during a task. It is click-through, uses no global cursor settings, and disappears on exit. Windows capture exclusion is requested to keep it out of model screenshots.

Native Windows UI Automation and managed-browser DOM labels are already used before OCR. Accessibility coverage depends on the app. Pixels in images still require OCR or vision. Older voice-mode documentation below describes the retained, inactive implementation.

# Gwen Doer 2.0

A resident Windows assistant with local voice recognition, spoken replies, direct mouse/keyboard commands, OCR, browser control, and your copied Qwen3-VL model.

## Use it

Double-click **Start Gwen.cmd** once. Gwen stays running after you close the chat window; use the small dock to reopen it or quit. Launching it again brings back the same session.

- Enable **Hands-free session** once. It turns on the microphone and accepts commands without repeating a wake word. Alternatively, press **F9**, say **Gwen listen**, then continue hands-free.
- Say **Gwen sleep** to end the hands-free session. You can still give a single command as **Gwen, scroll down**.
- **F9** listens for one command from any app, without opening the chat.
- **F10** shows or hides the chat. **F8** stops the task and spoken reply, and clears pending commands.
- Closing the chat hides it to the dock. **Quit** on the dock ends the program.
- The **Microphone** checkbox releases/reopens the microphone. Say **Gwen microphone off** to turn it off by voice; use F9 or the dock to enable it again.

## Examples

```text
Gwen listen
open chrome
search youtube.com
scroll down
scroll up
click here
click on Netflix
open WhatsApp
open Kashaf Uni chat
type Hello there
press enter
select all
Gwen sleep
```

For **click here**, point the mouse at the intended spot before speaking. Gwen retains that pointer position while speech is recognized. If the window moves or the point is outside it, the click is refused. Named clicks use observed Windows controls or local OCR and do not guess a location for a missing label. Scroll, click-at-pointer, typing, and key commands bypass Qwen entirely. Typed mistakes such as `sroll up` and `clikc herte` are recognized.

Commands act on the foreground app captured when the utterance ends, or the app you explicitly open/name. The chat stays hidden after tasks, and the dock hides during input so it does not cover the target. **Target** in the chat shows the last foreground app.

For voice conversation, ask a question such as **Gwen, what is a neural network?** Qwen gives a short reply, read aloud when **Spoken replies** is enabled. This is local conversation, not a live web research service. Open a browser and request a search for current information.

## Voice setup

The downloaded English speech model is `models/whisper-tiny.en`. Recognition uses faster-whisper on CPU with INT8; speech replies use the installed Windows SAPI voice. Once the speech model is present, voice processing is local and requires no speech API key. Live microphone audio is held in memory, not saved. Accepted command transcripts are included in local session logs. The WAVs under `voice_test_audio/` are generated test speech, not microphone recordings.

The system-default microphone is selected initially, with recording off until you enable Hands-free or press F9. Choose another input in the chat if necessary; the dock's meter shows input level. During spoken replies, microphone processing pauses to avoid hearing Gwen's own output. F9 interrupts a spoken reply and arms the next command; F8 stops it. Speech recognition can mishear names and accents; the recognized command is shown as **Heard** in the chat. Background fragments without a complete action/question are ignored; a plain `reset` resets conversation instead of going to the mouse-action model.

`setup_voice.py` downloads the small speech model if it ever needs restoring. `requirements.txt` pins the audio decoding version compatible with the installed speech recognizer.

## Browser and app control

Chrome/Edge tasks use a separate persistent browser profile inside `browser_profiles/`; your personal tabs/sign-ins are not automatically connected. Background browser mode is available. Reachable controls in visible frames are observed; popup-covered controls are excluded. CAPTCHAs and verification barriers require manual help.

The app directory indexes Start apps, registered executable paths and Desktop/Start Menu shortcuts. `/apps` lists entries, `/refresh` rescans, `/reset` clears task memory. `aliases.json` adds nicknames. Simple launch typos such as `oepn store` are corrected. Windows blocks input to apps running at a higher integrity level; Gwen reports that limit and never automatically elevates itself.

## What was tested

- Local recognition of generated speech for wake/session commands, scroll down/up, click here and sleep.
- Opening the default microphone and receiving audio samples.
- A live test window: real scroll down/up, click-at-pointer and Unicode clipboard typing, with Qwen never loaded.
- Resident UI startup/shutdown and single-instance signaling.
- Browser overlay/frame/stale-control regressions and the earlier Qwen-driven Word action.

Your own speech/accent and every application are not verified. Qwen3-VL-2B can still choose an incorrect action on more complex tasks; simple input commands do not depend on it. Original NavaAI files/model remain outside this folder and were not modified.

See `TESTING.md`, `voice-verification.json`, and `live-input-verification.json` for evidence. Run tests with this folder's `.venv/Scripts/python.exe`.
