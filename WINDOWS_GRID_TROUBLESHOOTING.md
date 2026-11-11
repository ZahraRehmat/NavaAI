# Grid shows only the taskbar · Windows 10 / other PCs

This symptom means the overlay and at least part of UI Automation are working.
It does **not** establish that application scanning is working. Taskbar targets
use a different scan path from normal app controls.

## Included compatibility repair

The branch keeps walking a Pane/Group/Document/container even if one provider
cached-property read fails. Previously that error could discard the whole branch
while the taskbar path continued to work. This is a reproduced code defect and a
possible explanation for the reported Windows 10 behavior, not a verified diagnosis
of the remote PC. No Windows 10 machine was available for live testing here.

Root scan errors, per-window raw/visible target counts and traversal failures are
now reported. A taskbar-only result displays an explicit warning. Input permission
and occlusion safeguards are preserved; this does not bypass Windows security.

## Check the affected Windows 10 PC

1. Check out **excel-redone** and install its requirements in a fresh Python 3.12
   environment. Do not copy another computer's `.venv`, `apps.json`, browser profile
   or UIA-generated package cache.
2. Keep an ordinary Notepad or File Explorer window visible, outside the assistant
   panel. Start with apps running normally, rather than elevated as administrator.
3. Double-click **Diagnose Grid.cmd**. It performs a bounded, read-only scan and
   saves **logs/grid-diagnostics.json**. It does not click/type, change settings,
   install software or upload the report.
4. Inspect the report for each app window's `raw_targets`, `visible_targets`,
   `property_errors`, `branch_errors` and error messages.

| Report evidence | What it tells us |
|---|---|
| Worker import/COM errors or missing packages | Dependency/provider initialization needs repair |
| Root exists, zero raw targets, property/branch errors | UIA provider reads/traversal failed |
| Raw targets exist, zero visible targets | Visibility/hit testing rejected the controls |
| A window is absent from roots | Window discovery or visibility filtering needs investigation |
| Provider runs at different privilege levels | Compare normal, non-elevated apps first; do not disable Windows protections |
| Notepad/Explorer work but browser page content does not | Investigate the browser's accessibility exposure separately |

The report includes Windows build and dependency versions, but omits control labels,
document contents and screenshots. Runtime logs should remain private. A report from
the affected PC is needed to identify its exact failure; results on the development
Windows machine do not certify every Windows 10 configuration.

From a terminal, the equivalent command is:

```powershell
.\.venv\Scripts\python.exe diagnose_grid.py
```

The full command assistant remains direct and Qwen-free. The Excel cell-label
suppression applies only to Excel; it does not intentionally hide other apps.
