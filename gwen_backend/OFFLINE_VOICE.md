# Offline voice commands

The resident Gwen panel has an **Offline voice** checkbox, a **Hands-free** checkbox and a **Mic…** device selector. With voice enabled, Gwen starts hidden by default. The startup shortcut starts the same background application after Windows sign-in. **Gwen show chat** or F10 explicitly opens the panel. It is not a topmost window and does not reappear after actions. F9 toggles the microphone; the checkbox and spoken controls are alternatives.

## Say commands

- **Gwen grid** / **Gwen full grid**: activate either grid.
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

The default recognizer is Vosk with the small English-US 0.15 model: approximately 40 MB to download, 71 MB unpacked. It runs on CPU and does not load Qwen or Whisper for speech. One model instance is reused. A bounded vocabulary includes command words, canonical letter/number pronunciations, NATO spellings and words from visible target names. Short contextual phrases improve code decoding. An unknown-word path is retained; there is no forced nearest-label conversion. The normal vocabulary graph can be used for free names/prose if the command graph reports unknown words.

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
