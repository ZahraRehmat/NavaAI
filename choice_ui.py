"""Lettered target chooser and click-through marks. Runs only on Tk's UI thread."""
import ctypes,io,tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk

class TargetChooser:
    def __init__(self,root,query,options,respond,stop,preview=None,activate=True):
        self.respond=respond;self.stop=stop;self.done=False;self.marks=[]
        from smart_labels import smart_label
        selection=bool(options) and all(o.get('selection_role') for o in options)
        self.numbers=[o.get('choice_number') for o in options]
        self.labels=[smart_label(i) if selection or any(self.numbers) else chr(65+i) for i in range(len(options))]
        self.key_buffer='';self.key_after=None
        self.window=tk.Toplevel(root);self.window.title('Gwen Doer - Choose a target');self.window.attributes('-topmost',True)
        if not activate:self.window.withdraw()
        self.window.withdraw()
        available_width=max(360,self.window.winfo_screenwidth()-60)
        available_height=max(300,self.window.winfo_screenheight()-110)
        self.window.configure(bg='#172033');self.window.protocol('WM_DELETE_WINDOW',lambda:self.finish(None))
        self.window.bind('<KeyPress>',self.key_choice)
        if options and all(o.get('selection_role') for o in options) and any(o.get('bounds') for o in options):
            self.point_choices(root,options)
            self.present(activate)
            self.check_stop()
            return
        tk.Label(self.window,text='Which one did you mean?',bg='#172033',fg='white',font=('Segoe UI',13,'bold')).pack(anchor='w',padx=12,pady=(10,3))
        tk.Label(self.window,text='Request: '+query+'\nSay a displayed letter or its NATO spelling, click a choice, or press its letter. Say cancel to stop.',bg='#172033',fg='#cbd5e1',wraplength=min(900,available_width-30),justify='left').pack(anchor='w',padx=12)
        if any(self.numbers):
            tk.Label(self.window,text='You can also say the window number: 1, 2, 3…',bg='#172033',fg='#fbbf24').pack(anchor='w',padx=12,pady=3)
        if preview:
            image=Image.open(io.BytesIO(preview));image.thumbnail((min(660,available_width-30),min(180,available_height//5)));self.photo=ImageTk.PhotoImage(image)
            tk.Label(self.window,image=self.photo).pack(padx=10,pady=6)
        frame=ttk.Frame(self.window);frame.pack(fill='both',expand=True,padx=10,pady=8)
        # Ordinary widgets wrap to their column width; there is no scrollable
        # canvas, so every offered letter stays visible together.
        cards=[]
        for index,option in enumerate(options):
            letter=self.labels[index];detail=option.get('detail','');score=option.get('match_score')
            text=letter+'  '+option['label']+(f'   [{score:.0f}/100]' if isinstance(score,(int,float)) else '')
            card=tk.Frame(frame,bg='#24334b',highlightbackground='#425573',highlightthickness=1)
            button=tk.Button(card,text=text,command=lambda n=index:self.finish(n),
                bg='#24334b',fg='white',activebackground='#354d70',activeforeground='white',
                relief='flat',anchor='w',justify='left',padx=9,pady=6)
            button.pack(fill='x')
            description=None
            if detail:
                description=tk.Label(card,text=detail,bg='#24334b',fg='#b9c9df',justify='left',anchor='w',padx=9,pady=3)
                description.pack(fill='x');description.bind('<Button-1>',lambda _,n=index:self.finish(n))
            cards.append((card,button,description))
            if option.get('bounds'):self.mark(root,letter,option['bounds'])
        ttk.Button(self.window,text='Cancel — none of these',command=lambda:self.finish(None)).pack(pady=(0,10))
        self.window.bind('<Escape>',lambda _:self.finish(None))
        # Measure actual wrapped widget heights, expanding into columns before
        # reducing type size. Keep full option text instead of clipping it.
        self.window.update_idletasks()
        fitted=False
        for size in (11,10,9):
            for columns in range(1,min(8,max(1,len(cards)))+1):
                width=min(720,(available_width-60)//columns-12)
                for old in range(8):frame.columnconfigure(old,weight=0,minsize=0)
                for index,(card,button,description) in enumerate(cards):
                    button.configure(wraplength=max(90,width-32),font=('Segoe UI',size),pady=6)
                    if description:description.configure(wraplength=max(90,width-32),font=('Segoe UI',max(8,size-1)))
                    card.grid(row=index//columns,column=index%columns,sticky='nsew',padx=4,pady=4)
                self.window.update_idletasks()
                if self.window.winfo_reqwidth()<=available_width and self.window.winfo_reqheight()<=available_height:
                    fitted=True;break
            if fitted:break
        self.window.geometry('+20+25')
        self.present(activate)
        self.check_stop()

    def present(self,activate):
        if activate:self.window.deiconify();self.window.lift();self.window.focus_force()
        else:
            self.window.withdraw();self.window.update_idletasks()
            from ctypes import wintypes as w
            user=ctypes.WinDLL('user32');user.GetParent.argtypes=[w.HWND];user.GetParent.restype=w.HWND
            user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];user.GetWindowLongW.restype=w.LONG
            user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG]
            hwnd=user.GetParent(self.window.winfo_id()) or self.window.winfo_id()
            user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x08000080)
            self.window.deiconify()

    def point_choices(self,root,options):
        role=options[0]['selection_role'].upper();phrase=options[0]['selection_phrase']
        tk.Label(self.window,text='Choose a dropdown to open' if role=='DROPDOWN' else 'Select the correct '+role+' point',bg='#172033',fg='white',
                 font=('Segoe UI',13,'bold')).pack(anchor='w',padx=12,pady=(10,4))
        tk.Label(self.window,text=('Say a letter beside the marked control.\nFor example: A / alpha, F / foxtrot. Say cancel to stop.' if role=='DROPDOWN' else 'Which “'+phrase+'”? Say the letter beside the word.\nFor example: A / alpha, F / foxtrot. Say cancel to stop.'),
                 bg='#172033',fg='#cbd5e1',justify='left',wraplength=460).pack(anchor='w',padx=12)
        row=tk.Frame(self.window,bg='#172033');row.pack(fill='x',padx=10,pady=8)
        ttk.Button(row,text='Cancel',command=lambda:self.finish(None)).pack(side='right')
        missing=[(index,o) for index,o in enumerate(options) if not o.get('bounds')]
        if missing:
            tk.Label(self.window,text='Other dropdown choices:' if role=='DROPDOWN' else 'Other choices (outside the visible text):',bg='#172033',fg='#cbd5e1').pack(anchor='w',padx=12)
            extra=tk.Frame(self.window,bg='#172033');extra.pack(fill='x',padx=10,pady=4)
            for position,(index,option) in enumerate(missing):
                title='Occurrence '+str(option['occurrence']) if option.get('occurrence') else option['label']
                ttk.Button(extra,text=self.labels[index]+' · '+title,command=lambda n=index:self.finish(n)).grid(row=position//3,column=position%3,padx=3,pady=3)
        for index,option in enumerate(options):
            letter=self.labels[index]
            if option.get('bounds'):self.mark(root,letter,option['bounds'],word=True)
        self.window.bind('<Escape>',lambda _:self.finish(None))
        self.window.update_idletasks()
        # Choose the corner that covers the fewest observed words.
        width=self.window.winfo_reqwidth();height=self.window.winfo_reqheight()
        sw=self.window.winfo_screenwidth();sh=self.window.winfo_screenheight()
        corners=[(sw-width-20,20),(20,20),(sw-width-20,sh-height-80),(20,sh-height-80)]
        def overlap(point):
            x,y=point
            return sum(max(0,min(x+width,b[2])-max(x,b[0]))*max(0,min(y+height,b[3])-max(y,b[1])) for b in (o['bounds'] for o in options if o.get('bounds')))
        x,y=min(corners,key=overlap)
        self.window.geometry(f'+{max(0,x)}+{max(0,y)}')

    def mark(self,root,letter,box,word=False):
        left,top,right,bottom=map(round,box)
        if right<=left or bottom<=top:return
        window=tk.Toplevel(root);window.withdraw();window.title('Gwen Doer - Target '+letter);window.overrideredirect(True)
        window.attributes('-topmost',True);window.configure(bg='#ff00ff');window.wm_attributes('-transparentcolor','#ff00ff')
        lift=32 if word and top>=32 else 0
        width=max(36,right-left+8);height=max(36,bottom-top+8+lift)
        window.geometry(f'{width}x{height}+{max(0,left-4)}+{max(0,top-4-lift)}')
        canvas=tk.Canvas(window,width=width,height=height,bg='#ff00ff',highlightthickness=0);canvas.pack()
        canvas.create_rectangle(3,3+lift,width-4,height-4,outline='#ffb000',width=2 if word else 4)
        center=width//2 if word else 17
        canvas.create_oval(center-15,1,center+15,31,fill='#ffb000',outline='#111827',width=2)
        canvas.create_text(center,16,text=letter,font=('Segoe UI',13,'bold'),fill='#111827')
        window.update_idletasks()
        user=ctypes.WinDLL('user32',use_last_error=True);from ctypes import wintypes as w
        user.GetParent.argtypes=[w.HWND];user.GetParent.restype=w.HWND
        user.GetWindowLongW.argtypes=[w.HWND,ctypes.c_int];user.GetWindowLongW.restype=w.LONG
        user.SetWindowLongW.argtypes=[w.HWND,ctypes.c_int,w.LONG];user.SetWindowLongW.restype=w.LONG
        hwnd=user.GetParent(window.winfo_id()) or window.winfo_id()
        user.SetWindowLongW(hwnd,-20,user.GetWindowLongW(hwnd,-20)|0x20|0x08000000|0x80)
        window.deiconify()
        self.marks.append(window)

    def key_choice(self,event):
        if self.key_after:self.window.after_cancel(self.key_after);self.key_after=None
        if event.keysym=='Return':
            if self.key_buffer in self.labels:self.finish(self.labels.index(self.key_buffer))
            return
        char=event.char.upper()
        if len(char)!=1 or not 'A'<=char<='Z':return
        self.key_buffer+=char
        if not any(label.startswith(self.key_buffer) for label in self.labels):self.key_buffer=char
        value=self.key_buffer
        if value in self.labels and not any(label!=value and label.startswith(value) for label in self.labels):
            self.finish(self.labels.index(value));return
        def complete():
            self.key_after=None
            if value in self.labels:self.finish(self.labels.index(value))
            self.key_buffer=''
        self.key_after=self.window.after(700,complete)

    def check_stop(self):
        if self.done:return
        if self.stop.is_set():self.finish(None)
        else:self.window.after(100,self.check_stop)

    def finish(self,index):
        if self.done:return
        self.done=True
        if self.key_after:self.window.after_cancel(self.key_after);self.key_after=None
        for mark in self.marks:mark.destroy()
        self.window.destroy();self.respond(index)
