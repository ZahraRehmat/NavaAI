# Offline voice commands

The resident Gwen panel has an **Offline voice** checkbox, a **Hands-free** checkbox and a **Mic…** device selector. With voice enabled, Gwen starts hidden by default. The startup shortcut starts the same background application after Windows sign-in. **Gwen show chat** or F10 explicitly opens the panel. It is not a topmost window and does not reappear after actions. F9 toggles the microphone; the checkbox and spoken controls are alternatives.

## Say commands

- **Gwen grid**, **open grid**, **turn on grid**, **grid on**: activate smart grid. **Close grid**, **turn off grid**, or **grid off** stops it.
- **Gwen click F G**: single-click the visible FG target. Letters can be separated naturally.
- **Gwen listen**: enable continuous hands-free commands once. Then say **F G**, **scroll down from F G**, **double click alpha bravo**, **release**, etc., without repeating Gwen. This setting stays active across commands, task failures, stop/F8 and restarts until explicitly changed.
- **Gwen sleep**: return to requiring Gwen before commands; this is not a muted microphone.
- **Stop**: stop the current task and release held buttons. Continuous listening stays enabled.
- **Gwen show chat** / **Gwen hide chat**: control the resident panel.
- **Gwen microphone off**: stop microphone capture. Re-enable it using the checkbox or F9; a microphone that is off cannot hear a wake word.
- In Excel: **Gwen cell A two** → `select cell A2`. In a hands-free session, **Cell A2** is enough. **Cell alpha twenty three** and digit-by-digit rows such as **cell B one two** are also normalized.
- For indistinct codes, use NATO spelling: **alpha bravo**, **foxtrot golf**, **six mike juliet**.

The panel records what was heard and the normalized command. Ambiguous or low-confidence results populate its command field without executing or opening the panel. A double-tone cue means attention is needed: repeat the command, or say **Gwen show chat** for details. For a reviewable code, say **confirm command** while continuously listening, or **Gwen confirm command** in wake-word mode. A missing grid code is not changed to a nearby label. For example `click six M J` becomes `click 6MJ` only when that exact label exists.

A short single tone signals task completion. A double tone signals an error, cancellation or review request. Tones play on an audio thread using in-memory PCM; no mouse, keyboard, activation, taskbar notification or message-box API is used. The microphone briefly ignores cue playback to prevent self-recognition. A completion never deiconifies, lifts or focuses the panel, so menus and dropdowns are not dismissed by Gwen's completion UI. Actual action execution can still legitimately focus its intended target. On a necessary choice/confirmation request, the voice-enabled choice window and marks use no-activate styles; they do not force keyboard focus. Explicit **show chat**, F10 and relaunch requests may raise the panel because the user requested it.

Choice popups accept spoken letters (for example **alpha**, **option B**) while the popup is active. Action confirmation popups accept **yes** or **no**. An answer captured before a different popup appeared is ignored. Normal typed commands and popup buttons remain available.

## Lightweight recognition and correction

The default is now a hybrid: Vosk small English-US handles recognized commands, power controls, keyboard actions and grid codes. Faster-whisper base.en handles dictated text and selection endpoint phrases using CPU int8. Ordinary commands never fall back to Whisper. A separate small Vosk control grammar can recover mode controls from catalog-word competition when confidence is high and the ordinary decoder shares a command word. The additional dictation model is approximately 145 MB. Both run locally after a one-time download; no microphone audio is uploaded. Run `setup_dictation_voice.py` to install/re-enable this configuration. Models are loaded once and reused; Qwen is not loaded for dictation. A bounded vocabulary includes command words, canonical letter/number pronunciations, NATO spellings and words from visible target names. Short contextual phrases improve code decoding. An unknown-word path is retained; there is no forced nearest-label conversion. The normal vocabulary graph can be used for free names/prose if the command graph reports unknown words.

