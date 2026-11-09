# Direct Excel cell and dropdown commands

Bring the intended workbook to the foreground. These commands use native Excel
cell/range APIs, not screenshot coordinates or Qwen. They work with smart grid
on or off and support spoken row numbers/NATO column letters.

| Command | Behavior |
|---|---|
| select G6 / select H7 cell | Select and scroll to that cell |
| select cell golf six | Select G6 |
| select from B2 to N6 | Select the rectangular range B2:N6 |
| select from Y7 to Z9 | Select Y7:Z9 |
| edit J7 / double click J7 | Select J7 and send Excel's F2 edit key |
| edit J7 and start dictation | Enter edit mode, then enable Gwen dictation in that window |
| press enter | Send Enter to Excel, normally committing the edit |
| copy cell C9 | Use Excel's rich clipboard copy |
| copy B2 to N6 / copy selected cells | Copy that range/selection with formulas and formatting |
| paste copied data in cell K10 | Select K10 and let Excel paste its clipboard contents |
| make a table / make a table from selected cells | Convert the selected range to an Excel table |
| make B2:N6 into a table | Create a table from the specified range |
| open cell dropdown | Open the selected cell's list-validation dropdown |
| open dropdown in G6 | Select G6 and open its validation list |

Dictation starts only when explicitly requested. Say **stop dictation** to
stop; **press enter** commits the cell using Excel's normal behavior. Complete
an existing in-cell edit or dialog before asking for another native operation.
Excel may reject COM operations while its cell editor or a modal dialog is open.

**Copy cell 9** is ambiguous because it has no column. Gwen asks for a full
address instead of inventing one. Cell and range addresses are validated; the
new targeted operations are bounded to one contiguous range of at most 10,000
cells. Existing tables are not silently converted into duplicate tables.

## Dropdown choice overlay: Word, Excel and PowerPoint

In Excel, smart-grid labels skip worksheet cells and row/column headers.
Excel's own cell addresses are the worksheet grid: say **select G6** or
**select B2 to N6**. Ribbon controls, sheet tabs, scrollbars, menus and
dialogs still receive smart-grid labels. Other applications keep their
existing labeling behavior.

Say **open dropdown**. Gwen observes the app's currently visible, enabled
dropdown controls and marks them on screen. Say the displayed letter/NATO
spelling or click the matching option. Cancel leaves menus untouched.

The two font controls have separate names:

- **open Font selection dropdown**
- **open Font size dropdown**

These names work with grid on/off across Office's shared ribbon controls.
Font/FontName and Font Size/FontSize provider names are normalized without
changing the actual native control identity. Combo boxes are preferred over
duplicate menu captions. Split buttons expand their observed menu/arrow;
their main command is not invoked as an expansion fallback.

The ordinary smart-grid overlay is temporarily hidden while dropdown-choice
marks are shown, then restored. Visible dropdowns are offered together; there
is no scrolling list or new grid paging mode. In the live Excel inspection,
43 dropdown controls were detected, including both font controls. If the active
Excel cell has a list-validation dropdown, it is offered as an additional
choice even when the arrow itself isn't exposed through accessibility.

## Implementation and verification

- `excel_commands.py`: deterministic grammar, address validation and native cell actions.
- `dropdown_choices.py`: observed dropdown candidates and marked choices.
- `dropdown_control.py`: shared naming and verified semantic expansion.
- `agent.py`: Excel routing before generic text selection/browser/file fallbacks.
- `typed_ui.py`: target/epoch-bound dictation after a successful edit request.

An isolated, unsaved Excel instance verified range selection/scrolling, table
creation, validation-list detection and rich formula/formatting paste. The
user's workbook was not edited. Tests cover
address wording, mode routing, stopping/focus guards, missing columns, table
reuse refusal, dropdown identity, cancellation and Excel/PowerPoint font choices.
PowerPoint dropdown behavior is covered by shared-provider tests; no live
PowerPoint window was available during this verification.
