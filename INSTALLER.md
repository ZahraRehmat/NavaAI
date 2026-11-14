# NAVA AI — standalone Windows installer

The approved flat violet N artwork is used for the application EXE, installer, Start menu and desktop shortcuts. The setup payload contains the existing direct-control application plus a private, isolated Python runtime. Users launch **NAVA AI.exe**; no Python, pip, CMD launcher or model downloads are required on the receiving PC.

## What installation prepares

- Installs the runtime, the active Python dependency closure, app-local Microsoft VC runtime DLLs, Tcl/Tk, matching Chromium and offline feature assets.
- Discovers the receiving PC's Start apps, Desktop/Start Menu shortcuts and App Paths; writes a fresh app catalog. This development PC's catalog is excluded.
- Resolves the receiving user's Desktop, Documents, Downloads and other known file locations. It uses existing file matching on demand rather than copying or pre-indexing personal files.
- Includes the website directory, aliases, Office control catalogs, dictionary, grid configuration and existing command processors.
- Creates branded Start menu/desktop shortcuts and, by default, a sign-in shortcut with `--startup` so the microphone reaches **Say Nava listen** without launcher clicks.
- Preserves user voice, dictionary, grid, label, website and app-alias settings on upgrades. Uninstall leaves user settings, logs, downloads and browser profiles rather than deleting personal runtime data.

## Included assets — actual usage only

| Asset | Active feature |
| --- | --- |
| Vosk small English-US | Offline command recognition and Nava wake commands |
| Whisper base.en | Offline dictated text and difficult selection phrases |
| Punctuation ONNX + tokenizer | Punctuate it |
| RapidOCR package assets | Visible-text recognition fallback |
| Playwright Chromium/FFmpeg | Managed browser and browser support |

**Excluded:** Qwen weights, OpenVINO, unused Whisper Tiny, the old AI planner, developer virtual environment, private app catalog, browser profiles, recordings, credentials, checkpoint keys and local logs. The assistant remains rule/native-control based; inclusion of speech/OCR assets does not reintroduce a reasoning/VLM planner.

## Windows coverage and limits

This build targets **64-bit Windows 10 (2004+) and Windows 11**. It is not an x86/32-bit or native ARM64 installer. The current development machine can verify Windows 11 only; Windows 10 needs an actual acceptance run before it can be called certified. In particular, the current Playwright release officially lists Windows 11 support, so its managed-browser layer on Windows 10 must be verified separately: https://playwright.dev/python/docs/intro

Office commands require the relevant desktop Office apps already installed. Existing Chrome/Edge control uses those browsers if installed; bundled Chromium is also available. Setup does not install paid Office, change microphone privacy permissions, disable antivirus/SmartScreen, bypass UAC or control the Windows password/PIN screen.

The optional UIAccess shell renderer requires a trusted, signed accessibility deployment. The installer does not add self-signed certificates to trusted roots or silently grant UIAccess. Ordinary native/UIA grid behavior remains available with the same permissions as the source app. Elevated apps and protected desktops keep their Windows input restrictions.

The development installer and launcher are unsigned; production distribution should use a publisher code-signing certificate. Windows 10 validation and signing remain explicit release requirements, not claimed completed tests.

## Build

On the development PC, run:

```powershell
.\packaging\Build-Installer.ps1
```

The builder uses the installed locked dependency versions, verifies pinned downloads, copies only explicitly used assets and compiles a native C# Windows launcher. The matching browser download happens on the build PC; installation is offline. Build tools are not needed by end users.

The isolated runtime uses `python312._pth` and private package/DLL paths. Existing grid and dropdown subprocesses still invoke the adjacent bundled `python.exe`, which preserves their current protocols instead of rewriting them for a frozen executable.

Artifacts:

- `dist/NAVA-AI-Setup-1.0.0-win-x64.exe` — single offline setup EXE.
- `build/NAVA AI/NAVA AI.exe` — standalone launcher within its complete application folder; do not distribute this small EXE by itself.
- `build/NAVA AI/PAYLOAD_MANIFEST.json` — byte hashes and dependency inventory.
- `build/NAVA AI/THIRD_PARTY_PACKAGES.json` — packaged dependency versions and license metadata. Distribution license files remain alongside their packages/models.

## Validation

The packaged EXE supports `--initialize` (fresh local discovery), `--self-test` (native imports, Tk, input-device enumeration, used speech/OCR assets and an offline browser smoke check), and `--ui-smoke` (short resident UI lifecycle check). These diagnostics do not execute user commands, send messages or modify documents.

The installer performs initialization during setup and fails visibly if initialization fails. Setup is per user under LocalAppData, with no system-wide Python registration or PATH change. App-local VC DLLs avoid requiring a separate administrator runtime installer.

Build documentation: https://docs.python.org/3.12/using/windows.html#the-embeddable-package and https://jrsoftware.org/isinfo.php

## Completed local acceptance results

212 source regression checks passed. Both the standalone and freshly installed EXE passed 19 native imports, Tcl/Tk, used speech/OCR asset loading and an offline managed-browser smoke check. The installed worker observed 138 controls. Fresh install, reinstall/upgrade and uninstall returned exit code 0; changed dictionary opacity and a sample download survived upgrade and uninstall, and the existing development startup shortcut was unchanged. See `dist/BUILD_VALIDATION.json`. The installer is 869,637,148 bytes (about 830 MiB), with no orphan Qwen, OpenVINO or Whisper Tiny payload.
