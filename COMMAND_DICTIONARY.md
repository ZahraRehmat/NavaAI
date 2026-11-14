# Adaptive command dictionary

Gwen now shows a transparent black-and-purple command panel without taking keyboard focus or intercepting mouse clicks. Entries use **command - short description**. Names such as Alex, Budget and example are samples; replace them with your own.

## Commands

| Say or type | Result |
| --- | --- |
| show commands / show dictionary / open dictionary | Show the contextual overlay |
| hide commands / hide dictionary / commands off | Hide the overlay and full manual |
| commands on | Restore the overlay |
| next commands page / previous commands page | Page through contextual commands |
| commands more transparent / commands less transparent | Adjust opacity |
| open full dictionary / show full dictionary | Open the searchable master manual |
| search dictionary for font | Search the master manual using your own keywords |
| dictionary scroll down / dictionary scroll up | Scroll the master manual |
| close full dictionary | Close the manual and return to the overlay |

The overlay is visible by default. Visibility and opacity persist separately in `command_help_config.json`. Hiding help does not stop Gwen, voice typing, selection or the grid. Help requests also work in standby; opening help does not activate the assistant. In standby, the overlay shrinks to wake-up and help commands. Explicit microphone off still requires F9 to restore voice input.

## What adapts

- The foreground app is tracked through the existing window context. Own Gwen windows are excluded so help does not replace the app being controlled.
- Notepad, Word, Excel, PowerPoint, Explorer/Desktop, WhatsApp, Store and Task Manager receive their relevant command families.
- A YouTube browser title adds playback, seeking and Skip ad commands to Chrome/Edge tab and navigation commands.
- The footer changes with dictation, selection and smart-grid state. Grid-on pages add labelled mouse instructions; grid-off help explains how to enable it.
- Extra contextual entries have pages rather than covering the entire screen. The master manual contains all catalogued command examples, nested by app and purpose, with keyword search and an app filter.
- Adaptation uses existing title/class and mode information. It does not claim to inspect every visual button or grant support to an unsupported app; use the smart grid for controls without a direct command.

## Isolation from recognition and execution

The manual is read-only data in `command_dictionary.py`. Its full entries, descriptions and sample names are **not** added to speech grammar. Only the small set of exact help-control phrases is added. `type show commands` stays literal. Ordinary action parsers and grid-label matching keep their existing rules.

The overlay is a layered, click-through, no-activate tool window, visible to remote screen capture. The full manual accepts focus only when explicitly opened. While it is foreground, voice searches/scrolling/closing act on the manual; unrelated dictated text is not sent to the editor behind it. Closing the manual returns normal application control.

## Verification

The catalog has 240 examples. Automated checks cover context filtering, Office example parsing, literal dictation, standby help and rejection of prose-to-help guessing. Installed UI checks cover Notepad help, master search, hide/show and standby. Synthetic offline speech tests cover four help commands; human accent accuracy is not guaranteed by those tests.
