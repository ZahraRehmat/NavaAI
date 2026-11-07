"""Own interactive test surface. No user files, browser tabs or documents touched."""
import json,time,tkinter as tk
from pathlib import Path
from grid_display import enable_dpi_awareness,monitors
enable_dpi_awareness()
import windows_api as win
from grid_geometry import GridMap
cfg=json.loads(Path(__file__).with_name('full_grid_config.json').read_text());grid=GridMap(monitors(),cfg['columns'],cfg['rows'])
click_cell=grid.locate(299,299);right_cell=grid.locate(419,299);scroll_cell=grid.locate(779,419);drag_cell=grid.locate(539,299)

root=tk.Tk();root.title('Gwen Grid Test Surface');root.geometry('1100x700+120+100')
canvas=tk.Canvas(root,bg='#172033',highlightthickness=0);canvas.pack(fill='both',expand=True)
events=[];result_path=Path(__file__).resolve().parent/'diagnostics'/'full-grid-ui-verification.json';start=time.monotonic()
def record(kind,event):
    events.append({'kind':kind,'x':event.x_root,'y':event.y_root,'delta':getattr(event,'delta',0)})
    canvas.itemconfigure(status,text='Events: '+', '.join(e['kind'] for e in events[-10:]))
root.update()
ox,oy=canvas.winfo_rootx(),canvas.winfo_rooty()
for cell,description in ((click_cell,'click / double click / hold'),(right_cell,'right click'),(scroll_cell,'scroll')):
    x,y=cell['point'];label=cell['label']+': '+description
    canvas.create_rectangle(x-ox-55,y-oy-35,x-ox+55,y-oy+35,fill='#26384c',outline='#6ee7b7',width=3)
    canvas.create_text(x-ox,y-oy+50,text=label,fill='white',font=('Segoe UI',12))
status=canvas.create_text(20,20,anchor='nw',text='Grid test surface — no user content',fill='white',font=('Segoe UI',14))
for binding,kind in (('<Button-1>','left_down'),('<Double-Button-1>','double_click'),('<Button-3>','right_click'),('<MouseWheel>','scroll'),('<B1-Motion>','held_move'),('<ButtonRelease-1>','left_up')):
    canvas.bind(binding,lambda event,k=kind:record(k,event))
def inspect():
    kinds={e['kind'] for e in events};overlay=[]
    @win.ENUM
    def visit(hwnd,_):
        if win.title(hwnd).startswith('Gwen Doer - Full Grid') and win.user.IsWindowVisible(hwnd):overlay.append(hwnd)
        return True
    win.user.EnumWindows(visit,0)
    released=not bool(win.user.GetAsyncKeyState(1)&0x8000)
    passed={'double_click','right_click','scroll','held_move'}<=kinds and released and not overlay
    if passed or time.monotonic()-start>240:
        result={'passed':passed,'events':events,'mouse_released':released,'grid_windows_remaining':len(overlay),'physical_monitors':monitors()}
        result_path.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True);root.destroy();return
    root.after(150,inspect)
name=click_cell['label'];root.after(200,inspect);print(json.dumps({'ready':True,'title':root.title(),'surface_origin':[ox,oy],'commands':['gwen full grid',name,'double click '+name,'right click '+right_cell['label'],'scroll down on '+scroll_cell['label'],'hold '+name+' and move right 100 and release','drag '+name+' to '+drag_cell['label'],'hold '+name,'F8']}),flush=True)
root.mainloop()
