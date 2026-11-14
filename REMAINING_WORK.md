# Remaining work · NavaAI

> **Next milestone:** a clearer, more forgiving hands-free experience that is easy to install and use across everyday Windows applications.

This is a roadmap, not a claim that these items are complete.

## 1 · Clear feedback and graceful recovery

- [ ] **Give graceful errors instead of stopping or ignoring commands.** Explain what failed in plain language and suggest a useful retry or next step.
- [ ] **Show an appropriate loading/status indicator** while working, listening, dictating, selecting, waiting for confirmation or recovering from an error.
- [ ] Keep feedback passive so it does not steal focus, dismiss dropdowns or interrupt typing.

**Current position:** status badges and completion cues exist, but consistent feedback and recovery across all command paths still need improvement.

## 2 · Common everyday keywords

- [ ] **Common keywords are not finished yet.** Accept the words and phrases people normally use in daily life.
- [ ] Expand natural synonyms and incomplete-but-clear wording without requiring exact command syntax.
- [ ] Ask a short clarification when several meanings are plausible; avoid silently guessing a different action.

**Current position:** there are aliases and normalization rules already, but this does not amount to complete everyday-language understanding.

## 3 · NAVA AI branding — completed

- [x] Product, windows, overlays, launchers and current manuals show **NAVA AI**.
- [x] The command wake name is **Nava only**. `NavaAI` and the old wake name are not command aliases.
- [x] Recognition grammar, standby activation, power, grid, selection and help use Nava.
- [x] Existing installation settings are preserved; old entry-point filenames remain compatibility shims.

See [NAVA_RENAME.md](NAVA_RENAME.md) for the exact changed commands and verification.

## 4 · Installer preview delivered; wider certification remains

- [x] Create the offline installer and native EXE launcher; exclude the unused Qwen planner/weights and OpenVINO.
- [x] Package only the active dependency closure and used speech/OCR/punctuation assets.
- [x] Initialize local app discovery and known file locations; include startup choice and dependency checks.
- [x] Verify fresh install, upgrade and uninstall on Windows 11, including preference/download preservation.
- [ ] Run real Windows 10 acceptance tests, especially managed Playwright browser controls.
- [ ] Add publisher signing and complete trusted UIAccess deployment where required.
- [ ] Improve first-run microphone guidance and benchmark lower-spec PCs/human accents.

**Current position:** the unsigned development installer preview is available from the [installer guide](installer/README.md). It is approximately 830 MiB and contains no orphan Qwen/OpenVINO/Whisper Tiny assets. Offline recognition assets remain because current features use them. Windows 10 and broader clean-environment certification are still pending; see [validation](installer/BUILD_VALIDATION.json).

## 5 · Two-app multitasking

- [ ] **Multitasking with two apps working at once is remaining.**
- [ ] Make the intended target explicit when apps are side by side; preserve the correct typing/selection target across focus changes.
- [ ] Test Notepad + browser and Office + browser workflows, including copy/paste between windows.

**Current position:** switching apps is supported; independent simultaneous targeting of two apps is not complete.

## 6 · Desktop markers

- [ ] **Add/improve desktop markers for files, folders and app shortcuts, including extensions/type information.**
- [ ] Ensure exposed desktop items are discovered consistently and not lost behind shell/window changes.
- [ ] Make it clear which item will open, while keeping labels legible and avoiding unnecessary visual clutter.

**Current position:** the scanner already attempts exposed desktop icons, but reliable coverage and useful type/extension markers remain unfinished. Excel cells intentionally retain native cell addresses rather than added grid labels.

---

**Suggested order:** graceful feedback → everyday wording → Nava rename → desktop coverage and two-app targeting → clean installer and wider hardware testing.
