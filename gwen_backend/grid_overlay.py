"""Click-through full-screen grid windows. Tk UI-thread use only."""
import ctypes,re,tkinter as tk
from ctypes import wintypes as w

class GridOverlay:
    def __init__(self,root):self.root=root;self.windows=[];self.canvases=[];self.layout=None

    def close(self):
        for window in self.windows:
            try:window.destroy()
            except tk.TclError:pass
        self.windows=[];self.canvases=[];self.layout=None

    def draw(self,snapshot):
        if not snapshot['active']:self.close();return
        layout=(snapshot.get('mode','full'),tuple(tuple(a['bounds']) for a in snapshot['areas']))
        reuse=self.layout==layout
        if not reuse:self.close()
        cfg=snapshot['config'];user=ctypes.WinDLL('user32',use_last_error=True)
        user.GetParent.argtypes=[w.HWND];user.GetParent.restype=w.HWND
        user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];user.GetWindowLongW.restype=w.LONG
        user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG];user.SetWindowLongW.restype=w.LONG
        user.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT];user.SetWindowPos.restype=w.BOOL
        user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]
        transparent='#010203'
        for index,area in enumerate(snapshot['areas']):
            l,t,r,b=area['bounds'];width,height=r-l,b-t
            if reuse:
                window=self.windows[index];canvas=self.canvases[index];canvas.delete('all')
            else:
                window=tk.Toplevel(self.root);window.withdraw();window.title('Gwen Doer - '+snapshot.get('mode','full').title()+' Grid '+str(area['monitor']))
                window.overrideredirect(True);window.configure(bg=transparent)
                window.attributes('-transparentcolor',transparent,'-topmost',True)
                window.geometry(f'{width}x{height}+0+0')
                canvas=tk.Canvas(window,width=width,height=height,bg=transparent,highlightthickness=0);canvas.pack(fill='both',expand=True)
            badges=[]
            for cell in area['cells']:
                x1,y1,x2,y2=cell['bounds'];x1-=l;y1-=t;x2-=l;y2-=t
                canvas.create_rectangle(x1,y1,x2-1,y2-1,outline=cfg['line_color'],width=1)
                caption=cell['label']
                if snapshot.get('mode')=='smart' and cell.get('scope')=='taskbar':
                    name=re.split(r'\s+[-—]\s+\d+\s+running\s+windows?\b|\s+pinned\b',cell.get('name',''),maxsplit=1,flags=re.I)[0].replace('\n',' ')
                    caption+=' · '+(name[:21]+'…' if len(name)>22 else name)
                label=canvas.create_text(x1+4,y1+3,text=caption,anchor='nw',fill=cfg['label_color'],font=('Segoe UI',-max(10,round(cfg['font_size']*1.4)),'bold'))
                box=canvas.bbox(label)
                if snapshot.get('mode')=='smart':
                    bw,bh=box[2]-box[0]+4,box[3]-box[1]+2
                    # Move crowded badges without moving the actual target outline.
                    candidates=[(x1+3,y1+2),(x2-bw,y1+2),(x1+3,y2-bh)]
                    candidates.extend((x1+3,y1+2+offset*bh) for offset in range(1,9))
                    best=None;best_score=None
                    for x,y in candidates:
                        x=max(0,min(width-bw,x));y=max(0,min(height-bh,y));candidate=(x,y,x+bw,y+bh)
                        score=sum(max(0,min(candidate[2],o[2])-max(x,o[0]))*max(0,min(candidate[3],o[3])-max(y,o[1])) for o in badges)
                        if best_score is None or score<best_score:best=candidate;best_score=score
                        if score==0:break
                    canvas.move(label,best[0]-box[0]+2,best[1]-box[1]+1);box=canvas.bbox(label);badges.append(best)
                    if best[1]>y2 or best[0]>x2:canvas.create_line((x1+x2)//2,(y1+y2)//2,best[0],best[1],fill=cfg['line_color'],dash=(2,2))
                background=canvas.create_rectangle(box[0]-2,box[1]-1,box[2]+2,box[3]+1,fill=cfg['label_background'],outline='')
                canvas.tag_lower(background,label)
            if reuse:continue
            window.update_idletasks();hwnd=user.GetParent(window.winfo_id()) or window.winfo_id()
            # LAYERED, TRANSPARENT, TOOLWINDOW and NOACTIVATE. Labels never eat clicks.
            user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x080800a0)
            # Tk deiconify can steal the edit caret or dismiss an open menu.
            user.ShowWindow(hwnd,4);user.SetWindowPos(hwnd,w.HWND(-1),l,t,width,height,0x10|0x40)
            self.windows.append(window)
            self.canvases.append(canvas)
        self.layout=layout