Correction is deterministic and restricted to known command slots. It maps spoken letter names/NATO words and number words to a code, checks visible labels, and validates Excel references against Excel's row/column limits. Dictated content following `type`, `write` or `dictate` is left literal. It does not use a generative model to rewrite intent, invent missing words, change filenames or create a plausible command from fragments.

Recognition confidence is a heuristic, not a calibrated probability. Small recognizers can still confuse accents, similar letters and noisy speech. Words outside the model dictionary may be unavailable in constrained command mode; use a visible grid label or review a typed command. English is the configured recognition language. This is not an Urdu/multilingual model.

Audio segmentation uses adaptive RMS activity detection, roughly 900 ms of trailing silence and a bounded utterance length. Typical synthetic decoding took approximately 0.1–0.4 seconds after segmentation; live latency additionally includes silence detection, device buffering and the requested action. Timing and accuracy are not guarantees. Microphone and processing queues are bounded. Overflow, cancellation and microphone changes discard pending audio rather than stitching old fragments together. Speech captured while another task runs is not queued for later execution, apart from the stop control.

Grid context is captured when speech starts. Reused labels, changed grid modes and changed target windows invalidate pending commands. A confirmation for a reviewed command expires after 20 seconds. Existing grid/native/Office execution checks still apply.

## Fully offline runtime

The model is loaded from `models/vosk-model-small-en-us-0.15`. Runtime recognition does not download, use an API key, contact a speech service, or send audio/transcripts to a server. Captured microphone audio is processed in memory and not recorded to a file. Recognized/normalized commands are shown locally; commands actually sent to the agent follow its existing local session logging. Requested browser or connected-app tasks can naturally use the internet; that is separate from speech recognition.

