# Selection recognition and latency — 11 November 2026

The investigated runs spent about 2.6–3.5 seconds in Whisper recognition and only
0.5–0.9 seconds in the failed native selection attempt. Recognized endpoints
included `required Head` and `see Thank you`, with very low confidence on the added
words. Average sentence confidence had allowed some of these through.

Repairs:

- Clear Vosk ranges whose two endpoints occur in current-app vocabulary use a
  fast path; uncertain/new endpoints still use the offline English decoder.
- Selection-mode vocabulary includes up to 100 words from the active app. Cached
  dictation from another app is no longer substituted for that vocabulary.
- The selection fallback uses one beam and at most 48 new tokens. Dictation's
  separate settings and literal payload handling are unchanged.
- An unsupported low-confidence suffix can be removed only when the remaining
  endpoints are supported by the current app's vocabulary and the retained words
  are clear. A literal endpoint already in the hints is not shortened.
- Low-confidence endpoint words are reviewed before a native selection is attempted.
- Close selection, selection off, turn off selection and stop selecting finish
  selection mode without becoming app-close requests.

Repeated-word choices, exact native range verification and clipboard-on-success
behavior remain intact. A read-only check verified the scrolling→required native
range in the existing Notepad document without selecting or changing the clipboard.

Synthetic fast-path samples decoded in about 0.30–0.33 seconds after warm-up (the
first took 0.88 seconds). These figures exclude utterance-ending silence, actual
selection/choices and human microphone variability. No microphone setting changed.
