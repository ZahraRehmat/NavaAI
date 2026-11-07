# Browser tab switching checkpoint — 31 October 2026

This checkpoint freezes the Gwen Doer project at the browser-tab/media milestone. Both `main` and `Browser-tab-switchinng` initially point to the same commit. The requested name "Browser tab switchinng" was normalized because Git branch names cannot contain spaces.

The permanent reference is the tag `checkpoint/browser-tab-switchinng-2026-10-31`. Preserve that tag even after branches advance.

## What is included

Every original project file is inventoried with its path, size and SHA-256 in `CHECKPOINT_MANIFEST.json`. Source, settings, app catalog, aliases, Office controls, tests and model files are stored directly in the repository (models use Git LFS). The exact Python environment, GPU cache, browser profiles, session logs/screenshots and bytecode are packed into an encrypted, split runtime archive under `checkpoint_assets/`, also using LFS. Original application code/settings are unchanged by creating this checkpoint.

Browser cookies, saved-login databases and session records are never uploaded in plaintext. The archive uses AES-256-GCM. The recovery key is intentionally OUTSIDE this repository, on the original Desktop:

`Gwen recovery key - 2026-10-31-browser-tab-switchinng.json`

Keep a separate safe copy of that file. Without it, source/models remain recoverable, but the encrypted runtime state cannot be decrypted. Browser login encryption can also depend on the original Windows account/computer.

A complete unencrypted local snapshot is additionally stored at:

`C:\Users\mahno\OneDrive\Desktop\Gwen checkpoints\2026-10-31-browser-tab-switchinng\original`

This captures the project folder, not independently installed Windows, Chrome, Office, GPU drivers or the base Python installation. Restoring on this PC preserves the existing external installations. Other PCs may need those prerequisites installed; the compiled GPU cache may need rebuilding there.

## Restore without overwriting later work

1. Close Gwen before restoring. Keep any later changes in their own commit/backup.
2. Clone the private repository into a separate checkout; install Git LFS if needed.
3. Check out the permanent checkpoint and retrieve the binary payload:

```powershell
git switch --detach checkpoint/browser-tab-switchinng-2026-10-31
git lfs pull
```

4. Use Python 3.12 with `cryptography` installed. The original PC's base Python already provides it. Restore into a NEW folder:

```powershell
py -3.12 restore_checkpoint.py --destination 'C:\Users\mahno\OneDrive\Desktop\Gwen restored checkpoint' --key-file 'C:\Users\mahno\OneDrive\Desktop\Gwen recovery key - 2026-10-31-browser-tab-switchinng.json'
```

The helper refuses to overwrite an existing destination, authenticates the encrypted archive before extracting it, and verifies every restored original file against the manifest. It does not run Gwen or execute restored browser data. Only a successful `passed: true` result confirms a complete restoration.

For source-only comparison, use `git diff checkpoint/browser-tab-switchinng-2026-10-31`; avoid a hard reset until later work is committed or backed up. GitHub's normal Download ZIP may contain LFS pointers rather than the actual binary payload; use a Git/LFS clone for full recovery.
