"""Optional drawing-only shell layer; ordinary Tk remains the fallback."""
import hashlib,json,os,time,uuid
from pathlib import Path


def canvas_frame(snapshot,canvases):
    areas=[]
    for area,canvas in zip(snapshot['areas'],canvases):
        commands=[]
        for item in canvas.find_all():
            kind=canvas.type(item)
            if kind not in ('rectangle','oval','line','text'):continue
            op={'kind':kind,'coords':canvas.coords(item),'fill':canvas.itemcget(item,'fill')}
            if kind=='text':
                op.update(text=canvas.itemcget(item,'text'),anchor=canvas.itemcget(item,'anchor'),font_size=max(10,round(snapshot['config']['font_size']*1.4)))
            else:
                op['width']=float(canvas.itemcget(item,'width') or 1)
                if kind!='line':op['outline']=canvas.itemcget(item,'outline')
            commands.append(op)
        areas.append({'bounds':area['bounds'],'commands':commands})
    return {'active':True,'areas':areas}


class UiAccessOverlay:
    def __init__(self,install_root=None):
        self.install_root=Path(install_root or Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Gwen Accessibility')
        self.handle=None;self.retry_after=0;self.error='';self.verified=False

    def installed(self):
        try:
            meta=json.loads((self.install_root/'install.json').read_text(encoding='utf-8-sig'))
            return meta['exe_sha256'].lower()==hashlib.sha256((self.install_root/'GwenOverlay.exe').read_bytes()).hexdigest()
        except (OSError,KeyError,ValueError):return False

    def connect(self):
        if self.handle is not None:return True
        if time.monotonic()<self.retry_after or not self.installed():return False
        import win32api,win32file,win32pipe,win32con
        name='GwenOverlay-'+uuid.uuid4().hex;pipe='\\\\.\\pipe\\'+name
        result=win32api.ShellExecute(0,'open',str(self.install_root/'GwenOverlay.exe'),name,str(self.install_root),4)
        if result<=32:raise OSError('Windows refused the installed UIAccess helper.')
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            try:
                self.handle=win32file.CreateFile(pipe,win32con.GENERIC_READ|win32con.GENERIC_WRITE,0,None,win32con.OPEN_EXISTING,0,None)
                break
            except OSError:time.sleep(.02)
        if self.handle is None:raise OSError('UIAccess helper did not create its local drawing pipe.')
        win32pipe.SetNamedPipeHandleState(self.handle,1,None,None) # PIPE_NOWAIT, byte mode.
        greeting=b''
        while time.monotonic()<deadline:
            _,available,_=win32pipe.PeekNamedPipe(self.handle,64)
            if available:
                _,data=win32file.ReadFile(self.handle,min(available,64));greeting+=data
                if b'\n' in greeting:break
            time.sleep(.01)
        if greeting.strip()!=b'READY UIACCESS=1':raise OSError('The helper did not confirm a UIAccess token.')
        self.verified=True;self.error='';return True

    def draw(self,snapshot,canvases):
        try:
            if not self.connect():return False
            import win32file
            payload=(json.dumps(canvas_frame(snapshot,canvases),ensure_ascii=False)+'\n').encode('utf-8')
            offset=0;deadline=time.monotonic()+.2
            while offset<len(payload):
                if time.monotonic()>=deadline:raise OSError('UIAccess drawing pipe is not responding.')
                _,count=win32file.WriteFile(self.handle,payload[offset:]);offset+=count
                if not count:time.sleep(.005)
            return True
        except Exception as exc:
            self.close();self.error=str(exc);self.retry_after=time.monotonic()+10;return False

    def close(self):
        if self.handle is not None:
            try:self.handle.Close()
            except Exception:pass
        self.handle=None;self.verified=False
