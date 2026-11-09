# Smart grid only

The uniform rows-and-columns grid has been removed. All grid activation phrases open the adaptive smart grid.

**On:** Gwen grid, open grid, show grid, start grid, turn on grid, turn grid on, grid on.

**Off:** close grid, hide grid, stop grid, exit grid, turn off grid, turn grid off, grid off.

Leading Gwen/please and common typed mistakes such as griud on and turhn of grid are accepted. Older full-grid activation phrases are compatibility aliases for smart grid; they never create uniform cells. Row/column density and grid zoom commands are removed.

Type or say `Gwen grid` or `Gwen smart grid` in the resident chat. Accessible interactive controls across visible windows, taskbars, shell menus and exposed desktop icons receive A–Z, AA–AZ, etc. labels. Taskbar names remain available for spoken/typed matching without being printed over the icons. This is a direct manual mouse mode; Qwen is not loaded for grid commands. See [OFFLINE_VOICE.md](OFFLINE_VOICE.md) for voice controls and phonetic label spelling.


Smart labels use only the speech-friendly alphabet **A F H I L M O Q R U W B**. After those singles, the system reuses the same alphabet in pairs (**AA, AF, AH, ...**) and longer labels. It never introduces C/D/E/G/P/T/V/Z as competing mouse labels on dense screens. This is an English letter-name heuristic; NATO spelling remains available. Actual Excel column names are unchanged.

Refreshes preserve a control's label. Removed labels are not reassigned to different controls during the same activation, so earlier speech cannot hit a replacement target. Newly appearing controls advance to longer combinations from the same restricted alphabet; turning the grid off and on starts a fresh allocation.

| Command | Effect |
|---|---|
| `A` / `FH` | Move to the displayed target and single-click it |
| `move to A` / `move to FH` | Move only, without clicking |
| `click B`, `double click B`, `right click B` | Move and click that control |
| `press B`, `select B`, `open B` | Single click, single click, double click |
| `press Chrome`, `select File Explorer` | Match and click the named taskbar app |
| `click Windows button`, `press win button`, `select startup button` | Click the taskbar Start button |
| `scroll down on C`, `scroll up 3 on C` | Send wheel input at C |
| `scroll down from FH`, `scroll up FH`, `from FH scroll down` | Move to FH and scroll there without clicking |
| `hold A`, `B`, `release` | Hold, move, release |
| `drag A to B` | Smooth drag between labeled controls |
| `hold A and move right 100 and release` | Continuous gesture without returning to chat between steps |
| `move left 1`, `move down 20` | Fine pixel adjustments |
| `refresh grid` | Re-observe immediately |
| `open grid`, `turn on grid`, `grid on` | Start smart grid |
| `close grid`, `turn off grid`, `grid off` | Stop smart grid |
| `exit grid` or **F8** | Hide labels, release held buttons, restore agent commands |

Bare labels click in smart-grid mode. While a mouse button is already held, a bare label moves the held pointer instead, preserving drag control; `release` ends the hold. Outside grid mode, bare labels are not intercepted.

Typing and keyboard commands coexist with both grids: focus the input with a label, then say `type hello`, `write hello`, `press enter`, `press tab`, `select all`, or `paste`. The grid stays on and these commands use the existing keyboard executor. `press F` still clicks the displayed F target. `back`/`go back`, `forward`/`go forward`, `go up`, and `go home` send Alt+Left, Alt+Right, Alt+Up, and Alt+Home to the current app; Explorer determines their navigation behavior.

You can also say `type` alone or `start dictation`, wait for the beep, then speak text in separate phrases. The badge says Dictating. Phrases use the unrestricted offline speech decoder and are typed literally (including phrases that sound like commands). Say `stop dictation` or `finish typing` to return to commands; bare `stop` also ends dictation and stops the task. Dictation mode does not persist across restarts. A phrase heard while another typing action is busy is reviewed rather than queued for later input.

