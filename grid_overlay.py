"""Click-through full-screen grid windows. Tk UI-thread use only."""
import ctypes,tkinter as tk
from tkinter import font as tkfont
from ctypes import wintypes as w
from grid_badge_layout import taskbar_layout

class GridOverlay:
    def __init__(self,root):
        self.root=root;self.windows=[];self.canvases=[];self.layout=None;self.font=None
        from uiaccess_overlay import UiAccessOverlay
        self.shell_layer=UiAccessOverlay()

    def close(self):
        self.shell_layer.close()
        for window in self.windows:
            try:window.destroy()
            except tk.TclError:pass
        self.windows=[];self.canvases=[];self.layout=None;self.font=None

    def draw(self,snapshot):
        if not snapshot['active']:self.close();return
        layout=(snapshot.get('mode','smart'),tuple(tuple(a['bounds']) for a in snapshot['areas']))
        reuse=self.layout==layout
        if not reuse:self.close()
        cfg=snapshot['config'];user=ctypes.WinDLL('user32',use_last_error=True)
        user.GetParent.argtypes=[w.HWND];user.GetParent.restype=w.HWND
        user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];user.GetWindowLongW.restype=w.LONG
        user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG];user.SetWindowLongW.restype=w.LONG
        user.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT];user.SetWindowPos.restype=w.BOOL
        user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]
        transparent='#010203'
        self.font=tkfont.Font(root=self.root,family='Segoe UI',size=-max(10,round(cfg['font_size']*1.4)),weight='bold')
        font=self.font
        for index,area in enumerate(snapshot['areas']):
            l,t,r,b=area['bounds'];width,height=r-l,b-t
            if reuse:
                window=self.windows[index];canvas=self.canvases[index];canvas.delete('all')
            else:
                window=tk.Toplevel(self.root);window.withdraw();window.title('Gwen Doer - '+snapshot.get('mode','smart').title()+' Grid '+str(area['monitor']))
                window.overrideredirect(True);window.configure(bg=transparent)
                window.attributes('-transparentcolor',transparent,'-topmost',True)
                window.geometry(f'{width}x{height}+0+0')
                canvas=tk.Canvas(window,width=width,height=height,bg=transparent,highlightthickness=0);canvas.pack(fill='both',expand=True)
            tray=[]
            for cell in area['cells']:
                if cell.get('scope')!='taskbar':continue
                x1,y1,x2,y2=cell['bounds'];point=cell.get('point',((x1+x2)//2,(y1+y2)//2))
                tray.append({'label':cell['label'],'bounds':(x1-l,y1-t,x2-l,y2-t),
                    'point':(point[0]-l,point[1]-t),'badge_size':(font.measure(cell['label'])+12,font.metrics('linespace')+6)})
                if cell.get('taskbar_bounds'):
                    bl,bt,br,bb=cell['taskbar_bounds'];tray[-1]['bar_bounds']=(bl-l,bt-t,br-l,bb-t)
            tray=taskbar_layout(tray,width,height)
            badges=[]
            for cell in area['cells']:
                if cell.get('scope')=='taskbar':continue
                x1,y1,x2,y2=cell['bounds'];x1-=l;y1-=t;x2-=l;y2-=t
                canvas.create_rectangle(x1,y1,x2-1,y2-1,outline=cfg['line_color'],width=1)
                caption=cell['label']
                label=canvas.create_text(x1+4,y1+3,text=caption,anchor='nw',fill=cfg['label_color'],font=font)
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
            # Taskbar gets a clean label-only rail. Long accessible names remain
            # available to name matching, but do not cover the clock/tray icons.
            for item in tray:
                x1,y1,x2,y2=item['box'];px,py=item['point']
                edge_x=max(x1,min(x2,px));edge_y=max(y1,min(y2,py))
                canvas.create_line(edge_x,edge_y,px,py,fill='#5b7485',width=1)
                canvas.create_oval(px-2,py-2,px+2,py+2,fill=cfg['line_color'],outline='')
            for item in tray:
                x1,y1,x2,y2=item['box']
                canvas.create_rectangle(x1,y1,x2,y2,fill=cfg['label_background'],outline='#5a8796',width=1)
                canvas.create_text((x1+x2)/2,(y1+y2)/2,text=item['label'],fill=cfg['label_color'],font=font)
            if reuse:
                # Newly opened topmost menus can cover an existing overlay.
                # Reassert z-order without taking focus or dismissing the menu.
                window.update_idletasks();hwnd=user.GetParent(window.winfo_id()) or window.winfo_id()
                user.SetWindowPos(hwnd,w.HWND(-1),0,0,0,0,0x1|0x2|0x10)
                continue
            window.update_idletasks();hwnd=user.GetParent(window.winfo_id()) or window.winfo_id()
            # LAYERED, TRANSPARENT, TOOLWINDOW and NOACTIVATE. Labels never eat clicks.
            user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x080800a0)
            # Tk deiconify can steal the edit caret or dismiss an open menu.
            user.ShowWindow(hwnd,4);user.SetWindowPos(hwnd,w.HWND(-1),l,t,width,height,0x10|0x40)
            self.windows.append(window)
            self.canvases.append(canvas)
        self.layout=layout
        shell_drawn=self.shell_layer.draw(snapshot,self.canvases)
        for window in self.windows:
            hwnd=user.GetParent(window.winfo_id()) or window.winfo_id()
            user.ShowWindow(hwnd,0 if shell_drawn else 4)
