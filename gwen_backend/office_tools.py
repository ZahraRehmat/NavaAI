"""Parameterized native Office tools. Targets are data, never executable COM paths."""
import re
from PIL import ImageColor

TOOL_APPS={
 'select':('word','excel','powerpoint'),'font_size':('word','excel','powerpoint'),'font_size_delta':('word','excel','powerpoint'),
 'font_name':('word','excel','powerpoint'),'font_color':('word','excel','powerpoint'),'fill_color':('word','excel','powerpoint'),
 'highlight':('word',),'align':('word','excel','powerpoint'),'vertical_align':('excel','powerpoint'),
 'bullets':('word','excel','powerpoint'),'numbering':('word','excel','powerpoint'),'list_remove':('word','excel','powerpoint'),
 'indent':('word','excel','powerpoint'),'line_spacing':('word','powerpoint'),'style':('word','excel'),
 'wrap_text':('excel','powerpoint'),'number_format':('excel',),'autofit':('word','excel'),
 'column_width':('excel',),'row_height':('excel',),'merge':('excel',),'unmerge':('excel',),
 'borders':('word','excel'),'table_fill':('word','excel','powerpoint'),'table_remove':('word','excel','powerpoint'),
 'table_delete':('word','excel','powerpoint'),'table_borders':('word','excel'),
 'cells_clear':('word','excel'),'cells_delete':('word','excel'),
 'table_cell':('word','excel','powerpoint'),'table_row_add':('word','excel','powerpoint'),
 'table_column_add':('word','excel','powerpoint'),'sheet_add':('excel',),'sheet_select':('excel',),'sheet_rename':('excel',),
 'freeze_panes':('excel',),'sort':('excel',),'formula':('excel',),'slide_add':('powerpoint',),'slide_select':('powerpoint',),
 'slide_duplicate':('powerpoint',),'text_box':('powerpoint',),'page_orientation':('word','excel'),
 'page_break':('word',),'zoom':('word','excel','powerpoint'),'undo':('word','excel','powerpoint'),'redo':('word','excel','powerpoint'),
 'save':('word','excel','powerpoint'),'mso':('word','excel','powerpoint')}
DESCRIPTIONS={
 'font_size':'point size 1..409','font_size_delta':'relative points, e.g. 2 or -2','font_color':'named color or #RRGGBB',
 'fill_color':'background color','table_fill':'color entire chosen table','select':'cell/range or text',
 'bullets':'value can contain semicolon/newline-separated items; empty uses selection','numbering':'same as bullets',
 'table_remove':'remove structure, preserve content','table_cell':'target table, value R2C3, text content',
 'table_delete':'delete the chosen table AND its contents; Excel clears only its table rectangle',
 'table_borders':'value named color or #RRGGBB; applies inside and outside visible lines',
 'cells_clear':'clear cell contents, preserve cell positions and formatting',
 'cells_delete':'structurally delete selected/addressed cells; value up or left',
 'mso':'value must be a supplied published control ID','formula':'target cell/range; value Excel formula',
 'style':'Word heading 1..9/normal/title, or Excel style','sort':'value ascending/descending; target range',
 'sheet_add':'value optional sheet name','sheet_rename':'target old name or selected, value new name',
 'text_box':'value text','font_name':'font family','page_orientation':'portrait/landscape'}

def check_stop(stop):
    if stop and stop.is_set():raise InterruptedError('Stopped')

def clean_target(value):
    value=(value or '').strip().strip('"\'')
    value=re.sub(r'^(?:the\s+)?(?:cell|cells|range)\s+','',value,flags=re.I)
    if value.casefold() in ('it','this','that','selection','selected','selected text','selected cells','the selection','the selected text','text','font'):return ''
    return value