Grid mode no longer blocks ordinary agent commands. `open <name>` first uses an observed smart target when available; if no such target exists, it falls through to the app/file/folder directory. Explicit grid labels retain their mouse behavior. Folder matching treats number words and digits equivalently (`gwen three` / `gwen 3`) and offers a choice for nearby folder names rather than silently guessing. Desktop icon hosts are always scanned; covered icons remain removed by point hit-testing, and DWM-cloaked windows are ignored.

App commands also work with grids on: `close Word`, `quit Chrome`, `stop Notepad`, and `close this window` request a normal window close after one confirmation. Names use the running-window matcher, including aliases and approximate spelling. Multiple matching windows use the current matching window or a choice card. Save/discard prompts remain for the user. `force close Notepad` or `terminate Notepad` explicitly requests process termination, warns about unsaved work, and requires one confirmation. This stops only the selected process (possibly several windows belonging to it), not an arbitrary process tree. Protected Windows processes and the desktop shell cannot be force-stopped. Bare `stop` continues to stop Gwen's current task and release the mouse; it does not kill the foreground app.

Opening, closing and window switching share `apps.json` and `aliases.json` through `Catalog.identities`. Spacing/punctuation do not distinguish product identities: `Chat GPT`, `Chat G P T`, `ChatGPT`, `Whats App`, and `WhatsApp` work. Catalog entries provide executable names and packaged app IDs for matching windows whose titles only show documents. Known names/aliases ending in “app” are preserved. Different matching windows still require a choice; speech that did not actually recognize the app name is not silently rewritten to one.

`minimize this app`, `minimize this screen`, `maximize this app`, `maximize this screen`, `restore this window`, and `close this screen` operate on the selected/current active app window with grids on or off. “Screen” here means that app's window, not the desktop or monitor. Minimize/maximize/restore use direct asynchronous Windows requests and verify the resulting state; no visual model or title-bar click is needed. A blocked modal dialog must be handled first. Close retains one confirmation and the app's save prompts. After minimizing, the next “this app” command targets whichever app is now active.

Named versions (`minimize Chat GPT`, `maximize Word`, `restore Chrome`) use the shared running-app directory and ambiguity chooser with either grid mode on or off. Startup captures the external app before Tk is created and restores its focus only if Gwen's own initialization took it; switching to another application during startup is respected. Voice decision logs now include the target captured at utterance onset for diagnosis.

Explorer AppBar containers, tab descendants, and Start's SemanticZoom container are traversed. Native popup windows are merged with UIA desktop roots rather than discarded when UIA omits them. Known transparent shell flyout hosts remain eligible. Disabled navigation buttons are excluded until Windows enables them. The grid and cursor annotations show without activation, preserving the edit caret and open menus.

For Explorer items with an exposed filename child, clicks target that text instead of the row's centre, checkbox, or inline action area. `open A` double-clicks that filename; bare `A` and `click A` intentionally single-click for selection. If an app exposes no interactive accessibility element, a smart-grid target cannot be guaranteed; use ordinary agent commands or precise mouse movement for unsupported controls.

Scroll locations accept `from`, `on`, `at`, `in`, `over`, or no preposition. `scroll down 3 steps from FH`, `scroll down at FH 3 times`, and `scroll up a little on FH` also work. `formfg` is accepted as the common joined typo for `from FH`. Named targets can use phrases such as `scroll down from Search chats`; confidence matching and target revalidation apply. The wheel is sent at the target; the application determines which pane under that point scrolls.

## Refresh and target identity

A Windows WinEvent listener requests refreshes for window, menu, structure, location, name and value changes. The watcher checks notifications at roughly 120 ms intervals, with a roughly 350 ms fallback poll. Scan time is additional. Unchanged window trees are reused for up to two seconds; change events invalidate their caches immediately. Addressed windows are refreshed before commands, and `refresh grid` forces every visible root to be scanned. Bulk UI Automation cache requests collect control properties in one provider call instead of issuing multiple remote calls for every property. This is best-effort low-latency refreshing, not a hard real-time guarantee: initial scans, complex apps, unresponsive providers and eventless custom UIs can take longer.

