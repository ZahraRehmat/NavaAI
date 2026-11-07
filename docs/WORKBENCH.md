# NavaAI desktop workbench

This repository contains the desktop frontend, its runtime adapter, and source
tests. It does not contain model weights, a Python environment, browser profiles,
recordings, or conversation history. The Gwen runtime and its model are installed
separately and selected through Preferences. Without that runtime, the interface
can still open, but it cannot execute desktop requests.

This frontend connects to the existing **Gwen Doer** runtime developed from the
`gwen 3` experiments. It follows the current **typing-only** testing setup:
no microphone capture, speech recognition or spoken replies start here.

## Start

Double-click **Start NavaAI.cmd** in this folder. The local frontend environment
is installed separately from Gwen's existing model/runtime environment.

To install on another machine:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Settings discovers `OneDrive/Desktop/Gwen doer` or `Desktop/Gwen doer`. Otherwise
select the folder containing `agent.py`, `config.json`, and `.venv/Scripts/python.exe`.
Quit Gwen's original panel before connecting: both interfaces share its existing
single-instance lock so two controllers cannot run concurrently.

## Using it

- Use **Choose window** to select the app you want to control, or **Use recent**
  to follow the last app selected outside Nava. The selected window is retained
  while Nava hides. If it closes, input is refused rather than redirected.
- App-opening, app switching and grid commands do not require a previous window.
  Opening an app while a grid is active exits the grid before launch.
- The workbench hides during execution and returns without forcing focus.
- **F8** or **Stop task** requests cancellation and releases grid-held buttons.
  Model inference may take time to return; another task cannot start meanwhile.
- Existing confirmations and the original lettered target chooser are retained.
- Examples prefill common requests. **Show click labels**, **Show screen grid**
  and **Hide labels** run the existing grid controls directly.
- **Do this** sends the request. Results appear under **This session**.
  Technical logs are hidden under **Show technical details** by default.
- Browser, Office, app matching, OCR and Qwen visual control use the existing
  implementation and model files. No model is copied, retrained or downloaded.
- Connection lists the actual model/device configuration and existing test
  reports. Opening a report is not a new test run. Backend results and task
  evidence are shown without claiming independently verified success.
- History stores user requests and assistant results locally under
  `%LOCALAPPDATA%/NavaAI/workbench_sessions.json`. Selected sessions can be exported.
  Original detailed backend traces remain in Gwen's `logs` folder.
- Theme and background-browser preferences persist. Background mode applies
  only where the backend supports managed browser control.

## Scope and preserved work

Source changes are confined to this Documents/FYP/NavaAI-main copy. The Desktop/NavaAI-main
floating companion, Gwen Doer source/model/checkpoints, and NavaAI-VLM-Test
experiments are left in place. Normal runtime logs are written to Gwen's existing
logs folder. No Windows startup entry is changed.

`navaai_ui.py` retains the original preview. `main.py` now
opens `workbench_ui.py`; `backend_bridge.py` runs inside Gwen's Python environment.
The original `window.py`, `speech_worker.py`, and voice tests remain separate
legacy experiments. Their audio dependencies are listed in
`requirements-voice-legacy.txt`, not required by this typing-only frontend.

The configured Qwen3-VL OpenVINO INT4 model and inference tests are not evidence
of custom model training. Original model limitations and application coverage
still apply. Windows sign-in control remains outside this frontend's scope.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest test_workbench -v
.\.venv\Scripts\python.exe verify_workbench.py
.\.venv\Scripts\python.exe verify_input_bridge.py
```

The first integration check connects to the real runtime and requests `/apps`
and `/reset`. The input check creates a disposable text window, checks refusal
when the selected window is unavailable, types into the fixture, renders the original full
grid, checks reset and Stop, then closes the fixture and backend. Neither check
controls personal applications or starts the model. The input check temporarily
needs foreground focus and preserves the clipboard through the original executor.
`verify_workbench.py --launch-store` additionally requests a real Store launch
with a stale prior window to check the reported regression. This opens Store;
it does not install anything or run model inference.