def ranges(app,kind,target='',stop=None):
    target=clean_target(target);lower=target.casefold()
    if re.fullmatch(r'(?:the |selected )?table(?:\s*\d+)?',lower):
        chosen=table(app,kind,target)
        if kind!='powerpoint':return [chosen.Range]
        return [chosen.Table.Cell(r,c).Shape.TextFrame.TextRange for r in range(1,chosen.Table.Rows.Count+1) for c in range(1,chosen.Table.Columns.Count+1)]
    if kind=='word':
        if not target:return [app.Selection.Range.Duplicate]
        if lower in ('all','all text','entire document','whole document','document'):return [app.ActiveDocument.Content]
        if lower in ('paragraph','current paragraph'):return [app.Selection.Paragraphs(1).Range]
        result=[];doc=app.ActiveDocument;start=0;end=doc.Content.End
        while start<end and len(result)<1000:
            check_stop(stop);rng=doc.Range(start,end);rng.Find.ClearFormatting()
            if not rng.Find.Execute(target,False,False,False,False,False,True,0,False):break
            result.append(rng.Duplicate);start=rng.End
        if not result:raise ValueError('That text was not found in the active document.')
        return result
    if kind=='excel':
        if not target:return [app.Selection]
        if lower in ('all','all cells','used range','whole sheet'):return [app.ActiveSheet.UsedRange]
        sheet=app.ActiveSheet
        if '!' in target:
            name,target=target.rsplit('!',1);sheet=app.ActiveWorkbook.Worksheets(name.strip("'"))
        address=r'(?:\$?[A-Z]{1,3}\$?\d{1,7}(?::\$?[A-Z]{1,3}\$?\d{1,7})?|[A-Z]{1,3}:[A-Z]{1,3}|\d+:\d+)'
        if re.fullmatch(address,target,re.I):return [sheet.Range(target)]
        used=sheet.UsedRange;cell=used.Find(What=target,LookIn=-4163,LookAt=2,SearchOrder=1,SearchDirection=1,MatchCase=False,SearchFormat=False)
        if cell is None:raise ValueError('No cell contains that text in the active sheet.')
        result=[];first=cell.Address
        while cell is not None and len(result)<1000:
            check_stop(stop);result.append(cell);cell=used.FindNext(cell)
            if cell is None or cell.Address==first:break
        return result
    selection=app.ActiveWindow.Selection
    if not target:
        if selection.Type==3:return [selection.TextRange]
        if selection.Type==2:return [s.TextFrame.TextRange for s in selection.ShapeRange if s.HasTextFrame]
        raise ValueError('Select a text box or name the text to format.')
    slide=app.ActiveWindow.View.Slide
    if lower in ('title','slide title','the title') and slide.Shapes.HasTitle:return [slide.Shapes.Title.TextFrame.TextRange]
    slides=list(app.ActivePresentation.Slides) if lower in ('all slides','whole presentation') else [slide]
    result=[]
    for page in slides:
        for shape in page.Shapes:
            check_stop(stop)
            if not shape.HasTextFrame or not shape.TextFrame.HasText:continue
            text=shape.TextFrame.TextRange
            if lower in ('all','all text','all slides','whole presentation'):result.append(text);continue
            for match in re.finditer(re.escape(target),text.Text,re.I):result.append(text.Characters(match.start()+1,len(target)))
    if not result:raise ValueError('That text was not found on the selected slide(s).')
    return result

def table(app,kind,target=''):
    target=clean_target(target);m=re.fullmatch(r'table\s*(\d+)',target,re.I)
    if kind=='word':
        if m:return app.ActiveDocument.Tables(int(m[1]))
        if app.Selection.Tables.Count:return app.Selection.Tables(1)
        if app.ActiveDocument.Tables.Count==1:return app.ActiveDocument.Tables(1)
    elif kind=='excel':
        tables=app.ActiveSheet.ListObjects
        if m:return tables(int(m[1]))
        if target and target.lower() not in ('table','the table','selected table'):
            try:return tables(target)
            except Exception:pass
        try:
            chosen=app.ActiveCell.ListObject
            if chosen is not None:return chosen
        except Exception:pass
        if tables.Count==1:return tables(1)
    else:
        candidates=[s for s in app.ActiveWindow.View.Slide.Shapes if s.HasTable]
        if m:return candidates[int(m[1])-1]
        try:
            chosen=app.ActiveWindow.Selection.ShapeRange
            if chosen.Count==1 and chosen(1).HasTable:return chosen(1)
        except Exception:pass
        if len(candidates)==1:return candidates[0]
    raise ValueError('Select a table or specify table 1, table 2, or its Excel name.')

def color(value):
    rgb=ImageColor.getrgb(str(value).replace(' ',''))
    return rgb[0]+(rgb[1]<<8)+(rgb[2]<<16)

def numeric(value,minimum,maximum):
    number=float(value)
    if not minimum<=number<=maximum:raise ValueError(f'Value must be between {minimum} and {maximum}.')
    return number

def word_borders(chosen,value='black'):
    borders=chosen.Borders
    borders.Enable=True;borders.OutsideLineStyle=1;borders.InsideLineStyle=1
    borders.OutsideLineWidth=6;borders.InsideLineWidth=6
    for index in (-1,-2,-3,-4,-5,-6):
        line=borders(index);line.LineStyle=1;line.LineWidth=6;line.Color=color(value)

