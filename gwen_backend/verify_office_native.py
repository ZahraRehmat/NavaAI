"""Real COM checks on newly created scratch instances only. No user files used."""
import json,subprocess,ctypes,time
from pathlib import Path
from ctypes import wintypes as w
import pythoncom,win32com.client
from office_control import apply_office,office_hwnd
from office_tools import color
import windows_api as win

ROOT=Path(__file__).resolve().parent
def main():
    pythoncom.CoInitialize();rows=[]
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command',"@(Get-Process WINWORD,EXCEL,POWERPNT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress"],creationflags=subprocess.CREATE_NO_WINDOW,text=True).strip()
    existing=json.loads(raw or '[]');before=set(existing if isinstance(existing,list) else [existing])
    for kind,prog in (('word','Word.Application'),('excel','Excel.Application'),('powerpoint','PowerPoint.Application')):
        app=None;doc=None;owned=False;row={'application':kind}
        try:
            if kind=='powerpoint':
                import comtypes.client
                app=comtypes.client.CreateObject(prog)
            else:app=win32com.client.DispatchEx(prog)
            count=app.Documents.Count if kind=='word' else app.Workbooks.Count if kind=='excel' else app.Presentations.Count
            if count:
                row.update(skipped=True,reason='An isolated empty Office instance could not be established.');continue
            doc=app.Documents.Add() if kind=='word' else app.Workbooks.Add() if kind=='excel' else app.Presentations.Add()
            hwnd=office_hwnd(app,kind);pid=w.DWORD();win.user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if not pid.value or pid.value in before:
                row.update(skipped=True,reason='The scratch document belongs to a pre-existing process.');continue
            owned=True
            def run(action,target='',value='',**extra):
                return apply_office(app,kind,dict(action=action,target=target,value=value,**extra))
            if kind=='word':
                apply_office(app,kind,{'action':'write','text':'Mahnoor native test.','range':None})
                apply_office(app,kind,{'action':'format','style':'bold','target':'Mahnoor','value':True})
                row['bold_verified']=doc.Range(0,7).Font.Bold==-1
                apply_office(app,kind,{'action':'table','rows':3,'columns':2,'explicit_size':True})
                row['table_verified']=doc.Tables.Count==1 and doc.Tables(1).Rows.Count==3 and doc.Tables(1).Columns.Count==2
                run('font_size','Mahnoor','20');run('font_name','Mahnoor','Arial');run('font_color','Mahnoor','red')
                row['font_verified']=doc.Range(0,7).Font.Size==20 and doc.Range(0,7).Font.Name=='Arial' and doc.Range(0,7).Font.Color==255
                run('table_fill','table','blue');row['table_color_verified']=doc.Tables(1).Shading.BackgroundPatternColor==color('blue')
                doc.Tables(1).Cell(1,1).Range.Text='keep me'
                run('table_remove','table');row['preserve_verified']=doc.Tables.Count==0 and 'keep me' in doc.Content.Text
                app.Selection.EndKey(6);run('bullets','','first;second')
                row['bullets_verified']=any(doc.Paragraphs(i).Range.ListFormat.ListType==2 for i in range(1,doc.Paragraphs.Count+1))
                app.Selection.EndKey(6)
                apply_office(app,kind,{'action':'table','rows':2,'columns':2,'explicit_size':True})
                row['visible_borders_verified']=doc.Tables(1).Borders(-1).LineStyle==1 and doc.Tables(1).Borders(-5).LineStyle==1 and doc.Tables(1).Borders(-1).Color==0
                run('table_borders','table','red');row['border_color_verified']=doc.Tables(1).Borders(-1).Color==255
                cell=doc.Tables(1).Cell(1,1);cell.Range.Text='delete me';cell.Range.Select();run('cells_clear')
                row['cell_clear_verified']=cell.Range.Text=='\r\x07'
                run('table_delete','table');row['table_delete_verified']=doc.Tables.Count==0
            elif kind=='excel':
                apply_office(app,kind,{'action':'write','text':'Mahnoor native test','range':'A1'})
                apply_office(app,kind,{'action':'format','style':'bold','target':'Mahnoor','value':True})
                row['bold_verified']=bool(doc.ActiveSheet.Range('A1').Font.Bold)
                apply_office(app,kind,{'action':'table','rows':3,'columns':2,'explicit_size':True})
                row['table_verified']=doc.ActiveSheet.ListObjects.Count==1 and doc.ActiveSheet.ListObjects(1).Range.Columns.Count==2
                row['table_count']=doc.ActiveSheet.ListObjects.Count
                if row['table_count']:row['table_dimensions']=[doc.ActiveSheet.ListObjects(1).Range.Rows.Count,doc.ActiveSheet.ListObjects(1).Range.Columns.Count]
                run('select','E5');row['selection_verified']=app.ActiveCell.Address=='$E$5'
                run('font_size','E5','20');run('font_size_delta','E5','2');run('font_color','E5','red');run('font_name','E5','Arial')
                cell=doc.ActiveSheet.Range('E5');row['font_verified']=cell.Font.Size==22 and cell.Font.Color==255 and cell.Font.Name=='Arial'
                run('table_fill','table','blue');row['table_color_verified']=doc.ActiveSheet.ListObjects(1).Range.Interior.Color==color('blue')
                before_values=doc.ActiveSheet.UsedRange.Value
                run('table_remove','table');row['preserve_verified']=doc.ActiveSheet.ListObjects.Count==0 and doc.ActiveSheet.UsedRange.Value==before_values
                run('bullets','G1','first;second');row['bullets_verified']=doc.ActiveSheet.Range('G2').Value=='• second'
                run('formula','H1','=1+2');row['formula_verified']=doc.ActiveSheet.Range('H1').Value==3
                run('sheet_add','','ScratchTwo');row['sheet_verified']=app.ActiveSheet.Name=='ScratchTwo'
                cell=app.ActiveSheet.Range('E5');cell.Value='delete me';cell.Font.Color=255;run('cells_clear','E5')
                row['cell_clear_verified']=cell.Value is None and cell.Font.Color==255
                app.ActiveSheet.Range('E5').Value='gone';app.ActiveSheet.Range('E6').Value='shift me';run('cells_delete','E5','up')
                row['cell_shift_verified']=app.ActiveSheet.Range('E5').Value=='shift me'
                app.ActiveSheet.Range('A1').Select();apply_office(app,kind,{'action':'table','rows':3,'columns':2,'explicit_size':True})
                run('table_borders','table','red');row['border_color_verified']=app.ActiveSheet.ListObjects(1).Range.Borders(7).Color==255
                app.ActiveSheet.Range('J10').Value='outside stays';run('table_delete','table')
                row['table_delete_verified']=app.ActiveSheet.ListObjects.Count==0 and app.ActiveSheet.Range('A1').Value is None and app.ActiveSheet.Range('J10').Value=='outside stays'
            else:
                slide=doc.Slides.Add(1,12)
                box=slide.Shapes.AddTextbox(1,50,30,400,50);box.TextFrame.TextRange.Text='Mahnoor native test';box.TextFrame.TextRange.Select()
                apply_office(app,kind,{'action':'format','style':'bold','target':'Mahnoor','value':True})
                row['bold_verified']=box.TextFrame.TextRange.Characters(1,7).Font.Bold==-1
                apply_office(app,kind,{'action':'table','rows':3,'columns':2,'explicit_size':True})
                row['table_verified']=any(slide.Shapes(i).HasTable for i in range(1,slide.Shapes.Count+1))
                run('font_size','Mahnoor','20');run('font_color','Mahnoor','red');run('font_name','Mahnoor','Arial')
                font=box.TextFrame.TextRange.Characters(1,7).Font;row['font_verified']=font.Size==20 and font.Color.RGB==255 and font.Name=='Arial'
                run('table_fill','table','blue');chosen=next(s for s in slide.Shapes if s.HasTable)
                row['table_color_verified']=chosen.Table.Cell(1,1).Shape.Fill.ForeColor.RGB==color('blue')
                chosen.Table.Cell(1,1).Shape.TextFrame.TextRange.Text='keep me';run('table_remove','table')
                row['preserve_verified']=not any(s.HasTable for s in slide.Shapes) and any(s.HasTextFrame and 'keep me' in s.TextFrame.TextRange.Text for s in slide.Shapes)
                box.TextFrame.TextRange.Select();run('bullets','','first;second');row['bullets_verified']=box.TextFrame.TextRange.ParagraphFormat.Bullet.Visible==-1
                run('slide_add');row['slide_verified']=doc.Slides.Count==2
                apply_office(app,kind,{'action':'table','rows':2,'columns':2,'explicit_size':True});run('table_delete','table')
                row['table_delete_verified']=not any(s.HasTable for s in app.ActiveWindow.View.Slide.Shapes)
            row['passed']=all(v for k,v in row.items() if k.endswith('_verified'))
        except Exception as exc:row.update(passed=False,error=str(exc))
        finally:
            if doc is not None:
                try:
                    if kind=='word':doc.Close(0)
                    elif kind=='excel':doc.Close(False)
                    else:doc.Saved=True;doc.Close()
                except Exception:pass
            if owned:
                try:app.Quit()
                except Exception:pass
            rows.append(row);print(json.dumps(row),flush=True)
            (ROOT/'diagnostics'/'office-native-verification.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    pythoncom.CoUninitialize()
if __name__=='__main__':main()
