# YouTube controls in Chrome and Edge

| Say or type | Action |
| --- | --- |
| pause video / pause YouTube | Pause; leave an already paused video paused |
| resume video / play YouTube / unpause video | Resume; leave an already playing video playing |
| forward five seconds / fast forward ten seconds | Seek +5 / +10 seconds |
| rewind five seconds / rewind ten seconds | Seek -5 / -10 seconds |
| skip ad / skip this ad | Click the available YouTube Skip button once |
| play next video | Request YouTube next video |
| play previous video | Request YouTube previous video; normally requires a playlist |

Use the intended browser window. Grid can stay enabled. Media commands route before generic input and grid labels; explicit `type ...` stays literal typing.

## Implementation

`media_commands.py` parses explicit media wording. `system_media.py` first matches a Windows media session by browser source and video title. Chrome and Edge sessions are distinct, even for the same video. Pause/resume are explicit state operations, not toggle keys. Seeking changes the playback position and verifies the reported timeline. Stop, foreground and title guards prevent acting after the target changes. Duplicate matching sessions are left unresolved rather than guessed.

The minimal WinRT packages are pinned in both requirements files. Missing or unsupported media-session capabilities fall back to the observed UIA player in `native_media.py`. That fallback refreshes replaced player controls after focus; next/previous retain YouTube player shortcuts. A declined attempted media operation is reported without sending a second toggle or seek.

`browser_control.py` retains HTML media control for the assistant-owned browser session. No Qwen model is involved.

## Actual website verification, 12 November 2026

The earlier local YouTube-origin fixture passed but failed to reproduce the real site's disappearing/replaced player buttons. It was insufficient evidence for live compatibility. Actual user logs showed correctly recognized commands failing with player-changed / no exposed Play-Pause control errors.

The repair was tested through the real NAVA AI command panel on the actual youtube.com video W9_0OsajRN8, in ordinary Chrome and Edge windows. Independent read-only Windows media-session queries checked outcomes.

- Chrome resume: 0.34 seconds; pause with smart grid enabled: 0.48 seconds.
- Chrome paused timeline: 739.480662 -> 744.480662 (+5) -> 739.480662 (-5) -> 749.480662 (+10) -> 739.480662 (-10).
- Edge live voice pause: 0.22 seconds, confirmed paused.
- Edge +5: 708.376249 -> 713.376249 -> 708.376249 (+5 / -5); forward took 0.42 seconds. Chrome stayed at 739.480662.
- 139 regression tests passed across media, browser/tab routing, grid, voice, typing, selection, Word and Excel. Dependency consistency check passed.

Next/previous have regression coverage but were not reverified against a live playlist in this run. Live streams, advertisements, unavailable playlist controls and ambiguous sessions may restrict actions; errors must describe the failure rather than claim success.

References: [Windows media sessions](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssession), [YouTube shortcuts](https://support.google.com/youtube/answer/7631406).

## Skip ads

`skip ad`, `skip this ad`, `skip the ad` and `skip ads` work through the media router, including grid mode and active browser dictation/selection. Native controls use a visible, enabled, exactly named Skip / Skip ad / Skip ads accessibility button with a hit test before clicking. The managed browser uses its accessible button role. No timer is bypassed: unavailable or unskippable ads return an explanation. Ambiguous buttons are refused. After one click, the button must disappear; a persistent button returns an unconfirmed result without retrying.

Live Skip-ad verification: on 12 November 2026, the actual Edge YouTube page exposed a skippable ad. `skip this ad` executed through NAVA AI in 1.20 seconds; its Skip button disappeared and a subsequent accessibility snapshot exposed only Skip navigation, not an ad Skip button. This was the actual website, not a local fixture.

## 14 November repair: unread notifications and opening a new tab

The failed live tab title was `(1) Do Souvenir Plots Make You a Scottish LORD? - YouTube - Google Chrome`, while Windows media metadata reported `Do Souvenir Plots Make You a Scottish LORD?`. The original exact comparison included the notification count and rejected the correct session. This sent recognized commands into the hidden-button fallback.

Media matching now considers both the full video title and a version with only YouTube's leading numeric notification count removed. It still requires the requested browser source and exactly one matching session. Tests cover duplicate sessions, other browser sources, unrelated video titles and genuine titles beginning with a number. No substring or fuzzy video-title selection is used.

`open you tube on new tab` and `open youtube in a new tab` now resolve the website and create a new tab, before the generic existing-tab-name parser. Existing user tabs are retained.

Actual-site resume and pause on the previously failing video, with smart grid enabled, completed in 0.28 and 0.19 seconds respectively. Windows independently confirmed the playback state. 144 regression tests passed.

The exact failed phrase `open you tube on new tab` was also run through the real NAVA AI panel with grid on: it opened youtube.com in a new Chrome tab in 1.98 seconds. The test tab was closed afterwards. Live +5/-5 seeking returned the paused video from 348.584038 to 353.584038 and back to 348.584038 seconds.
