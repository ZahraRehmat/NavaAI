"""Self-contained Windows x64 payload builder; no target-PC pip steps."""
import argparse,hashlib,importlib.metadata as metadata,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path.home()/'.codex/tmp/nava-build-downloads'
RESOURCES={
 'python-3.12.10-embed-amd64.zip':('https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip','4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3'),
 'Microsoft.VCLibs.x64.14.00.Desktop.appx':('https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx','b56a9101f706f9d95f815f5b7fa6efbac972e86573d378b96a07cff5540c5961')}
MODELS=('vosk-model-small-en-us-0.15','whisper-base.en','punctuation-en')
EXCLUDE={'planner.py','restore_checkpoint.py','resident_ui.py','gwen.py'}
CONFIGS=('aliases.json','label_aliases.json','website_aliases.json','config.json','voice_config.json','smart_grid_config.json','command_help_config.json')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def resource(name):
 CACHE.mkdir(parents=True,exist_ok=True);url,digest=RESOURCES[name];path=CACHE/name
 if not path.exists():
  import urllib.request
  with urllib.request.urlopen(url,timeout=90) as response,path.open('wb') as output:shutil.copyfileobj(response,output)
 if sha(path)!=digest:raise ValueError('Build download hash mismatch: '+name)
 return path

def required_distributions():
 pending=[Requirement(line.strip()) for line in (ROOT/'requirements.txt').read_text().splitlines() if line.strip() and not line.startswith('#')];found={}
 while pending:
  req=pending.pop();name=canonicalize_name(req.name)
  if name in found:continue
  if req.marker and not req.marker.evaluate({'extra':''}):continue
  dist=metadata.distribution(req.name)
  if req.specifier and not req.specifier.contains(dist.version):raise ValueError('Installed dependency does not match requirements: '+str(req))
  found[name]=dist
  pending.extend(Requirement(line) for line in (dist.requires or []) if not Requirement(line).marker or Requirement(line).marker.evaluate({'extra':''}))
 return found

