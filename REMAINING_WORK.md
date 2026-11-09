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

## 3 · Rename Gwen to Nava / Nava AI

- [ ] **The activation keyword shall be Nava or Nava AI instead of Gwen.**
- [ ] Update recognition vocabulary, wake phrases, UI text, launchers, startup entries, documentation and tests together.
- [ ] Decide how long old Gwen phrases remain as compatibility aliases.

**Current position:** repository/product branding says NavaAI; the running application still uses Gwen.

## 4 · Installer and model cleanup

- [ ] **Create an installer; first remove the unused AI planner model from the distributable.**
- [ ] Package only required dependencies and the intended offline speech/punctuation models.
- [ ] Add first-run microphone setup, dependency/model checks, startup choice, update and uninstall flows.
- [ ] Measure installation size, startup time and performance on lower-spec PCs.

**Current position:** Qwen weights and OpenVINO dependencies are excluded from this published snapshot, and runtime dispatch does not call Qwen. The original development folder still retains historical files. A finished installer and clean-environment certification remain to be done. Offline speech and punctuation models are still required for their features.

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
