# Expanded Office connection — 29 October 2026

Select the intended Word, Excel or PowerPoint document, then type in Gwen. Voice remains off. Common supported commands use native Office APIs; unfamiliar Office wording goes to local Qwen with registered tools. Generated VBA and arbitrary COM paths are not executed. Office model calls receive a whole-primary-screen image. Office controls document protection, feature availability and modal dialogs.

## Examples

- `Delete E5` or `clear selected cells` — clears contents and retains positions/formatting.
- `Delete cells E5:F6 shift up` — structurally deletes cells and shifts remaining cells.
- `Delete the table` — deletes both the table and its contents.
- `Change table outline colour to red` — sets visible inside/outside borders in Word/Excel.

New Word tables have explicit black inside/outside borders at 0.75 pt. Table fill and table line color are separate commands. Existing tables can receive visible colored borders with the outline command.

Window commands: `switch to Word`, `switch to whats app`, or `bring Chrome to front` select a matching running window, including minimized apps, without launching another instance. Multiple matching document windows need a title unless the matching app is already selected. `close this window` binds to the selected window, asks once in a Yes/No dialog, and sends a graceful close request. It never kills the process or chooses Save/Don't Save automatically. A changed/closed target cancels the close.

- `Select cell E5`
- `Make E5 font bigger` (adds two points)
- `Make E5 font size 20`
- `Make E5 bold and red`
- `Change the font of E5 to Calibri`
- `Change selected text colour to blue`
- `Insert bullet points: First item; Second item; Third item`
- `Make table background light blue`
- `Add a row to the table`
- `Remove the table` (keeps its text/data)
- `Set column width to 22`
- `Format E5 as percentage`
- `Add a sheet named Results`
- `Add a blank slide`
- `Insert a text box: Project summary`

Named targets refer to document/slide text or Excel addresses. Empty targets use the current selection. If several tables exist, select one or specify table 1/table 2. Excel table operations use structured tables (ListObjects), not cells that merely look like a table. Excel bullets are text characters; Word and PowerPoint use native lists.

## Native coverage

All three: text entry; bold/italic/underline; font family, size, relative size and text color; background fill; selection and alignment; bullets/numbering; indent; table creation, cell text, background, add row/column and conversion to text/data; zoom; undo/redo; explicit save to an existing path.

Word: highlighting, paragraph styles/spacing, borders, page orientation/breaks, table autofit.

Excel: formulas, number formats, wrapping, widths/heights/autofit, merge/unmerge, borders, freeze panes, sorting, sheets add/select/rename, page orientation. Merge refuses to discard populated cells. Sorting uses the first selected column and treats all selected rows as data; exclude headers. Creating a structured table can generate a header row; Gwen reports actual dimensions.

PowerPoint: slides add/select/duplicate, text boxes, wrapping and vertical alignment. Advanced slide geometry, animations and arbitrary chart-data editing do not yet have parameterized tools.

## Published command catalog

Local Microsoft OfficeDev catalog: 2,570 Word, 2,243 Excel and 1,881 PowerPoint IDs (6,694 total). These are indexed IDs, not 6,694 verified workflows. `/office` lists tools; `/office search chart` finds IDs; `run office command <ID>` invokes a known command. Natural-language Office planning receives relevant candidates.

ExecuteMso supports button, toggleButton and splitButton controls only, when enabled in the current view. Galleries, dropdown values and pickers need parameterized tools or further dialog interaction. Opening a dialog is reported as invocation, not completed configuration. Generic macro/security/account/sharing commands are excluded.

Sources: https://github.com/OfficeDev/office-fluent-ui-command-identifiers and https://learn.microsoft.com/en-us/office/vba/api/office.commandbars.executemso

## Evidence and limits

`diagnostics/office-native-verification.json` records real property checks in isolated scratch instances of all three applications: bold, font family/size/color, bullets, table creation/fill, and preservation on table conversion. Excel also verified E5 selection, relative size, formulas and sheet creation; PowerPoint verified slide creation. Scratch documents were closed without saving. User documents were not used.

`diagnostics/office-planner/result.json` records local Qwen translating a combined request to increase E5 by four points and make it red. The first model interpretation failed; narrowing tools and adding relative-size examples corrected that measured case. The small model can still misunderstand unfamiliar or complex requests. This is not proof of universal language understanding or every Office workflow.

Commands do not save automatically. If a later batch step fails, Gwen reports the completed count; previous edits remain available to Undo. Finish any open modal before editing its document.