def apply_tool(app,kind,command,stop=None):
    op=command['action']
    if op not in TOOL_APPS:return None
    if kind not in TOOL_APPS[op]:raise ValueError(op+' is not a native feature of '+kind+'.')
    target=command.get('target','');value=command.get('value','');text=command.get('text','')
    check_stop(stop)
    if op=='mso':
        from office_catalog import execute_control
        return execute_control(app,kind,value)
    if op=='save':
        doc=app.ActiveDocument if kind=='word' else app.ActiveWorkbook if kind=='excel' else app.ActivePresentation
        if not doc.Path:raise ValueError('Choose a save location first; this document has no existing path.')
        doc.Save();return 'Saved the active '+kind+' document.'
    if op in ('undo','redo'):
        if kind=='powerpoint':app.CommandBars.ExecuteMso('Undo' if op=='undo' else 'Redo')
        else:getattr(app,op.title())()
        return op.title()+' requested.'
    if op.startswith('sheet_'):
        sheets=app.ActiveWorkbook.Worksheets
        if op=='sheet_add':
            sheet=sheets.Add()
            if value:sheet.Name=value
            return 'Added sheet '+sheet.Name+'.'
        sheet=app.ActiveSheet if not target or target.lower() in ('selected','current','sheet') else sheets(target)
        if op=='sheet_select':sheet.Activate();return 'Selected sheet '+sheet.Name+'.'
        sheet.Name=value;return 'Renamed the sheet to '+sheet.Name+'.'
    if op.startswith('slide_'):
        slides=app.ActivePresentation.Slides
        if op=='slide_add':slide=slides.Add(slides.Count+1,12);slide.Select();return 'Added a blank slide.'
        index=int(value or target);slide=slides(index)
        if op=='slide_duplicate':slide.Duplicate();return 'Duplicated slide '+str(index)+'.'
        slide.Select();return 'Selected slide '+str(index)+'.'
    if op=='text_box':
        slide=app.ActiveWindow.View.Slide;shape=slide.Shapes.AddTextbox(1,50,50,500,150);shape.TextFrame.TextRange.Text=value
        return 'Inserted a text box.'
    if op=='page_break':app.Selection.InsertBreak(7);return 'Inserted a page break.'
    if op=='page_orientation':
        if kind=='word':app.ActiveDocument.PageSetup.Orientation=1 if value.lower()=='landscape' else 0
        else:app.ActiveSheet.PageSetup.Orientation=2 if value.lower()=='landscape' else 1
        return 'Set page orientation to '+value+'.'
    if op=='zoom':
        amount=int(numeric(value,10,400))
        if kind=='word':app.ActiveWindow.View.Zoom.Percentage=amount
        elif kind=='excel':app.ActiveWindow.Zoom=amount
        else:app.ActiveWindow.View.Zoom=amount
        return 'Set zoom to '+str(amount)+'%.'
    if op.startswith('table_'):
        chosen=table(app,kind,target)
        if op=='table_delete':
            if kind=='word':chosen.Delete()
            elif kind=='excel':
                area=chosen.Range;chosen.Unlist();area.Clear()
            else:chosen.Delete()
            return 'Deleted the table and its contents.'
        if op=='table_borders':
            if kind=='word':word_borders(chosen,value)
            else:
                chosen.Range.Borders.LineStyle=1;chosen.Range.Borders.Weight=2;chosen.Range.Borders.Color=color(value)
            return 'Set the table inside and outside borders to '+value+'.'
        if op=='table_remove':
            if kind=='word':chosen.ConvertToText(1)
            elif kind=='excel':chosen.Unlist()
            else:
                rows=['\t'.join(chosen.Table.Cell(r,c).Shape.TextFrame.TextRange.Text for c in range(1,chosen.Table.Columns.Count+1)) for r in range(1,chosen.Table.Rows.Count+1)]
                shape=app.ActiveWindow.View.Slide.Shapes.AddTextbox(1,chosen.Left,chosen.Top,chosen.Width,chosen.Height)
                shape.TextFrame.TextRange.Text='\r'.join(rows);chosen.Delete()
            return 'Removed the table structure and preserved its text/data.'
        if op=='table_fill':
            rgb=color(value)
            if kind=='word':chosen.Shading.BackgroundPatternColor=rgb
            elif kind=='excel':chosen.Range.Interior.Color=rgb
            else:
                for r in range(1,chosen.Table.Rows.Count+1):
                    for c in range(1,chosen.Table.Columns.Count+1):
                        check_stop(stop);fill=chosen.Table.Cell(r,c).Shape.Fill;fill.Solid();fill.ForeColor.RGB=rgb
            return 'Changed the table background color to '+value+'.'
        if op=='table_cell':
            match=re.fullmatch(r'R(\d+)C(\d+)',value,re.I)
            if not match:raise ValueError('Specify a table cell as R2C3.')
            r,c=map(int,match.groups())
            if kind=='word':chosen.Cell(r,c).Range.Text=text
            elif kind=='excel':chosen.Range.Cells(r,c).Value=text
            else:chosen.Table.Cell(r,c).Shape.TextFrame.TextRange.Text=text
            return 'Entered text in table cell '+value+'.'
        if op=='table_row_add':
            if kind=='word':chosen.Rows.Add()
            elif kind=='excel':chosen.ListRows.Add()
            else:chosen.Table.Rows.Add()
        elif op=='table_column_add':
            if kind=='word':chosen.Columns.Add()
            elif kind=='excel':chosen.ListColumns.Add()
            else:chosen.Table.Columns.Add()
        return 'Added a table '+('row.' if op=='table_row_add' else 'column.')
    selected=ranges(app,kind,target,stop)
    if not selected:raise ValueError('No editable target was found.')
    for item in selected:
        check_stop(stop)
        if op in ('cells_clear','cells_delete'):
            if kind=='excel':
                if item.CountLarge>10000:raise ValueError('Choose at most 10,000 cells to delete/clear.')
                if op=='cells_clear':item.ClearContents()
                else:
                    if value not in ('up','left'):raise ValueError('Specify shift up or shift left for structural cell deletion.')
                    item.Delete(-4162 if value=='up' else -4159)
            else:
                if not item.Cells.Count:raise ValueError('Select cells inside a Word table first.')
                if op=='cells_delete':
                    if value not in ('up','left'):raise ValueError('Specify shift up or shift left for structural cell deletion.')
                    item.Cells.Delete(1 if value=='up' else 0)
                else:
                    for cell in item.Cells:
                        check_stop(stop);content=cell.Range.Duplicate;content.End=content.End-1;content.Text=''
        elif op=='select':
            if kind=='excel':item.Worksheet.Activate()
            item.Select()
        elif op in ('font_size','font_size_delta','font_name','font_color'):
            font=item.Font
            if op=='font_name':font.Name=value
            elif op=='font_color':
                if kind=='powerpoint':font.Color.RGB=color(value)
                else:font.Color=color(value)
            else:
                size=float(value)
                if op=='font_size_delta':
                    previous=font.Size
                    if previous is None or not 0<float(previous)<4000:raise ValueError('Mixed font sizes: specify an exact point size.')
                    size+=float(previous)
                size=numeric(size,1,409 if kind=='excel' else 1638 if kind=='word' else 3600)
                font.Size=size
        elif op=='fill_color':
            if kind=='word':item.Shading.BackgroundPatternColor=color(value)
            elif kind=='excel':item.Interior.Color=color(value)
            else:
                shapes=app.ActiveWindow.Selection.ShapeRange
                if not shapes.Count:raise ValueError('Select a text box/shape for background fill.')
                for shape in shapes:shape.Fill.Solid();shape.Fill.ForeColor.RGB=color(value)
        elif op=='highlight':
            palette={'none':0,'black':1,'blue':2,'cyan':3,'green':4,'magenta':5,'red':6,'yellow':7,'white':8,'darkblue':9,'darkcyan':10,'darkgreen':11,'violet':12,'darkred':13,'darkyellow':14,'gray':15,'lightgray':16}
            item.HighlightColorIndex=palette[value.replace(' ','').lower()]
        elif op=='align':
            labels={'left':0,'center':1,'centre':1,'right':2,'justify':3}
            index=labels[value.lower()]
            if kind=='word':item.ParagraphFormat.Alignment=index
            elif kind=='excel':item.HorizontalAlignment=[-4131,-4108,-4152,-4130][index]
            else:item.ParagraphFormat.Alignment=index+1
        elif op=='vertical_align':
            index={'top':0,'middle':1,'center':1,'bottom':2}[value.lower()]
            if kind=='excel':item.VerticalAlignment=[-4160,-4108,-4107][index]
            else:app.ActiveWindow.Selection.ShapeRange(1).TextFrame.VerticalAnchor=[1,3,4][index]
        elif op in ('bullets','numbering','list_remove'):
            content=command.get('items') or ([s.strip() for s in re.split(r'[;\n]',value) if s.strip()] if value else [])
            if kind=='word':
                if content:
                    start=item.Start;inserted='\r'.join(content);item.Text=inserted
                    item=app.ActiveDocument.Range(start,start+len(inserted.encode('utf-16-le'))//2)
                if op=='bullets':item.ListFormat.ApplyBulletDefault()
                elif op=='numbering':item.ListFormat.ApplyNumberDefault()
                else:item.ListFormat.RemoveNumbers()
            elif kind=='powerpoint':
                if content:item.Text='\r'.join(content)
                item.ParagraphFormat.Bullet.Visible=0 if op=='list_remove' else -1
                if op!='list_remove':item.ParagraphFormat.Bullet.Type=1 if op=='bullets' else 2
            else:
                if item.CountLarge>1000:raise ValueError('Select at most 1,000 cells for a text list.')
                if content:
                    for index,entry in enumerate(content):
                        check_stop(stop);item.Worksheet.Cells(item.Row+index,item.Column).Value=('• ' if op=='bullets' else str(index+1)+'. ')+entry
                else:
                    for index,cell in enumerate(item.Cells):
                        check_stop(stop)
                        if cell.HasFormula:raise ValueError('A formula cell cannot be replaced with bullet text. Choose text cells.')
                        original='' if cell.Value is None else str(cell.Value)
                        cell.Value=re.sub(r'^\s*(?:[•●▪-]|\d+[.)])\s+','',original) if op=='list_remove' else ('• ' if op=='bullets' else str(index+1)+'. ')+original
        elif op=='indent':
            delta=int(value)
            if kind=='word':item.ParagraphFormat.LeftIndent=max(0,item.ParagraphFormat.LeftIndent+18*delta)
            elif kind=='excel':item.IndentLevel=max(0,min(15,item.IndentLevel+delta))
            else:item.IndentLevel=max(1,min(5,item.IndentLevel+delta))
        elif op=='line_spacing':
            amount=numeric(value,1,10)
            if kind=='word':item.ParagraphFormat.LineSpacingRule=5;item.ParagraphFormat.LineSpacing=12*amount
            else:item.ParagraphFormat.LineRuleWithin=-1;item.ParagraphFormat.SpaceWithin=amount
        elif op=='style':
            match=re.fullmatch(r'heading\s*([1-9])',value,re.I)
            item.Style=(-1-int(match[1])) if kind=='word' and match else -1 if kind=='word' and value.lower()=='normal' else value
        elif op=='wrap_text':
            enabled=str(value).lower() not in ('false','off','no','0')
            if kind=='excel':item.WrapText=enabled
            else:app.ActiveWindow.Selection.ShapeRange(1).TextFrame.WordWrap=-1 if enabled else 0
        elif op=='number_format':
            formats={'number':'0.00','percent':'0.00%','percentage':'0.00%','date':'yyyy-mm-dd','text':'@','general':'General','currency':'$#,##0.00','pkr':'"PKR" #,##0.00'}
            item.NumberFormat=formats.get(value.lower(),value)
        elif op=='autofit':
            if kind=='word':table(app,kind,target).AutoFitBehavior(1)
            elif value.lower()=='rows':item.Rows.AutoFit()
            else:item.Columns.AutoFit()
        elif op=='column_width':item.Columns.ColumnWidth=numeric(value,0,255)
        elif op=='row_height':item.Rows.RowHeight=numeric(value,1,409)
        elif op=='merge':
            if item.CountLarge>1000:raise ValueError('Choose at most 1,000 cells to merge.')
            if sum(cell.Value is not None for cell in item.Cells)>1:raise ValueError('Several cells contain data. Move/combine their contents before merging to avoid losing values.')
            item.Merge()
        elif op=='unmerge':item.UnMerge()
        elif op=='borders':
            if kind=='word':item.Borders.Enable=0 if value=='none' else 1
            else:item.Borders.LineStyle=-4142 if value=='none' else 1
        elif op=='freeze_panes':
            item.Select();app.ActiveWindow.FreezePanes=value.lower() not in ('off','false','no')
        elif op=='sort':
            if item.Areas.Count!=1:raise ValueError('Choose one contiguous range to sort.')
            item.Sort(Key1=item.Cells(1,1),Order1=2 if value.lower().startswith('desc') else 1,Header=0)
        elif op=='formula':
            if item.CountLarge>10000 or not value.startswith('='):raise ValueError('Supply an Excel formula starting with = and a bounded range.')
            item.Formula=value
    if op=='cells_clear':return 'Cleared cell contents in '+(target or 'the selection')+'; cell positions and formatting were kept.'
    if op=='cells_delete':return 'Deleted cells in '+(target or 'the selection')+' and shifted remaining cells '+value+'.'
    return 'Applied '+op.replace('_',' ')+' to '+(target or 'the selection')+(' ('+str(value)+')' if value else '')+'.'