def copy_tree(source,dest):
 shutil.copytree(source,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.cache','.git'))

def build(destination,skip_browser=False):
 destination=destination.resolve();destination.mkdir(parents=True,exist_ok=True);runtime=destination/'runtime';runtime.mkdir(exist_ok=True)
 print('Bundling isolated Python 3.12.10...',flush=True)
 with zipfile.ZipFile(resource('python-3.12.10-embed-amd64.zip')) as archive:archive.extractall(runtime)
 with zipfile.ZipFile(resource('Microsoft.VCLibs.x64.14.00.Desktop.appx')) as archive:
  for name in archive.namelist():
   if '/' not in name and name.lower().endswith('.dll') and name.lower().startswith(('msvcp140','vcruntime140','concrt140','vcomp140')):(runtime/name).write_bytes(archive.read(name))
  for name in archive.namelist():
   if 'license' in name.lower() and not name.endswith('/'):
    target=destination/'licenses/microsoft-vclibs'/Path(name).name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
 lib=runtime/'Lib';lib.mkdir(exist_ok=True);dlls=runtime/'DLLs';dlls.mkdir(exist_ok=True);base=Path(sys.base_prefix)
 for name in ('_tkinter.pyd','tcl86t.dll','tk86t.dll','zlib1.dll','libffi-8.dll'):shutil.copy2(base/'DLLs'/name,dlls/name)
 copy_tree(base/'Lib/tkinter',lib/'tkinter')
 for name in ('tcl8.6','tk8.6','tcl8'):copy_tree(base/'tcl'/name,runtime/'tcl'/name)
 (runtime/'python312._pth').write_text('python312.zip\n.\nDLLs\nLib\nLib/site-packages\n..\nimport site\n',encoding='utf-8')
 (lib/'site-packages').mkdir(exist_ok=True)
 (lib/'site-packages/sitecustomize.py').write_text('''import os,sys,site
from pathlib import Path
base=Path(sys.executable).resolve().parent
site.addsitedir(str(base/'Lib/site-packages'))
os.environ.setdefault('TCL_LIBRARY',str(base/'tcl/tcl8.6'))
os.environ.setdefault('TK_LIBRARY',str(base/'tcl/tk8.6'))
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(base.parent/'browsers'))
_DLL_HANDLES=[]
for path in (base,base/'DLLs',base/'Lib/site-packages/pywin32_system32'):
 if path.is_dir():
  os.environ['PATH']=str(path)+os.pathsep+os.environ.get('PATH','')
  if hasattr(os,'add_dll_directory'):_DLL_HANDLES.append(os.add_dll_directory(str(path)))
''',encoding='utf-8')
 print('Copying the active dependency closure...',flush=True);distributions=required_distributions();packages=[]
 for key,dist in sorted(distributions.items()):
  packages.append({'name':dist.metadata['Name'],'version':dist.version,'license':dist.metadata.get('License-Expression',dist.metadata.get('License',''))})
  for file in dist.files or []:
   relative=Path(str(file))
   if relative.is_absolute() or '..' in relative.parts:continue
   source=Path(dist.locate_file(file))
   if not source.is_file() or source.suffix=='.pyc':continue
   target=lib/'site-packages'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 for p in ROOT.glob('*.py'):
  if p.name in EXCLUDE or p.name.startswith(('test_','verify','diagnose','setup_')) or p.name.endswith('_test_support.py'):continue
  shutil.copy2(p,destination/p.name)
 shutil.copy2(ROOT/'app_catalog.ps1',destination/'app_catalog.ps1')
 for name in CONFIGS:
  value=json.loads((ROOT/name).read_text(encoding='utf-8'))
  if name=='voice_config.json':value.update(device=None,enabled=True,handsfree=False,assistant_active=True,start_hidden=True)
  if name=='aliases.json':value={'nava browser':'google chrome'}
  (destination/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
 copy_tree(ROOT/'assets',destination/'assets');copy_tree(ROOT/'data',destination/'data')
 print('Copying only runtime-used speech/punctuation assets...',flush=True)
 for name in MODELS:copy_tree(ROOT/'models'/name,destination/'models'/name)
 extras=[p.name for p in (destination/'models').iterdir() if p.is_dir() and p.name not in MODELS]
 if extras:raise ValueError('Unexpected model directories in payload; refusing to ship: '+str(extras))
 for p in (ROOT/'README.md',ROOT/'COMMAND_DICTIONARY.md',ROOT/'NAVA_RENAME.md'):shutil.copy2(p,destination/p.name)
 (destination/'bundle.json').write_text(json.dumps({'product':'NAVA AI','version':'1.0.0','python':'3.12.10','architecture':'x64','models_included':list(MODELS),'excluded':['Qwen','OpenVINO','whisper-tiny.en','personal app catalog','browser profiles','recordings','logs']},indent=2),encoding='utf-8')
 (destination/'THIRD_PARTY_PACKAGES.json').write_text(json.dumps(packages,indent=2),encoding='utf-8');license_dir=destination/'licenses';license_dir.mkdir(exist_ok=True);shutil.copy2(base/'LICENSE.txt',license_dir/'PYTHON-TCL-TK-LICENSE.txt')
 if not skip_browser:
  print('Installing matching Chromium into the payload...',flush=True);env=os.environ.copy();env['PLAYWRIGHT_BROWSERS_PATH']=str(destination/'browsers')
  subprocess.run([sys.executable,'-m','playwright','install','chromium'],env=env,check=True)
 print('Compiling native Windows launcher...',flush=True);compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
 subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/optimize+','/out:'+str(destination/'NAVA AI.exe'),'/win32icon:'+str(ROOT/'assets/nava.ico'),'/reference:System.Windows.Forms.dll',str(ROOT/'packaging/Launcher.cs')],check=True)
 files=[{'path':p.relative_to(destination).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(destination.rglob('*')) if p.is_file() and not any(x in p.relative_to(destination).parts for x in ('logs','browser_profiles','__pycache__','downloads')) and p.name not in ('PAYLOAD_MANIFEST.json','apps.json')]
 (destination/'PAYLOAD_MANIFEST.json').write_text(json.dumps({'packages':packages,'files':files,'build_downloads':{name:{'url':url,'sha256':digest} for name,(url,digest) in RESOURCES.items()}},indent=2),encoding='utf-8')
 print('Payload ready:',destination,'files:',len(files),'packages:',len(packages),flush=True);return destination

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--destination',type=Path,default=ROOT/'build/NAVA AI');parser.add_argument('--skip-browser',action='store_true');args=parser.parse_args();build(args.destination,args.skip_browser)