First-time installation or recovery:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_command_voice.py
```

The setup script performs the one-time official model download and records its source and SHA-256 hash. Recognition then works without internet. The previously installed Whisper model and API remain for compatibility but are not loaded by the default voice path.

Settings are in `voice_config.json`: microphone state, last hands-free selection, hidden startup, completion beep, model path, input device, silence duration and confidence thresholds. **Gwen listen** saves hands-free mode; **Gwen sleep** or turning voice off saves wake-word mode. **Mic…** selects a Windows input device. If capture is unavailable, the panel reports it. Protected Windows sign-in still needs Windows Voice Access or a separately trusted accessibility component; this ordinary desktop listener does not implement secure-desktop password input.

## Verification

`verify_offline_commands.py` generates temporary Windows SAPI audio, blocks socket connections during model loading/recognition, and checks the full recognizer → contextual correction → voice-session routing path. It verifies cell A2, mixed alphanumeric code 6MJ, ordinary and NATO grid letters, scroll commands, wake/sleep controls, silence and artificial noise. Temporary audio is removed. The report is `diagnostics/offline-command-speech-verification.json`.

`test_speech_context.py` covers homophone ambiguity, invalid-label rejection, literal text preservation, cell number parsing, wake/session controls, confidence review, changed grid context, busy input, malformed chains and stale capture epochs. A real default microphone was opened and 3,200 samples captured in memory without overflow. The UI's voice checkbox was toggled off/on and confirmed the microphone-listening state. Human accent, distance and room-noise accuracy still require a live user trial; synthetic recognition is not evidence of perfect human recognition.

`test_background_voice.py` verifies listening stays latched over repeated commands, stop, review and elapsed time; the production completion presenter cannot restore/focus a fake panel; cues are short PCM and run asynchronously; and audio can be flushed without reopening the input device. `diagnostics/background-completion-cue-verification.json` records a real tone with foreground HWND and pointer unchanged. This establishes that audio feedback itself does not interact with the screen.

Sources: https://alphacephei.com/vosk/models and https://github.com/alphacep/vosk-api
# Assistant on/off and remote visibility

Say or type **Gwen turn off** to cancel the task, release held buttons, close grids/choices and hide the chat, pointer halo and status badge. Ordinary commands are ignored while off. **Gwen turn on** restores the halo/badge and continuous voice commands without reopening the panel. The preference is saved. F9 also reactivates a powered-off assistant.

Voice reactivation requires a microphone listener: “off” is a **wake-only standby**, not microphone shutdown. Its local recognition grammar is restricted to the on/off phrases; it does not dispatch normal commands or invoke Qwen. **Gwen microphone off** releases microphone capture, and **Quit** exits the process; either requires a manual launcher/hotkey to resume. Exact on/off phrases take precedence over dictation, busy tasks and pending choices.

The badge and cursor halo now use Windows `WDA_NONE` (capture allowed), rather than `WDA_EXCLUDEFROMCAPTURE`. This allows desktop capture/remote-control tools such as RustDesk and AnyDesk to include them. Their actual capture mode and viewer settings can still affect display; a remote viewer must verify the end-to-end result. Windows tests check capture affinity, passive visibility toggling and unchanged foreground/pointer.



## Voice typing and editing (grid on or off)

Focus the app's text field, say **start dictation** (or **type**), then speak phrases. Say **stop dictation** to return to ordinary commands. **Type hello** is a one-shot text command. A short backlog retains up to eight dictation/editing phrases while typing; it expires after 30 seconds and clears on Stop, errors, app changes or cancellation. Unrelated agent commands are not queued. Routine task completion no longer flushes microphone audio. Avoid changing fields while dictating.

- **Press Enter**, **hit return**, **press the Enter key**: sends the real Enter key. Word may insert a paragraph; WhatsApp may send a message. The target app decides.
- **Select from father to sun**: selects the inclusive text span in the focused accessible text field. Case and repeated spaces are ignored. Common homophones can match existing text only when the exact word is absent. Repeated start phrases require a longer phrase; nothing is guessed.
- **Select all**, **copy it**, **cut it**, **paste the thing**, **paste the stuff**, **paste the copied data**, **paste what I copied**, **undo**, **redo**: ordinary app keyboard shortcuts.
- **Increase font**, **decrease font**: use native Office formatting for Word/Excel/PowerPoint. Other apps receive the common rich-text shortcut; unsupported apps may ignore it. Notepad reports that selected-text formatting is unavailable.
- Editing commands also work while dictating. To enter the words “press enter” literally, say **type press enter**. Close/open app requests remain literal text until dictation ends; power and emergency Stop retain priority.

Spacing checks the actual caret/selection through Windows TextPattern (or DOM for an owned background browser). A new phrase gets one leading space if it follows non-whitespace text. Existing spaces/newlines, punctuation, start of field and selection replacements do not get an extra space. Apps without accessible caret text receive the literal phrase; spacing/word-range selection cannot be guaranteed in them. Password fields are not read.

Single-line native typing uses Unicode keyboard packets, preserving the user's clipboard including rich copied data. Multiline/tab payloads retain the existing paste path. Copy and paste commands use the app's clipboard normally. Text selection does not copy the whole document into the clipboard.

The dictation pause is 1.2 seconds; command pause remains 0.9 seconds. Recognition is not generative paraphrasing: the transcript is typed as heard. Accent, distance, noise and microphone choice still affect recognition. Low confidence is reviewed, not silently rewritten. Two recognizers may share command confidence only when their parsed keyboard actions independently agree.

`test_voice_typing.py` covers parsing, grid passthrough, dictation editing, actual-caret spacing rules, repeated-span rejection, queue cancellation, Unicode packets and owned headless Chrome textarea/contenteditable selection and replacement. Synthetic SAPI recordings are diagnostic samples, not evidence of human-accent accuracy.

References: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Windows UI Automation text selection](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/find-and-highlight-text-using-ui-automation).


## Selection mode: select and copy a spoken range

After **stop dictation**, say **selection**. The badge changes to **Selection**. Then say **Islamabad to Karachi** or **from Islamabad to Karachi**. Gwen selects the inclusive span (both endpoints and everything between them) and copies the actual matched text to the Windows clipboard. **Paste the stuff** pastes it normally. Grid may be on or off. Typed commands in the resident panel support the same mode and range syntax. **Selection Islamabad to Karachi** and **select and copy from Islamabad to Karachi** also work as one-shot commands.

Selection mode remains active for another range. Say **stop selection** to return to ordinary commands, **start dictation** to type again, or **stop** to cancel. Power off, microphone off and emergency Stop clear selection mode. A range spoken while another task is busy is reviewed rather than queued. The badge/panel stays passive.

Endpoint speech uses the offline English decoder instead of treating place names as grid codes or constrained command vocabulary. Recent dictated words provide recognition hints. Each selection utterance accepts one complete range sentence; decoder text after that sentence is excluded rather than appended to the endpoint. Low-confidence endpoints still require repetition. Exact text matches take priority; a unique close spelling such as “Islamad” can match an existing “Islamabad.” Conflicting close spellings require more context. Repeated words offer lettered choices with surrounding text, line and character positions. Choose the start and end separately when both repeat; later end occurrences are never silently replaced by the nearest one. Say **from second father to last sun**, **from first Islamabad to third Karachi**, or **the second occurrence of father** to specify occurrences directly. Counts refer to the text available from that provider, in reading order. Choices are paged so later occurrences remain reachable. Cancel leaves selection and clipboard unchanged. The text and target are checked again after choosing.

The focused text provider is tried first. If it has no match, a bounded accessibility scan checks visible document/edit text providers in the same active application. No app switch or blind mouse drag is used. Selection must succeed before the clipboard is changed; only the matched text is copied. Images/canvases and apps without selectable accessibility text are unsupported by this path. A failed selection reports that limitation without copying unrelated content.


## Reliable mode controls

**Dictation on**, **start dictation**, **start typing**, **typing on**, **enable dictation** and **typing mode** enter dictation. **Dictation off**, **stop dictation**, **stop typing**, **finish typing** and **end dictation** exit it. The badge must show **Dictating** before free speech is treated as text. Mode controls have an independent bounded vocabulary with an unknown-word path. A compact recognition only overrides the ordinary decoder when it is a complete known control phrase, mean confidence is at least 0.90, each word is at least 0.65, and both decoders share a substantive command word. Thresholds for ordinary commands are unchanged; unrelated speech is not converted into a mode switch.

Whisper is no longer a fallback for unknown ordinary commands, preventing low-confidence added sentences from replacing mode commands. For one-shot typing, a clear Vosk `type ...` transcript can be retained if the English decoder is below the normal confidence threshold. Recognition logs include decoder backend, rescue primary transcript/confidence, decoding time, and captured mode. The runtime status also includes dictating/selecting flags.

`test_voice_control_recognition.py` covers dictation aliases, compact control recovery, unrelated/weak-control rejection, ordinary-command isolation and one-shot typing fallback. Two synthetic system voices passed 12 mode-control samples. Live microphone/accent testing remains separate from those synthetic checks.


## Raw dictation, requested punctuation and erasing words

Continuous dictation now removes the speech recognizer's automatic sentence/clause marks, so a pause does not add a full stop. Decimal numbers, in-word punctuation, URLs, email addresses and contractions are preserved. Typed commands outside dictation retain their explicit punctuation.

Say **punctuate it**, **punctuate this**, or **add punctuation** to restore punctuation in the selected text, or the current editing scope when nothing is selected: the Word document, Excel active text cell, PowerPoint text box, or focused text field. The new SentencePiece dependency is small; a pinned ~209 MB English ONNX model is downloaded once by `setup_punctuation.py`. ONNX Runtime runs it locally on CPU with two threads, and the model is loaded on demand. No text is uploaded and Qwen is not loaded for this command.

The model predicts full stops, commas and question marks. Existing quotations are preserved; paired spoken **open quote ... close quote** markers can be converted to quotes when punctuating. Conservative direct-speech rules also handle simple greetings/answers introduced by said/replied/whispered/shouted. Quote interpretation is not guaranteed for arbitrary prose. The model's token surfaces are retained to preserve names, URLs and Unicode; word-preservation checks reject changed wording before editing. Paragraphs, tabs and Word cell markers remain in place. There is a 20,000-character scope limit.

Word receives minimal edits in reverse order rather than full-document replacement, preserving existing character formatting and grouping the operation in one custom Undo record when supported. Excel formulas are excluded. Other supported fields use ValuePattern or native text replacement; some apps may require selecting one paragraph. Focus changes, read-only/password fields, or changed source text stop the edit. Browser text fields and contenteditable text are edited without pressing Enter or sending messages. Generic app undo support depends on the app; Word's custom Undo grouping is tested separately.

- **Erase it**, **erase that**, **delete last word**, bare **backspace**/**back space**: Ctrl+Backspace, deleting the previous word at the caret (the app handles an existing selection).
- **Press Backspace**/**press back space**: the actual single-character Backspace key.
- **Copy it**, **copy it to clipboard**, **paste**, **paste here**, **paste the copied data**, **paste the stuff**: work in dictation, selection, and ordinary active command mode. Paste needs a focused field, not dictation/selection mode. Gwen must be on/listening, as with other voice commands.
- **Type erase it** or **type punctuate it** enters those words literally while dictating.

The compact command grammar includes punctuation/erase/clipboard phrases. Model fallback cannot boost confidence merely because unrelated speech shares “it” or “here.” `test_dictation_punctuation.py` covers raw punctuation removal, word guards, all-mode clipboard/erase commands with grid enabled, real offline model output, quotation marks, paragraph/number preservation, minimal Word edits and Undo grouping, and owned headless browser editing including selection scope, bold preservation and read-only refusal. Six synthetic speech command samples passed; human accent/microphone testing remains separate.

Model source and license: [English punctuation restoration, Apache-2.0](https://huggingface.co/1-800-BAD-CODE/punctuation_fullstop_truecase_english), pinned revision `b26fd1c40e88678859048898218ea4edcc24c84a`.


While a choice popup is open, its bounded offline Vosk grammar takes priority over selection/dictation speech. Say **B**, **bravo**, **select D**, **click delta**, or **cancel**. Only letters for current choices are accepted. Audio from an earlier dialog is discarded, and accepted/rejected answers are recorded in `logs/voice-decisions.jsonl`. Low-confidence answers leave the choice pending. Six synthetic SAPI choice samples passed; human microphone/accent performance still requires live testing.


Repeated-word selection now uses TextPattern bounding rectangles to mark the actual visible endpoint words with A, B, C badges above them. A compact banner asks for the START or END point and is placed in the corner covering the fewest candidates. Voice choice recognition stays active. If some occurrences are outside the visible text, their letter/occurrence choices remain in the compact banner; providers without word positions retain the text-choice fallback. Marking reads text geometry without changing selection or scrolling the document.


### Selecting displayed text

Selection is also available for non-editable text: browser pages, chat responses and other active-app text exposing Windows TextPattern. The scanner includes selectable Text/Custom/Pane/Group providers and embedded renderer processes within the target window, not just typing fields. A matching document covers its nested paragraphs once, preventing duplicate text-area choices. Distinct matching areas can be chosen before endpoint choices. Empty visible-range results require actual endpoint rectangles before a document fallback is accepted.

For an owned browser connection, a range absent from the focused field falls back to visible rendered page text and frames. Hidden text, script/style contents, password/input values, off-screen nodes and text marked non-selectable are excluded. DOM node identity and content are checked again before selection; the actual resulting selection is copied. This does not turn screenshots, images or inaccessible canvases into selectable text.

Bring the desired app to the foreground, say **selection**, then **from <start phrase> to <end phrase>**. The range is selected and copied; **paste** works in the destination field. Displayed text uses the same occurrence choices, direct word markers when native geometry is available, and speech-friendly labels as typed text.


### Chromium range mapping repair

Chromium/Electron TextPattern.FindText can return a prefix range whose text differs from the requested string across block boundaries. Native selection now builds character-offset ranges and verifies the exact resulting text before using them for markers, selection or copying. A search fallback requires exact prefix and final-span verification. Read-only live checks reproduced the original error in ChatGPT and Chrome and verified exact character ranges without calling Select or changing the clipboard.

Selection mode now primes a nonblocking cache of visible vocabulary from the current app for the offline English decoder. Readable Document providers take precedence over toolbar/edit labels. Cache identity includes window, PID, title and bounds; power off clears it, and pending old reads cannot repopulate it. Hints improve context but do not authorize invented words or bypass speech-confidence checks.


### Multiple running app windows

**Switch to Chrome/Word/etc.** now asks which window when several windows match, including when one is already active. Choices show a window number and title plus a speech-friendly letter. Say **two**, **window two**, or the displayed letter/NATO spelling. Grouped taskbar app buttons in smart grid use the same chooser instead of leaving the user at a hover-preview strip. Cancel and Stop do not switch; the selected HWND/PID is checked again before activation. Existing single-window switching stays immediate.


### Verified foreground activation

A flashing taskbar icon does not prove a successful switch. Window activation now restores minimized windows and first requests the foreground normally. If Windows refuses a background voice worker, Gwen temporarily attaches its input queue to the foreground/target threads, brings the requested window forward, verifies it, and detaches every successful attachment in a finally block. It does not simulate Alt/Enter or change Windows foreground-lock settings. Opening an installed app reuses matching running windows (with the existing chooser); a newly launched app is polled for its actual window before activation is reported. Existing personal browser windows are reused for explicit open-browser app requests. Owned visible browser launches also verify their native window. Background app launches retain launch-only behavior. Smart-grid taskbar app buttons with a running-window count use activation instead of the taskbar toggle, including single-window apps.


Dense grids and selection/window choices now reuse the restricted speech-friendly alphabet in two-/three-letter combinations rather than introducing confusable letters. The Vosk grid grammar omits unused standalone letter/NATO choices; explicit keyboard chords such as Ctrl+C and real Excel column letters remain available. Browser tab commands take priority over grid mouse parsing. New tab-selection verification prevents a failed selection from closing the wrong tab. Four synthetic SAPI samples for tab two/current tab/close AF/bravo passed; live human speech accuracy still depends on microphone and pronunciation.


### Direct command runtime (Qwen removed)

The resident assistant no longer imports or calls Qwen for visual actions, unfamiliar Office commands, or general questions. Existing deterministic app/window, browser/tab/media, Office, grid, text selection, clipboard and dictation tools remain. Unsupported input returns a short explanation after existing direct lookups; it does not start a visual planning loop. Vosk/Whisper speech recognition and the separate offline punctuation model remain. Downloaded Qwen files and historical diagnostic/planner source are retained unused for recovery.


### Popular website names

The offline website directory indexes 10,000 downloaded Tranco domains, domain-brand names and curated spoken aliases. Vosk includes supported dictionary words from the directory and bounded complete phrases for prominent names, such as **open Wikipedia on Edge**, **open you tube on Chrome**, **open Google Meet on Edge**, and **open stack overflow on Chrome**. Plain domain addresses and spoken **dot com/org/etc.** are supported. Unknown names are not turned into arbitrary websites; only a uniquely strong one-character site-name typo is accepted. Dictation payloads are unchanged. The five synthetic website samples passed, with decoding about 0.13–0.31 seconds in that run. No Qwen or runtime ranking download is involved.


### Direct Excel cell commands

When Excel is active, explicit cell/range, editing and targeted copy/paste commands take precedence over generic text-selection and dictation payload parsing. **Type ...** remains literal. Spoken **select from B two to N six**, **edit J seven**, **copy cell C nine**, and **paste copied data in cell K ten** resolve to native addresses. **Edit J7 and start dictation** enables dictation only after selection/edit entry succeeds and the same live window/task epoch is still active. No mode switch occurs after a failed/stopped edit. Generic **open dropdown** uses the existing bounded chooser grammar and marked native controls; the regular grid is temporarily hidden while those choices are shown.
