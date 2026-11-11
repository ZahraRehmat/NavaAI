# Command-routing repairs — 11 November 2026

These fixes are based on the restored `21eb452` snapshot. The dictionary remains
removed. This document records the defects and verification rather than claiming
perfect speech recognition.

| Defect | Repair |
|---|---|
| Windows Store matched Notepad through similar package/publisher identifiers | Package IDs match exactly, never fuzzily. Installed-app requests cannot use a browser article title as app identity. |
| `click on f h` reached named-control lookup as prose | Speech and direct grid dispatch share visible-label normalization, including optional on/at, spaced letters, NATO names, drag endpoints and sequences. |
| A valid grid code hit the named-app confidence gate first | Normalize first; retain the existing code confidence checks and visible-target checks. |
| Excel parsing bypassed grid handling globally | Excel bypass requires the actual Excel target. Cell suppression remains an Excel-only scanner rule. |
| Spaced grid letters could become keyboard chords | Unmodified letter sequences remain grid targets; explicit modifier chords and special/function keys remain keyboard actions. |
| Compact speech decoder replaced YouTube with new tab because both said open | Generic verbs are not target evidence; different valid actions/opposite modes are preserved. |
| Every obscure website name competed with ordinary commands | Bound acoustic boosting to prominent names/aliases; keep the full 10,000-domain lookup. |
| Short misheard `git` fuzzy-opened a long PowerPoint name | Queries of three characters or fewer require an exact file stem. |
| Voice-review text could overwrite the typed command before Enter | Review text stays in the voice status/log and pending voice review, not the typed entry. |

Verification:

- 182 focused regression tests passed.
- Nine offline synthetic speech cases passed, including click/press/scroll at
  spaced `F H`, Store, YouTube, new tab, grid activation, Excel A2 and paste.
- Live `open store` returned `Opened Microsoft Store.` and the actual Store
  window was confirmed through its package identity.
- Live `open grid` exposed targets; `move to F H` returned `Moved to FH.`
- The laptop microphone selection was not changed. Synthetic speech is not a
  substitute for live microphone/accent testing.

Changes are local; the published Git snapshot has not been overwritten.
