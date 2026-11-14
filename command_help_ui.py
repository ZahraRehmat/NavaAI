"""Passive contextual help overlay and an explicit, searchable manual window."""
import ctypes,json,math,time
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from ctypes import wintypes as w
from command_dictionary import ENTRIES,contextual,app_scopes,search

CONFIG=Path(__file__).with_name('command_help_config.json')
BG='#100d1c';PURPLE='#c4a6ff';TEXT='#f1ecff';MUTED='#b9afcc'

class CommandHelp:
    def __init__(self,root,config_path=CONFIG):
        self.root=root;self.path=Path(config_path)
        try:self.config=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.config={}
        self.enabled=bool(self.config.get('visible',True));self.alpha=float(self.config.get('opacity',.65))
        self.alpha=max(.30,min(.95,self.alpha));self.side=self.config.get('side','left')
        if self.side not in ('left','right'):self.side='left'
        self.rect=None;self.shown=False;self.page=0;self.state={};self.last=None;self.updated=0;self.master=None
        self.window=tk.Toplevel(root);self.window.withdraw();self.window.title('NAVA AI - Command overlay')
        self.window.overrideredirect(True);self.window.attributes('-topmost',True);self.window.attributes('-alpha',self.alpha)
        self.canvas=tk.Canvas(self.window,bg=BG,highlightthickness=1,highlightbackground='#6d4ca0');self.canvas.pack(fill='both',expand=True)
        self.window.update_idletasks();self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.user.GetParent.argtypes=[w.HWND];self.user.GetParent.restype=w.HWND
        self.user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];self.user.GetWindowLongW.restype=w.LONG
        self.user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG];self.user.SetWindowLongW.restype=w.LONG
        self.user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]
        self.user.SystemParametersInfoW.argtypes=[w.UINT,w.UINT,ctypes.c_void_p,w.UINT]
        self.user.SetWindowPos.argtypes=[w.HWND,w.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.UINT]
        self.hwnd=self.user.GetParent(self.window.winfo_id()) or self.window.winfo_id()
        self.user.SetWindowLongW(self.hwnd,-20,self.user.GetWindowLongW(self.hwnd,-20)|0x080800a0)
        self.user.SetWindowDisplayAffinity.argtypes=[w.HWND,w.DWORD];self.user.SetWindowDisplayAffinity(self.hwnd,0)

    def save(self):
        self.path.write_text(json.dumps({'visible':self.enabled,'opacity':round(self.alpha,2),'side':self.side},indent=2)+'\n',encoding='utf-8')

    def apply(self,request):
        action=request['action']
        if action=='show':self.enabled=True;self.page=0;self.save()
        elif action=='hide':
            self.enabled=False;self.save();self.close_master()
        elif action in ('master','search'):self.show_master(request.get('query',''))
        elif action=='close_master':self.close_master()
        elif action=='next':self.page+=1
        elif action=='previous':self.page=max(0,self.page-1)
        elif action in ('lighter','darker'):
            self.alpha=max(.30,min(.95,self.alpha+(-.1 if action=='lighter' else .1)))
            self.window.attributes('-alpha',self.alpha);self.save()
        elif action in ('move_left','move_right'):
            self.side='left' if action=='move_left' else 'right';self.save()
        elif action in ('down','up') and self.master is not None:
            self.tree.yview_scroll(8 if action=='down' else -8,'units')
        self.last=None;self.update(self.state,force=True)

    def update(self,state,force=False):
        now=time.monotonic()
        if not force and now-self.updated<.35:return
        self.updated=now;self.state=state
        if not self.enabled or self.master is not None or state.get('dialog'):
            if self.shown:self.user.ShowWindow(self.hwnd,0)
            self.shown=False;self.last=None;return
        target=state.get('target') or {};scopes=app_scopes(target)
        signature=(state.get('active'),target.get('hwnd'),target.get('title'),state.get('dictating'),state.get('selecting'),state.get('grid'),state.get('dialog'),self.page)
        if signature==self.last:return
        # Start a fresh page when the app or mode changes, not on speech/status ticks.
        if self.last and signature[:-1]!=self.last[:-1]:self.page=0
        self.last=signature
        screen_h=self.root.winfo_screenheight();width=min(490,max(300,self.root.winfo_screenwidth()-32))
        limit=max(3,min(8,(screen_h-600)//60));rows=[row for row in contextual(state) if row.command not in {'dictation on','dictation stop','selection mode','stop selection','open grid','grid off'}]
        pages=max(1,math.ceil(len(rows)/limit));self.page%=pages
        self.canvas.delete('all');y=14
        active=state.get('active',True)
        title='NAVA AI · COMMANDS' if active else 'NAVA AI · STANDBY'
        self.canvas.create_text(15,y,text=title,anchor='nw',fill=PURPLE,font=('Segoe UI',10,'bold'));y+=25
        if active:
            label=' + '.join(scope.title() for scope in scopes) or 'General controls'
            self.canvas.create_text(15,y,text=f'{label}   ·   {self.page+1}/{pages}',anchor='nw',fill=MUTED,font=('Segoe UI',9));y+=26
            if state.get('dialog'):
                y=self.draw_row('Say a displayed letter','Choose a marked option; say cancel to stop',y,width)
            last_section=None
            for row in rows[self.page*limit:(self.page+1)*limit]:
                if row.section!=last_section:
                    self.canvas.create_text(15,y,text=row.section.upper(),anchor='nw',fill=PURPLE,font=('Segoe UI',8,'bold'));y+=19;last_section=row.section
                y=self.draw_row(row.command,row.description,y,width)
            self.canvas.create_line(14,y+3,width-14,y+3,fill='#463256');y+=14
            footer=[('dictation stop' if state.get('dictating') else 'dictation on','Stop voice typing' if state.get('dictating') else 'Start voice typing'),
                    ('stop selection' if state.get('selecting') else 'selection mode','Stop selecting' if state.get('selecting') else 'Select text by endpoint words'),
                    ('grid off' if state.get('grid') else 'open grid','Hide mouse labels' if state.get('grid') else 'Show mouse labels'),
                    ('nava turn off','Return to standby'),
                    ('dictionary more transparent','Make this panel lighter'),
                    ('dictionary more visible','Make this panel clearer'),
                    ('move dictionary left','Move this panel to the left'),
                    ('move dictionary right','Move this panel to the right'),
                    ('hide dictionary','Hide this panel'),('open full dictionary','Search every command family')]
            if pages>1:footer.extend([('next commands page','More commands for this app'),('previous commands page','Return to the previous page')])
        else:
            footer=[('nava turn on','Activate NAVA AI and start the microphone'),('hide commands','Hide this small reminder'),('open full dictionary','Browse the complete command manual')]
        for command,description in footer:y=self.draw_row(command,description,y,width)
        y+=10
        # Use the work area so taskbars remain visible; no foreground activation.
        area=w.RECT();self.user.SystemParametersInfoW(0x30,0,ctypes.byref(area),0)
        x=max(area.left+14,area.right-width-14) if self.side=='right' else area.left+14
        top=area.top+(60 if self.side=='right' else 14) # Leave the status badge clear.
        self.canvas.configure(width=width,height=y)
        self.window.geometry(f'{width}x{y}+{x}+{top}');self.window.update_idletasks()
        self.user.SetWindowPos(self.hwnd,w.HWND(-1),x,top,width,y,0x10|0x200)
        self.rect=(x,top,x+width,top+y)
        if not self.shown:self.user.ShowWindow(self.hwnd,4);self.shown=True

    def overlay_bounds(self):
        return [self.rect] if self.enabled and self.shown and self.rect and self.master is None and not self.state.get('dialog') else []

    def restack(self):
        if self.shown:self.user.SetWindowPos(self.hwnd,w.HWND(-1),0,0,0,0,0x1|0x2|0x10|0x200)

    def draw_row(self,command,description,y,width):
        col=int(width*.46)
        a=self.canvas.create_text(15,y,text=command,anchor='nw',width=col-22,fill=TEXT,font=('Segoe UI',9,'bold'))
        b=self.canvas.create_text(col,y,text='- '+description,anchor='nw',width=width-col-16,fill=MUTED,font=('Segoe UI',9))
        return max(self.canvas.bbox(a)[3],self.canvas.bbox(b)[3])+7

    def show_master(self,query=''):
        if self.master is not None:
            self.query.set(query);self.master.deiconify();self.master.lift();self.search_entry.focus_set();return
        window=tk.Toplevel(self.root);self.master=window;window.title('NAVA AI - Full dictionary');window.configure(bg=BG)
        width=min(1100,self.root.winfo_screenwidth()-60);height=min(760,self.root.winfo_screenheight()-100)
        window.geometry(f'{width}x{height}+30+30');window.minsize(650,400);window.protocol('WM_DELETE_WINDOW',self.close_master)
        tk.Label(window,text='COMMAND DICTIONARY',fg=PURPLE,bg=BG,font=('Segoe UI',18,'bold')).pack(anchor='w',padx=20,pady=(18,3))
        tk.Label(window,text='Search a command, app or task. Examples use sample names: replace them with your own.',fg=MUTED,bg=BG,font=('Segoe UI',10)).pack(anchor='w',padx=20)
        bar=tk.Frame(window,bg=BG);bar.pack(fill='x',padx=20,pady=14)
        self.query=tk.StringVar(value=query);self.scope=tk.StringVar(value='All')
        self.search_entry=ttk.Entry(bar,textvariable=self.query,font=('Segoe UI',12));self.search_entry.pack(side='left',fill='x',expand=True)
        box=ttk.Combobox(bar,textvariable=self.scope,state='readonly',values=['All']+sorted({row.scope for row in ENTRIES}),width=16);box.pack(side='left',padx=(10,0))
        self.count=tk.StringVar();tk.Label(window,textvariable=self.count,fg=PURPLE,bg=BG).pack(anchor='w',padx=20)
        frame=tk.Frame(window,bg=BG);frame.pack(fill='both',expand=True,padx=20,pady=8)
        style=ttk.Style(window);style.configure('NavaHelp.Treeview',background='#1d162c',fieldbackground='#1d162c',foreground=TEXT,rowheight=30,font=('Segoe UI',10))
        style.map('NavaHelp.Treeview',background=[('selected','#603c91')],foreground=[('selected','white')])
        self.tree=ttk.Treeview(frame,columns=('description',),show='tree headings',style='NavaHelp.Treeview')
        self.tree.heading('#0',text='Command / category');self.tree.heading('description',text='Short description')
        self.tree.column('#0',width=400,minwidth=250);self.tree.column('description',width=540,minwidth=220)
        scroll=ttk.Scrollbar(frame,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.tree.pack(fill='both',expand=True)
        tk.Label(window,text='Voice: search dictionary for font  ·  dictionary scroll down / up  ·  close full dictionary',fg=MUTED,bg=BG,anchor='w').pack(fill='x',padx=20,pady=(3,16))
        self.query.trace_add('write',lambda *_:self.render_master());self.scope.trace_add('write',lambda *_:self.render_master())
        self.render_master();self.search_entry.focus_set();window.lift()

    def master_focused(self):
        if self.master is None:return False
        import windows_api as win
        hwnd=self.user.GetParent(self.master.winfo_id()) or self.master.winfo_id()
        return win.foreground()==hwnd

    def render_master(self):
        rows=search(self.query.get(),self.scope.get());self.tree.delete(*self.tree.get_children());parents={}
        for row in rows:
            key=(row.scope,row.section)
            if key not in parents:
                parent=parents.setdefault(row.scope,self.tree.insert('','end',text=row.scope.title(),open=True)) if row.scope not in parents else parents[row.scope]
                parents[key]=self.tree.insert(parent,'end',text=row.section,open=True)
            self.tree.insert(parents[key],'end',text=row.command,values=(row.description,))
        self.count.set(f'{len(rows)} commands  ·  '+('No matches: try a shorter keyword' if not rows else 'Grouped by app and purpose'))

    def close_master(self):
        if self.master is not None:self.master.destroy();self.master=None
        self.last=None

    def close(self):
        self.close_master();self.window.destroy()