The scanner enumerates visible windows in their stacking order, includes taskbars independently of maximized app bounds, and subtracts covered regions to avoid scanning completely hidden windows. Click-through cursor/annotation overlays are ignored. Native point hit-testing filters covered controls; taskbar controls remain mapped beneath Gwen's own chat, which withdraws before sending input. Start menus, notification areas, owned dialogs and other exposed shell windows are included as they appear. Labels are preserved by control identity, not reassigned according to screen order; removed labels are not given to unrelated controls during the activation. Reactivating smart grid starts a fresh alphabet.

Taskbar badges use compact letters only in a collision-free rail outside the bar, with thin pointers to their controls. Long app/status/privacy captions are not painted over the clock and tray icons, and overlapping taskbar target rectangles are omitted. Names remain available for commands. Dense sets wrap to another rail; top/side taskbars use their actual bar orientation. Ordinary app targets keep their normal bounds/labels.

Before using a label, Gwen scans again and resolves its current bounds. Each step in a click chain is re-observed; all referenced labels must exist before the chain starts. Removed targets and targets covered by another app are rejected. Automatic refresh pauses while Gwen holds a button so a drag's labels do not change halfway through. F8 can release the mouse while a scan is running.

The high-contrast overlay is click-through and does not capture keyboard focus. Crowded label badges are repositioned while outlines stay attached to their controls. Overlay windows are reused instead of recreated on every refresh. Accessibility scanning uses a persistent, hidden worker process with one COM apartment, isolated from Office and the agent's existing accessibility connection. Initial results are published progressively, beginning with the taskbar. A failed scan clears obsolete targets; a later successful scan recovers automatically.

The worker has a six-second overall response deadline and a two-second per-window deadline. The Windows 8+ accessibility client also has bounded connection/transaction settings where supported. If a provider stalls, the worker is restarted, freshly collected targets from responsive windows are retained, and the stalled window is skipped for 15 seconds before retrying. No old cached targets from that skipped window are kept clickable. Timeout warnings are readable even when the original exception has no message. A targeted request for an unavailable label stops without input; use ordinary agent commands or precise mouse movement for unsupported controls.

## Coverage and limits

Windows UI Automation supplies controls and labels directly: buttons, edit fields, links, menus, tree/list items, tabs, sliders, scrollbars, document areas and custom controls exposing invoke, scroll or value patterns. This includes browser page controls when the browser exposes them to accessibility. It does not infer invisible semantics from arbitrary images, videos, game canvases or apps that withhold accessibility data. The former uniform full-grid system has been removed; use the agent or direct pointer movement for those pixels. DOM-based browser actions and all existing agent modules remain available after `exit grid`.

Application windows use direct HWND-to-UIA resolution and cached immediate-child queries, traversing only bounded branches to depth 18, at most 2,500 visited descendants and 600 targets per window. Buttons and chat/list/data items are atomic targets; their message-history descendants are not enumerated. Disabled or empty WebView host wrappers can still be traversed to reach enabled descendants, while disabled controls themselves are not targets. Compact shell trees retain bulk collection. A 1.4-second branch traversal budget and worker deadlines bound scans. Large virtualized lists expose their currently instantiated items; scrolling discovers more. Normal Windows integrity and secure-desktop restrictions still apply. Actual live verification used one physical display; multiple-monitor geometry is unit tested.

Names use confidence-based matching and common aliases. `win`, `windows`, `windows button`, `win button`, `startup button`, `windows logo` and `start menu` mean Start. A direct taskbar app match is preferred over unrelated text mentioning that app. Ambiguous or low-confidence names use the existing target-choice popup. The selected control identity is then revalidated before clicking. The verb aliases apply inside grid modes; existing agent keyboard commands outside grid mode keep their behavior.

