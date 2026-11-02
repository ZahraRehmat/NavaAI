# Workbench verification · 2 November 2026

Checks run using this folder's `.venv/Scripts/python.exe` and the existing
Gwen Doer runtime at `%USERPROFILE%/OneDrive/Desktop/Gwen doer`.

- `python -m unittest test_workbench -v`: **12 tests passed**. Covers full
  transcript persistence, corrupt-history preservation, model/report discovery,
  disconnected-command refusal, single-command dispatch and hiding/restoration,
  pending-stop behavior, uncertain disconnect outcomes, literal transcript text,
  selection retained across foreground changes, app/grid independence from old
  windows, unavailable-window refusal, and explicit-window selection persistence.
- `python verify_workbench.py --launch-store`: **passed**. Real Qt-to-Gwen connection,
  external-window enumeration, installed-app catalog, Store launch request despite
  a stale prior target, saved full transcript and clean exit.
- `python verify_input_bridge.py`: **passed**. Unavailable window refused before
  input; app list and full grid work with a stale prior target; real typing into a
  disposable Tk entry; original full-grid rendering;
  reset exits grid and clears context; Stop disables grid/releases held buttons;
  backend exits cleanly. No personal document/browser input was used in the
  successful fixture check.
- `python -m pip check`: **no broken requirements** in the frontend environment.
- Source compilation passed. Home and Preferences were rendered and visually
  inspected. Home was also checked at 900 x 620; content scrolls without clipping
  the request controls. The design uses warm light surfaces, forest navigation,
  simple request/result rows, plain labels and collapsed technical details.

Targeting now freezes the user's selected HWND/process instead of comparing it
to the foreground window Windows reveals when Nava hides. The bridge validates
that the selected window still exists; app launches, switching and grids bypass
the requirement for an old target. Nava also grants the connected backend PID
foreground permission before hiding so it can activate the selected app.

The input check exposed native DLL initialization blocking when NumPy/OpenCV
were imported from the worker after Tk started. Preloading the existing desktop
input module on the bridge's main thread resolved it. The existing backend
source and installed dependencies were not changed.

These checks do not run Qwen inference, rerun the historical browser/Office
suites, establish new model accuracy, or train a custom model. They verify the
new frontend integration and a bounded desktop-input path. Existing model,
application coverage and Windows integrity restrictions continue to apply.
