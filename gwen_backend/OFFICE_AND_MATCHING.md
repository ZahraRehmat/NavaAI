Current coverage and verification: see [OFFICE_CAPABILITIES.md](OFFICE_CAPABILITIES.md). The notes below describe the earlier adapter.

# Natural labels and native Office control

Label matching uses RapidFuzz and a dynamic dictionary of actual observed UIA/DOM/OCR labels and filenames. The editable built-in aliases are in `label_aliases.json`. It handles punctuation, apostrophes, word order, optional file extensions, partial long titles and small word typos. Typed document content stays literal.

`click 2024 datesheet mahnoor` can match the unique visible title `Datesheet+2023-Mahnoor_Karachi.Pdf`; Gwen reports the selected full title and the conflicting year. An exact 2024 candidate takes priority when available. Close competing candidates ask for clarification. Explicit file-extension conflicts and non-year number conflicts are not silently ignored.

## What the Word/Excel runs showed

In `session-20261028-220757-019586.jsonl`, `bold Mahnoor` reached a command guard without a native Office route, while `dont save` failed matching and `Don't save` succeeded. Recent-file queries required exact/prefix labels. Some early Excel clicks also carried Program Manager as their target, so the dictionary cannot by itself guarantee that the intended Office app has focus.

## Office connector

All three installed desktop applications expose native COM object models. No connected Codex Office add-in session was found. Gwen now uses local pywin32 for Word/Excel and typed comtypes for PowerPoint. PowerPoint's restricted HWND property requires typed access. The adapter checks both process identity and document-window ancestry before editing. It executes fixed operations rather than generated VBA or arbitrary code, and does not automatically save documents.

With the intended Office document selected, examples include:

- `bold Mahnoor` — matching text in Word or PowerPoint's current slide; matching cells on Excel's active sheet.
- `make it bold`, `italicize selected text`, `underline A1:C3` — current selection or an Excel range.
- `type Hello World.` — document/text cursor; Excel's active cell.
- `write hello in A1` — Excel cell/range entry.
- `insert a table with three rows and four columns`, `insert 3 by 4 table` — native tables.

Excel may generate an additional header row; Gwen reports the actual resulting dimensions. Formatting named text can apply to multiple matches and reports the count. These are common supported operations, not a complete natural-language interface to every Office feature. Unsupported complex tasks retain the general planner path.

## Verification

84 regression tests passed. `diagnostics/label-match-verification.json` records real OCR of the example title and successful approximate matching with a year warning. `diagnostics/office-native-verification.json` records real formatting/table checks in separate new scratch instances of Word, Excel and PowerPoint. The scratch documents were closed without saving; existing user workbooks were not used. Table/format results were checked through Office properties. Tests of the native adapter do not establish that every complex Office workflow works.

Microsoft references:

- https://learn.microsoft.com/en-us/office/vba/api/word.tables.add
- https://learn.microsoft.com/en-us/office/vba/api/excel.font.bold
- https://learn.microsoft.com/en-us/office/vba/api/excel.listobjects.add
- https://learn.microsoft.com/en-us/office/vba/api/powerpoint.shapes.addtable
- https://learn.microsoft.com/en-us/office/dev/add-ins/overview/office-add-ins
