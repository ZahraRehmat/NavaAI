"""Lettered target chooser and click-through marks. Runs only on Tk's UI thread."""
import ctypes,io,tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk

class TargetChooser:
    def __init__(self,root,query,options,respond,stop,preview=None,activate=True):
        self.respond=respond;self.stop=stop;self.done=False;self.marks=[]
        self.window=tk.Toplevel(root);self.window.title('Gwen Doer - Choose a target');self.window.attributes('-topmost',True)
        if not activate:self.window.withdraw()
        self.window.configure(bg='#172033');self.window.protocol('WM_DELETE_WINDOW',lambda:self.finish(None))
        tk.Label(self.window,text='Which one did you mean?',bg='#172033',fg='white',font=('Segoe UI',13,'bold')).pack(anchor='w',padx=12,pady=(10,3))
        tk.Label(self.window,text='Request: '+query+'\nClick a choice or press its letter. Esc cancels. Scores show label similarity.',bg='#172033',fg='#cbd5e1',wraplength=650,justify='left').pack(anchor='w',padx=12)
        if preview:
            image=Image.open(io.BytesIO(preview));image.thumbnail((660,330));self.photo=ImageTk.PhotoImage(image)
            tk.Label(self.window,image=self.photo).pack(padx=10,pady=6)
        frame=ttk.Frame(self.window);frame.pack(fill='both',expand=True,padx=10,pady=8)
        canvas=tk.Canvas(frame,height=min(300,55*len(options)),highlightthickness=0)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        content=ttk.Frame(canvas);canvas.create_window((0,0),window=content,anchor='nw')
        content.bind('<Configure>',lambda _:canvas.configure(scrollregion=canvas.bbox('all')))
        for index,option in enumerate(options):
            letter=chr(65+index);detail=option.get('detail','');score=option.get('match_score')
            text=letter+'  '+option['label']+(f'   [{score:.0f}/100]' if isinstance(score,(int,float)) else '')
            card=ttk.Frame(content);card.pack(fill='x',pady=3)
            ttk.Button(card,text=text,width=87,command=lambda n=index:self.finish(n)).pack(fill='x')
            if detail:
                description=ttk.Label(card,text=detail,wraplength=610,justify='left',padding=(8,3))
                description.pack(fill='x');description.bind('<Button-1>',lambda _,n=index:self.finish(n))
            self.window.bind('<KeyPress-'+letter.lower()+'>',lambda _,n=index:self.finish(n))
            self.window.bind('<KeyPress-'+letter+'>',lambda _,n=index:self.finish(n))
            if option.get('bounds'):self.mark(root,letter,option['bounds'])
        ttk.Button(self.window,text='Cancel — none of these',command=lambda:self.finish(None)).pack(pady=(0,10))
        self.window.bind('<Escape>',lambda _:self.finish(None))
        self.window.geometry('+30+40')
        if activate:self.window.lift();self.window.focus_force()
        else:
            self.window.withdraw();self.window.update_idletasks()
            from ctypes import wintypes as w
            user=ctypes.WinDLL('user32');user.GetParent.argtypes=[w.HWND];user.GetParent.restype=w.HWND
            user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];user.GetWindowLongW.restype=w.LONG
            user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG]
            hwnd=user.GetParent(self.window.winfo_id()) or self.window.winfo_id()
            user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x08000080)
            self.window.deiconify()
        self.check_stop()

    def mark(self,root,letter,box):
        left,top,right,bottom=map(round,box)
        if right<=left or bottom<=top:return
        window=tk.Toplevel(root);window.withdraw();window.title('Gwen Doer - Target '+letter);window.overrideredirect(True)
        window.attributes('-topmost',True);window.configure(bg='#ff00ff');window.wm_attributes('-transparentcolor','#ff00ff')
        width=max(36,right-left+8);height=max(36,bottom-top+8)
        window.geometry(f'{width}x{height}+{max(0,left-4)}+{max(0,top-4)}')
        canvas=tk.Canvas(window,width=width,height=height,bg='#ff00ff',highlightthickness=0);canvas.pack()
        canvas.create_rectangle(3,3,width-4,height-4,outline='#ffb000',width=4)
        canvas.create_oval(2,2,31,31,fill='#ffb000',outline='#111827',width=2)
        canvas.create_text(17,17,text=letter,font=('Segoe UI',13,'bold'),fill='#111827')
        window.update_idletasks()
        user=ctypes.WinDLL('user32',use_last_error=True);from ctypes import wintypes as w
        user.GetParent.argtypes=[w.HWND];user.GetParent.restype=w.HWND
        user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];user.GetWindowLongW.restype=w.LONG
        user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG];user.SetWindowLongW.restype=w.LONG
        hwnd=user.GetParent(window.winfo_id()) or window.winfo_id()
        user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x20|0x08000000|0x80)
        window.deiconify()
        self.marks.append(window)

    def check_stop(self):
        if self.done:return
        if self.stop.is_set():self.finish(None)
        else:self.window.after(100,self.check_stop)

    def finish(self,index):
        if self.done:return
        self.done=True
        for mark in self.marks:mark.destroy()
        self.window.destroy();self.respond(index)
