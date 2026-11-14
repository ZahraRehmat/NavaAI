"""Manage NAVA AI's current-user Windows sign-in startup shortcut."""
import argparse,json,os
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DESCRIPTION='NAVA AI resident assistant - current-user startup'

def shortcut_path():
    return Path(os.environ['APPDATA'])/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'Startup'/'NAVA AI.lnk'

def expected():
    return {'target':str(ROOT/'.venv'/'Scripts'/'pythonw.exe'),'arguments':'"'+str(ROOT/'nava.py')+'"','working_directory':str(ROOT)}

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
    for path in (Path(wanted['target']),ROOT/'nava.py'):
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

def migrate():
    """Rename only this installation's existing sign-in shortcut."""
    legacy=shortcut_path().with_name('Gwen Doer.lnk')
    if not legacy.exists():return status()
    import win32com.client
    old=win32com.client.Dispatch('WScript.Shell').CreateShortcut(str(legacy))
    wanted=expected()
    old_args='"'+str(ROOT/'gwen.py')+'"'
    if str(old.TargetPath).casefold()!=wanted['target'].casefold() or str(old.WorkingDirectory).casefold()!=str(ROOT).casefold() or old.Arguments not in (old_args,wanted['arguments']):
        raise ValueError('The legacy startup shortcut belongs to another install; left unchanged.')
    if shortcut_path().exists():raise ValueError('Both shortcut names exist; no automatic overwrite was made.')
    legacy.rename(shortcut_path())
    link=shortcut();link.TargetPath=wanted['target'];link.Arguments=wanted['arguments'];link.Description=DESCRIPTION;link.Save()
    return status()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('enable','disable','status','migrate'),nargs='?',default='status')
    args=parser.parse_args();print(json.dumps({'enable':enable,'disable':disable,'status':status,'migrate':migrate}[args.action](),indent=2))

if __name__=='__main__':main()
