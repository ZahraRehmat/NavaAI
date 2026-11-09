"""Own Tk fixture for visually inspecting letter marks and choosing B."""
import ctypes,json,threading,tkinter as tk
from pathlib import Path
ctypes.windll.user32.SetProcessDPIAware()
from choice_ui import TargetChooser

root=tk.Tk();root.title('Gwen Doer - Choice fixture');root.geometry('500x230+1100+250')
widgets=[]
for name in ('Report - draft.pdf','Report - final.pdf'):
    item=tk.Label(root,text=name,font=('Segoe UI',18),bg='white',pady=14);item.pack(fill='x',padx=20,pady=15);widgets.append(item)
root.update()
options=[]
for item in widgets:
    x,y=item.winfo_rootx(),item.winfo_rooty();options.append(dict(label=item.cget('text'),match_score=94,bounds=[x,y,x+item.winfo_width(),y+item.winfo_height()]))
def finished(index):
    result={'passed':index==1,'selected_index':index,'remaining_marks':sum(mark.winfo_exists() for mark in picker.marks)}
    (Path(__file__).resolve().parent/'diagnostics'/'target-choice-ui-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result),flush=True);root.after(100,root.destroy)
picker=TargetChooser(root,'open report',options,finished,threading.Event())
root.after(120000,lambda:picker.finish(None));print('Choice UI ready. Choose B.',flush=True);root.mainloop()
