# NAVA AI 1.0.1

[Download the complete Windows installer](https://github.com/ZahraRehmat/NavaAI/releases/download/v1.0.1/NAVA-AI-Setup-1.0.1-win-x64.exe)

This release publishes the current source application, runtime configuration, command dictionaries, model configuration, packaging sources and the rebuilt offline installer.

## Corrections

- Model and library directories are now installed independently of root preference exclusions, ensuring nested `config.json` files are included.
- Installer self-testing now exercises actual Whisper generation and word timestamps, catching decoder configuration failures that weight-loading checks missed.
- Named-word cursor commands include before/after vocabulary and words from the active editor. Both “move cursor after file” and “move cursor after word file” are supported, with equivalent before forms.
- The source launch shortcut continues to use `.venv/Scripts/pythonw.exe nava.py`; the installed launcher uses its isolated runtime.

## Local verification

- 78 source regression tests passed.
- Fresh installation completed with exit code 0.
- All 6,099 installed payload files matched their build hashes.
- All 19 dependency imports and installed speech generation, punctuation, OCR, Tk and browser smoke checks passed.
- The development PC was upgraded to 1.0.1 and its runtime files matched the build; user preference differences were preserved.

Installer size: 870,606,803 bytes (830 MiB).

SHA-256: `6c3fe3d73bda55b242bd175e4166115358533c02c066298a22b92053808fd078`

The installer is unsigned. Windows may show a SmartScreen warning. Windows 10 acceptance on a separate Windows 10 machine and live speech accuracy are not established by these packaging checks. Office actions require desktop Office applications installed on the receiving PC.

Only active speech, punctuation and OCR assets are included. Qwen, OpenVINO and unused model folders are excluded.
