"""Manage Gwen's current-user Windows sign-in startup shortcut."""
import argparse,json,os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DESCRIPTION='Gwen Doer resident assistant - current-user startup'

def shortcut_path():
    return Path(os.environ['APPDATA'])/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'Startup'/'Gwen Doer.lnk'

def expected():
    return {'target':str(ROOT/'.venv'/'Scripts'/'pythonw.exe'),'arguments':'"'+str(ROOT/'gwen.py')+'"','working_directory':str(ROOT)}

def shortcut():
    import win32com.client
    return win32com.client.Dispatch('WScript.Shell').CreateShortcut(str(shortcut_path()))

def status():
    path=shortcut_path();voice_path=ROOT/'voice_config.json'
    voice=json.loads(voice_path.read_text(encoding='utf-8')) if voice_path.exists() else {}
    mode='offline hands-free mode' if voice.get('handsfree') else 'offline wake-word mode'
    result={'shortcut':str(path),'installed':path.exists(),'starts':'after this user signs in','voice':mode if voice.get('enabled') else 'off','pre_sign_in_control':False}
    if path.exists():
        link=shortcut();result.update(target=link.TargetPath,arguments=link.Arguments,working_directory=link.WorkingDirectory,description=link.Description)
        wanted=expected()
        result['matches_this_install']=str(link.TargetPath).casefold()==wanted['target'].casefold() and link.Arguments==wanted['arguments'] and str(link.WorkingDirectory).casefold()==wanted['working_directory'].casefold()
    return result

def enable():
    wanted=expected()
    for path in (Path(wanted['target']),ROOT/'gwen.py'):
        if not path.is_file():raise FileNotFoundError('Startup target is missing: '+str(path))
    path=shortcut_path();path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and shortcut().Description!=DESCRIPTION:
        raise ValueError('A different startup shortcut already uses '+str(path)+'. It was left unchanged.')
    link=shortcut();link.TargetPath=wanted['target'];link.Arguments=wanted['arguments'];link.WorkingDirectory=wanted['working_directory'];link.Description=DESCRIPTION
    link.IconLocation=wanted['target']+',0';link.WindowStyle=1;link.Save()
    result=status()
    if not result.get('matches_this_install'):raise RuntimeError('Startup shortcut verification failed.')
    return result

def disable():
    path=shortcut_path()
    if path.exists():
        if shortcut().Description!=DESCRIPTION:raise ValueError('The shortcut belongs to another application; it was left unchanged.')
        path.unlink()
    return status()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('enable','disable','status'),nargs='?',default='status')
    args=parser.parse_args();print(json.dumps({'enable':enable,'disable':disable,'status':status}[args.action](),indent=2))

if __name__=='__main__':main()