## Verification

`test_smart_grid.py` covers stable identities, moved/removed targets, automatic refresh without commands, failed scans and recovery, mode switching, command-chain validation, emergency release and stopping an in-flight refresh. `verify_smart_grid_native.py` supplies an isolated native test window whose button moves another control and adds a new button. The live typed-chat check successfully clicked the initial control, retained the moved target's B label, discovered the new control and clicked both at their new positions. Recorded native events are in `diagnostics/smart-grid-native-events.json`.

`diagnostics/smart-grid-shell-verification.json` records whole-screen discovery and alias resolution: 22 taskbar targets were found; Windows-button aliases resolve to Start and Chrome resolves to the taskbar app rather than status text. The live typed command `press windows button` opened Start. Sample full scans took roughly one second on this machine, and unchanged cached scans took 0–16 ms (timer resolution applies); these are observations, not guaranteed response times. The 168-test regression suite includes verb aliases, name ambiguity choices, mixed name/letter chains and window occlusion geometry.

Activation crash regression: the session trace showed a WhatsApp accessibility timeout followed by `str(exc).splitlines()[0]` failing on an empty exception message. Error formatting now falls back to the exception type. Fault-injection tests exercise an empty `queue.Empty`, partial results followed by a stall, and a successful response after timeout. The updated 171-test suite passes. A live `gwen grid` activation with the same stalled WhatsApp window succeeded with 160 targets and a timeout warning; taskbar results appeared progressively before the stalled scan was stopped.

WhatsApp coverage repair: full application-tree collection and window-wrapper resolution were replaced with direct HWND access and bounded cached child traversal. The live WhatsApp window exposed 31 visible targets (21 buttons, an edit field, document area, three tabs and five chat-list items) without a timeout. The resident grid displayed its boxes; `click AA` successfully focused the observed search field without typing or sending anything. The 175-test regression suite includes disabled WebView hosts, atomic chat rows, document descendants and traversal depth limits. Counts vary with the visible layout; this is not a guarantee that every custom control exposes accessibility data.


## Split buttons and dropdown arrows

Word ribbon controls such as Paste, Underline, Font Color, Bullets, Shading and Borders expose a main action plus a separate arrow. Both remain mapped. Arrow children formerly named only “More Options” now inherit a useful display name such as **Font Color dropdown**, while retaining their real UIA identity and bounds.

- **Open dropdown A**, **expand A**, **open A**, or **double click A** opens a control marked as expandable using Windows ExpandCollapse, rather than double-clicking its default action.
- **Open Font Color dropdown**, **click the Font Color drop down arrow**, or **expand Font Color** opens the named menu with grid on or off.
- A plain grid label/click on the main split-button target retains its main action. A plain click on the separate arrow label hits the observed arrow.

Already-expanded menus remain open; opening them again is a no-op. There is no guessed right-edge/bottom-edge click. Where ExpandCollapse is unavailable, only an observed, named arrow child may be used. A provider that refuses expansion reports the error without invoking the main formatting action. Grid semantic expansion runs in a separate process with a four-second deadline and cancellation. The target's runtime ID, PID and window are checked before expanding. Menu targets continue to refresh through the existing shell/menu observer.

The native named-control scanner now includes SplitButton and traverses up to depth 18 to reach nested ribbon controls. It opens split buttons/comboboxes/expandable menu items semantically. Plain buttons and filling an editable control retain their existing action paths.


## Popup providers and Windows shell drawing

