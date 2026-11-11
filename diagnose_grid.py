"""Read-only grid/provider report. No clicks, typing, installs or network calls."""
import argparse,ctypes,json,platform,subprocess,sys,time
from pathlib import Path
from importlib.metadata import version,PackageNotFoundError

ROOT=Path(__file__).resolve().parent

def collect(timeout=25):
    report={'created_at':time.time(),'python':sys.version,'windows':platform.platform(),
            'windows_build':getattr(sys.getwindowsversion(),'build',None),
            'elevated':bool(ctypes.windll.shell32.IsUserAnAdmin()),'packages':{}}
    for name in ('pywinauto','comtypes','pywin32','Pillow','playwright'):
        try:report['packages'][name]=version(name)
        except PackageNotFoundError:report['packages'][name]='NOT INSTALLED'
    try:
        # pythonw starts this tool from the launcher; the worker needs real
        # stdin/stdout JSON pipes, so use its sibling console interpreter.
        worker_python=str(Path(sys.executable).with_name('python.exe'))
        worker=subprocess.run([worker_python,'-u',str(ROOT/'smart_grid_observer.py')],
            input=json.dumps({'context':None,'force':True})+'\n',capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=timeout,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW)
        messages=[]
        for line in worker.stdout.splitlines():
            try:messages.append(json.loads(line))
            except ValueError:pass
        result=next((m for m in reversed(messages) if 'diagnostics' in m or 'error' in m),{})
        report.update(worker_exit=worker.returncode,health=result.get('diagnostics',{}),timing=result.get('timing',{}),
                      warning=result.get('warning',''),worker_error=result.get('error',''),worker_stderr=worker.stderr[-2000:])
        if not result:report['worker_error']='No completed scanner report. Check worker_stderr and installed dependencies.'
    except subprocess.TimeoutExpired:report['worker_error']='Scanner exceeded the diagnostic time limit; an accessibility provider may be unresponsive.'
    except Exception as exc:report['worker_error']=str(exc)
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--show',action='store_true');args=parser.parse_args()
    report=collect();folder=ROOT/'logs';folder.mkdir(exist_ok=True)
    output=folder/'grid-diagnostics.json';output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(output),'counts':report.get('health',{}).get('visible_by_scope',{}),'error':report.get('worker_error','')},indent=2))
    if args.show:
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw()
        counts=report.get('health',{}).get('visible_by_scope',{})
        messagebox.showinfo('Gwen grid diagnostic',
            'Read-only check complete. No input was performed.\n\nVisible targets: '+str(counts)+
            '\n\nReport saved to:\n'+str(output)+'\n\n'+report.get('worker_error',report.get('warning','')),parent=root)
        root.destroy()

if __name__=='__main__':main()
