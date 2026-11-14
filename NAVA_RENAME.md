# NAVA AI — branding and command rename

Updated 15 November 2026. **Display name: NAVA AI. Command name: Nava.**

## Commands to use now

Replace the old wake name with **Nava**. Capitalization does not matter. `NavaAI` and `Nava AI` are display-name spellings, not command prefixes. The previous wake name is rejected as a prefix, including during a hands-free session.

| Previous command | New command | Purpose |
| --- | --- | --- |
| Gwen turn on | **Nava turn on** | Activate the assistant and continuous microphone commands |
| Gwen turn off | **Nava turn off** | Return to wake-listener standby |
| Gwen switch on / off | **Nava switch on / off** | Equivalent power commands |
| Gwen listen | **Nava listen** | Enable continuous hands-free commands |
| Gwen start listening | **Nava start listening** | Enable continuous listening |
| Gwen sleep / stop listening | **Nava sleep / Nava stop listening** | End continuous listening; named commands remain available |
| Gwen show chat | **Nava show chat** | Show the command panel |
| Gwen hide chat | **Nava hide chat** | Hide the command panel |
| Gwen microphone off | **Nava microphone off** | Stop microphone capture; F9/UI is then needed to restore it |
| Gwen stop / cancel | **Nava stop / Nava cancel** | Stop the current action and release held input |
| Gwen confirm command | **Nava confirm command** | Accept a displayed, confirmable speech candidate |
| Gwen grid / smart grid | **Nava grid / Nava smart grid** | Turn on smart-grid labels |
| Gwen open Chrome | **Nava open Chrome** | Run an existing app command with the new wake name |
| Gwen press enter | **Nava press enter** | Run an existing keyboard command with the new wake name |

## Dictionary controls

These commands retain their existing wording. Each can also be prefixed with **Nava**, for example `Nava show dictionary`.

- **show dictionary / open dictionary / show commands** — show the contextual pane.
- **hide dictionary / hide commands** — hide it; keep the status badge and compact reminders.
- **dictionary more transparent / make dictionary more transparent** — make the pane lighter.
- **dictionary more visible / make dictionary more visible** — make the pane clearer.
- **move dictionary left / move dictionary right** — dock it on either side.
- **next commands page / previous commands page** — change contextual pages.
- **open full dictionary / show full dictionary** — open the searchable manual.
- **search dictionary for font** — search for a command or topic.
- **dictionary scroll down / dictionary scroll up** — scroll the master manual.
- **close full dictionary** — return to the contextual pane.

Ordinary commands such as `open grid`, `grid off`, `dictation on`, `dictation stop`, `selection mode`, `press enter`, app switching, Office commands and YouTube controls retain their wording. They do not require a wake name during an active hands-free session. Dictated content and `type ...` payloads remain literal: saying a person's name or writing `Nava AI` does not rename or execute that text.

## Visible branding and launch files

| Area | New label |
| --- | --- |
| Status badge and headers | **NAVA AI** |
| Typed command panel | **NAVA AI - Type commands** |
| Status window | **NAVA AI - Status** |
| Command overlay | **NAVA AI - Command overlay** |
| Full manual | **NAVA AI - Full dictionary** |
| Microphone selector | **NAVA AI - Microphone** |
| Selection popup / target marks | **NAVA AI - Choose a target / Target ...** |
| Cursor halo | **NAVA AI Cursor** |
| Smart grid | **NAVA AI - Smart Grid ...** |
| Optional drawing helper | **NAVA AI Accessibility Grid** |
| Launcher | **Start NAVA AI.cmd** |
| Canonical Python entry point | **nava.py** |
| Current-user sign-in shortcut | **NAVA AI.lnk** |
| Custom browser alias | **nava browser** (Chrome) |

The wake vocabulary, standby grammar, compact speech controls, selection/word-target recognizers, grid parser, typed prefix handling, dictionary examples, feedback strings, window-exclusion checks and current manuals were updated together. NAVA AI windows continue to be excluded from targets so the assistant does not attempt to control its own overlays.

## Compatibility and preserved data

The installation folder remains `Gwen doer` to preserve environment paths and settings. `gwen.py` is an invisible compatibility entry point that launches the renamed interface; it does not restore the old wake word. Startup migration renames only this installation's existing shortcut and updates its entry point. It does not enable startup if it was previously disabled.