The popup scan is prioritized ahead of the underlying app. Expanded ComboBox descendants are traversed. If a known popup HWND resolves to an empty/stale UIA root (observed in Word's Font gallery), bounded semantic hit tests find a real UIA element, then follow its ancestors to the popup's actual provider. Oversized virtualized list hosts are crossed without adopting the underlying app. The real accessibility subtree supplies the names and rectangles; this does not restore a uniform grid or guess click coordinates. HWND/PID binding and visible-point filtering still apply.

Live read-only checks found **19 visible Font popup controls**, **40 Start targets**, and **10 hidden-tray popup targets**. The ordinary overlay now reasserts topmost stacking on redraw without activation. This repairs ordinary app/tray popups that opened above an existing grid window.

Start was observed in Windows display band 6, above the ordinary drawing layer. Detecting its targets does not guarantee that a normal Tk window can paint above it. The optional drawing-only UIAccess helper and administrator installer are in [uiaccess](uiaccess/README.md). Installation requires explicit approval because it adds local signing-certificate trust and places the signed helper in Program Files. Until installed, ordinary app/tray drawing works with the existing Tk overlay; Start's shell layer can still cover its labels. No UAC policy or secure-desktop setting is weakened.

The helper consumes the existing canvas's drawing commands, preserving label assignment, target bounds and taskbar rail layout. Its named pipe is restricted to the current Windows user. Gwen requires a real UIAccess-token handshake before hiding the ordinary overlay, checks the installed binary against its installation hash, and falls back to Tk on communication failure. It contains no input-injection or application-control protocol. `test_popup_grid.py` checks virtual-provider recovery, process boundaries, missing/modified helper fallback, drawing-only serialization, handshake rejection and non-activating native popup stacking. The unsigned diagnostic renderer compiled and painted a standalone test bitmap; installed UIAccess behavior must be verified after user-approved installation.


### Dropdown field labels

A label on the editable child of a ComboBox can now be opened as a dropdown: `open dropdown A` resolves the observed child, finds its owning ComboBox/SplitButton through a bounded parent chain, and expands that owner. `open A` also works on grid targets marked with a dropdown owner. Plain clicks still place the caret/apply the main action. Owner lookup cannot wander through an unrelated ribbon Group. Generic arrow children of ComboBox controls now receive contextual names, as split-button arrows already do.

Bare `open dropdown` responds immediately with a request for the control name or grid label; it does not rank the word “dropdown” against every control or start a planner. `font selection`, `font selector`, `font selecting`, `font list`, `font names` and `font family` identify the Font dropdown. Confidence checks still cover the meaningful target words; optional selector/dropdown wording does not hide a clearly recognized Font target. Weak distinct target words such as `color` still require review.

Manual-grid logs now include the resolved target label/name/type/bounds/runtime key and dropdown owner on success and failure, so edit-field versus arrow targeting can be diagnosed directly.


For an explicit named dropdown request, a unique exact ComboBox (then SplitButton) is preferred over duplicate captions from menu entries. Two truly distinct exact combo boxes still require a choice. A live Word test confirmed `open font dropdown` expanded the list; inspection of the earlier WQ position identified an Edit named Font whose parent is the Font ComboBox, validating the owning-control path.


### Specific font dropdown names in smart grid

The Font ComboBox is named **Font selection dropdown**; the Font Size ComboBox is named **Font size dropdown**. Say either full name alone, or say `open font selection dropdown` / `open font size dropdown`, with grid on. Each phrase resolves directly to its own observed ComboBox, rather than fuzzy-matching the font field, a Font menu entry, or the other dropdown. Letter badges remain available. Real UIA names/runtime identities are retained separately for action verification. Separate arrow children have names such as Font selection dropdown arrow. Bare names and the same open commands also work outside grid mode through the existing native dropdown path.


Browser tab commands bypass the grid: **select tab two**, **switch to next tab**, **close current tab**, **close tab two**, **close YouTube tab**, and **new tab** use browser controls. Clicking/opening a browser TabItem grid label selects the actual observed tab through accessibility instead of double-clicking its pixels. **Close AF** (or **close tab AF**) closes the browser tab bearing AF after its selection is confirmed. Stop, stale runtime IDs, changed tabs and unsaved-work prompts remain guarded.
