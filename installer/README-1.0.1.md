# NAVA AI 1.0.1 installer

Run `NAVA-AI-Setup-1.0.1-win-x64.exe` to install the current source application on 64-bit Windows 10 (2004 or later) or Windows 11.

This is a complete offline package: the private Python runtime, required libraries and native DLLs, speech and punctuation assets, browser runtime, command dictionaries, aliases, Office catalogs, artwork and configuration files are included. Office applications themselves must already be installed for their controls to be used.

The installer copies model and library folders separately from root user preferences. This fixes the previous recursive exclusion of model `config.json` files. Existing user preferences remain preserved on upgrades; required model configuration files are installed and repaired normally.

This release includes the current named-word cursor recognition repairs. It does not include Qwen, OpenVINO or unused model directories.

Validation includes source regression checks, a separate fresh installation compared against every file hash in the payload manifest, and the installed runtime self-test. The self-test now performs actual Whisper generation rather than merely loading the weights.

The installer is unsigned; Windows may display its unrecognized-publisher warning. Windows 10 compatibility still needs a test on an actual Windows 10 computer.
