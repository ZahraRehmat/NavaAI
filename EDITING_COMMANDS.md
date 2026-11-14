# Editing and Notepad menus

These commands work with smart grid on or off, including dictation and selection modes.

| Say or type | Result |
| --- | --- |
| undo / control z / Ctrl+Z / undo last action | Ctrl+Z |
| redo / control y | Ctrl+Y |
| erase it / erase last word | Ctrl+Backspace: delete previous word |
| erase letter / delete last character / press backspace | Backspace: delete previous character (or current selection) |
| move cursor up / move cursor down | Move text caret one displayed line |
| move cursor down 3 lines | Send Down three times |
| move caret left two characters | Send Left twice |
| previous line / move to next line | Up / Down; does not insert a new line |
| go to start of line / go to end of line | Home / End |
| next line / new line / press enter | Enter; app decides its effect |

Focus the intended text field first. Commands use the editor's native keyboard behavior; an existing text selection can change the deletion result. Bare `back` remains app navigation (Alt+Left). Existing bare `backspace` / `back space` retain their previous last-word behavior; use `press backspace` for one character. Cursor movements are bounded to 50 steps per command, and plain `move left` remains mouse movement.

Notepad toolbar dropdowns such as Lists, Headings and Table expose Button controls with ExpandCollapse. They are now included in named-dropdown discovery as well as smart grid discovery. A click/open/double-click on an expandable menu/button label expands once through its observed provider instead of toggling the popup twice. Regular leaf buttons keep their normal action, and Office split buttons keep their main-click versus arrow distinction.

Examples: `open Lists dropdown`, `open Headings dropdown`, `open dropdown` to choose a visible dropdown, or say the displayed grid label. Popup entries continue to use the scanner's normal live refresh.

If a Button/MenuItem Expand provider silently does nothing, one click on its observed control is attempted and expansion is checked again. There is no fallback on a SplitButton/ComboBox main action or a leaf button. An unchanged state produces an explicit failure.

Local verification: 104 automated checks passed. The live grid command `open dropdown HI` addressed Notepad Edit by its observed runtime identity and reported Expanded. Persistence of the displayed popup could not be confirmed: the same menu failed to remain open in the computer-use check with Nava stopped. This part requires confirmation in the user session; it is not claimed fully verified. No test document was saved.

## Named words

- `move cursor to word "Karachi"` places the text caret immediately before that word.
- `select word "Karachi"` selects that occurrence only, without copying automatically.
- `erase word "Karachi"` selects and deletes that exact word in the focused editable field. Adjacent spaces and punctuation are preserved.
- Quotes are optional. Multiword phrases also work.
- Repeated occurrences prompt once with the existing voice/click letter chooser. `select word last Karachi` can address a particular occurrence directly.
- Matching ignores case and requires word boundaries. Named-word deletion does not use fuzzy spelling or homophone substitution.
- Commands work with smart grid enabled or disabled and in dictation/selection mode. Say `type ...` to dictate the command literally.
- Selection can use selectable displayed app/page text. Moving an insertion caret and erasing require a focused field that exposes text selection; erase additionally verifies it is editable. Cancellation or stale text/changed focus prevents deletion.

### Named-word speech repair

The command recognizer uses a restricted vocabulary. This reproduced `Select word work` as `select word word` and `Move cursor to work` as `move cursor to word`. Named-word commands now receive a second Vosk pass using its full offline language graph. A recovery is accepted only when it preserves the original action, has a complete target, and passes word-confidence checks. It does not substitute work for word or use a target-specific alias. Incomplete commands ask which word instead of falling through to a generic unsupported-command response.

Offline Windows SAPI checks recovered all six: select/erase/move to work, the shorter move cursor to work, select word garden, and the literal select word word. Decoding took approximately 0.9–1.3 seconds locally. These synthetic checks reproduce the grammar failure; human-microphone accuracy still depends on the recorded speech.

### Follow-up from the Notepad run

The log confirmed native caret movement to work succeeded in 0.28 seconds. Subsequent speech failures included move cursor tool shell, and a recovery veto caused by the preposition to scoring 0.583 even though shell scored 1.0. Recovery detection now accepts to/tool/too only as a signal to re-decode the original audio; it never rewrites these into executable input. Target and action words still require confidence; grammatical to/the/word prefixes do not veto a clear target. A failed named-word decode gets one selection-length-limited offline English pass. Different actions or weak targets remain rejected. Rejected English text and confidence now appear in private speech diagnostics to make future failures traceable. 111 regression checks passed; these checks are not a claim of perfect live microphone recognition.

### Editor-grounded word recognition

Word targets now have a separate, bounded Vosk grammar built from the focused editable field's visible text, in addition to the general-English pass. This vocabulary does not enter the app/website/grid grammar. The asynchronous cache is scoped to HWND, PID, title and bounds; the focused field's runtime identity is carried with word actions and rechecked before selection, caret placement or deletion. Existing clearly heard targets present in the field bypass the extra pass. Short `select work` is accepted as a word command only in an observed editable context with grid off; grid letter commands retain priority.

A dedicated short word-command prompt replaces the unrelated range-selection prompt in the English fallback. When the primary recognizer clearly heard the action, a weak second decoding of that same action does not veto a confident target. A `move closer to ...` fallback can recover the already-confirmed move-cursor action; no target word is rewritten. Low-confidence trailing decoder sentences are removed only when the first complete target exists in current editor vocabulary. Target confidence and original action consistency remain required.

Read-only inspection of the user's open Notepad verified exact text-range mapping for work (1), testing (1), shall (3), and required (3), without selecting, copying, erasing or saving anything. Five synthetic offline speech checks with editor vocabulary passed for those words and for short select syntax. 123 regression checks passed. Human microphone accuracy must be verified with actual spoken commands; synthetic speech is not an accent/noise guarantee.

Live microphone verification after restart succeeded in the actual open Notepad: select word work (0.27s execution), move cursor to testing (0.09s), select word testing (0.11s). The last utterance's primary decoder heard select word js bing; the editor-scoped decoder recovered select word testing and its observed field identity was retained. These are actual session results, separate from synthetic speech checks. They do not guarantee every accent/utterance will be recognized.

### Word edges and selected-text deletion

`move cursor to end of word work` / `move cursor after word work` place a collapsed caret immediately after the chosen occurrence; `move cursor to start of word work` / `move cursor before word work` place it before. Repeated occurrences still use the chooser. `move cursor forward` and `move cursor backward` send Right/Left; add `a word` for Ctrl+Right/Ctrl+Left. These variants have separate recognition grammar so an end request cannot silently turn into a start request.

`erase it` and the existing last-word Backspace aliases now send ordinary Backspace when the editor has a nonempty selection, preserving Ctrl+Backspace when there is no selection. Explicit `erase word work` continues to resolve and select a named occurrence, verify editability and selection identity, then delete that occurrence only.

Live scratch-tab testing found a Windows/UIA focus synchronization race on fast text commands. FocusedText now waits up to 0.7 seconds for the requested foreground app's text provider, refusing a real foreground-app change. This fixed the observed failure in the scratch end-of-word test. Actual Notepad named deletion changed `Nava scratch alpha beta omega` to `Nava scratch alpha  omega`; end-of-alpha placement was verified by reading the exact text before the collapsed selection (`Nava scratch alpha`). No user document was saved or used for deletion testing.

Selection-aware erase-it was also verified in the scratch tab: selected alpha was deleted with ordinary Backspace, leaving `Nava scratch   omega`. The disposable tab was emptied and closed afterward. 125 automated checks passed.