Voice/microphone preferences, application aliases apart from the assistant's own browser alias, app catalog, browser profiles, grid preferences and dictionary opacity/position/visibility remain intact. Historic checkpoints, saved test transcripts, model files and recovery evidence keep their original bytes/names. These are records, not active branding.

Pretrained speech model names remain **Vosk** and **Whisper** so their loaders and attribution remain correct. NAVA AI is the product name, not a claim that those models were trained by this project. No Qwen inference was added.

The optional UIAccess drawing helper source, build names, manifest, drawing-pipe prefix and future installation labels use Nava/NAVA AI. Its renamed executable was rebuilt locally; this step does not install certificates, grant trust or change Windows security settings.

## Verification

- 206 focused regression checks passed across power, wake routing, dictation, selection, Office, browser/media, grid, dictionary, status and taskbar placement.
- Six synthetic offline SAPI-to-Vosk checks passed: Nava turn on/off, listen, show dictionary, grid and press enter. These are synthesized speech checks, not a guarantee of human accent accuracy.
- Explicit tests reject old wake names and `NavaAI`/`Nava AI` prefixes, and preserve literal dictated text.
- The broad legacy test discovery also reports older failures. Eight failures were reproduced against the source backup taken before this rename (grid/app routing, obsolete planner expectations and prior decoder-setting assertions); a separate native Store test timed out waiting for a real Store window. They are not presented as a clean full-suite pass.

## Changed source file inventory

A pre-rename source backup is retained on the development computer.

<details>
<summary>Source and test files touched by the rename</summary>

- `accessibility.py`
- `agent.py`
- `app_runtime.py`
- `branding.py`
- `browser_control.py`
- `choice_ui.py`
- `command_dictionary.py`
- `command_help_ui.py`
- `command_voice.py`
- `cursor_marker.py`
- `diagnose_grid.py`
- `dialog_voice.py`
- `grid_commands.py`
- `grid_events.py`
- `grid_mouse.py`
- `grid_overlay.py`
- `gwen.py` (compatibility wrapper)
- `Start NAVA AI.cmd`
- `hybrid_speech.py`
- `nava.py`
- `planner.py`
- `punctuation_edit.py`
- `resident_ui.py`
- `selection_recognition.py`
- `setup_command_voice.py`
- `setup_dictation_voice.py`
- `setup_website_directory.py`
- `smart_grid.py`
- `smart_grid_observer.py`
- `speech_context.py`
- `startup.py`
- `status_indicator.py`
- `task_feedback.py`
- `taskbar_status.py`
- `test_active_window_state.py`
- `test_background_voice.py`
- `test_browser_layers.py`
- `test_command_dictionary.py`
- `test_command_routing_boundaries.py`
- `test_dialog_focus.py`
- `test_dialog_voice.py`
- `test_failed_run_repairs.py`
- `test_file_control.py`
- `test_grid_integration.py`
- `test_media_reliability.py`
- `test_named_close.py`
- `test_nava_branding.py`
- `test_popup_grid.py`
- `test_power_controls.py`
- `test_reliability.py`
- `test_selection_mode.py`
- `test_smart_grid.py`
- `test_smart_only.py`
- `test_speech_context.py`
- `test_status_indicator.py`
- `test_status_recovery.py`
- `test_voice_commands.py`
- `test_voice_typing.py`
- `typed_ui.py`
- `uiaccess\NavaOverlay.cs`
- `uiaccess\NavaOverlay.manifest`
- `uiaccess\build.ps1`
- `uiaccess\install.ps1`
- `uiaccess\uninstall.ps1`
- `uiaccess_overlay.py`
- `verify.py`
- `verify_choice_ui.py`
- `verify_dialog_native.py`
- `verify_live_input.py`
- `verify_native_browser_fixture.py`
- `verify_nava_rename.py`
- `verify_offline_commands.py`
- `verify_runtime.py`
- `verify_searches.py`
- `verify_smart_grid_native.py`
- `verify_tab_media_fixture.py`
- `verify_vlm_input.py`
- `verify_voice.py`
- `voice_controls.py`
- `voice_gate.py`
- `vosk_speech.py`
- `window_commands.py`
- `windows_api.py`
- `word_commands.py`
- `word_context.py`

</details>
