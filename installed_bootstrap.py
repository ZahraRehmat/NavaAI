"""Installed EXE entry: local setup and diagnostics before the resident UI."""
import json,os,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)


def initialize():
    """Discover this PC only. No network downloads, app installation or personal-file copying."""
    from catalog import Catalog
    Catalog.refresh();catalog=Catalog()
    from folder_control import known_roots
    from website_directory import directory
    from office_catalog import summary
    report={'at':time.time(),'app_entries':len(catalog.entries),
            'file_locations':[str(p) for p in known_roots()],
            'office_controls':summary(),'python':sys.version,'root':str(ROOT)}
    directory() # Verify that bundled website/alias data is present.
    for name in ('logs','browser_profiles','downloads'): (ROOT/name).mkdir(exist_ok=True)
    (ROOT/'logs/installation-ready.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def self_test():
    import importlib
    modules=['tkinter','numpy','PIL','pyautogui','pyperclip','rapidfuzz','pythoncom','win32api',
             'comtypes','pywinauto','rapidocr_onnxruntime','faster_whisper','sounddevice','av',
             'vosk','sentencepiece','onnxruntime','winrt.windows.media.control','playwright.sync_api']
    report={'imports':{}}
    for name in modules:
        try:importlib.import_module(name);report['imports'][name]='ok'
        except Exception as error:report['imports'][name]=str(error)
    import tkinter as tk
    root=tk.Tk();root.withdraw();root.update();root.destroy();report['tk_window']='ok'
    import sounddevice as sd
    report['input_devices']=[d['name'] for d in sd.query_devices() if d['max_input_channels']>0]
    from vosk import Model,SetLogLevel
    SetLogLevel(-1);model=Model(str(ROOT/'models/vosk-model-small-en-us-0.15'))
    report['nava_vocabulary']=model.vosk_model_find_word('nava')>=0;del model
    from faster_whisper import WhisperModel
    whisper=WhisperModel(str(ROOT/'models/whisper-base.en'),device='cpu',compute_type='int8',cpu_threads=2)
    # Exercise generation, where missing decoder configuration actually fails.
    import numpy as np
    audio=np.random.default_rng(5).normal(0,.04,32000).astype('float32')
    segments,_=whisper.transcribe(audio,language='en',vad_filter=False,word_timestamps=True)
    list(segments)
    report['dictation_model']='loaded and decoded';del whisper
    from dictation_punctuation import Punctuator
    punctuation=Punctuator();report['punctuation']=punctuation.restore('hello world this is a test')
    from rapidocr_onnxruntime import RapidOCR
    ocr=RapidOCR();report['ocr']='loaded';del ocr
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        page=browser.new_page();page.set_content('<title>NAVA installer check</title><button>Ready</button>')
        report['browser']=page.get_by_role('button',name='Ready').inner_text();browser.close()
    report['passed']=all(v=='ok' for v in report['imports'].values()) and report['nava_vocabulary']
    (ROOT/'logs').mkdir(exist_ok=True)
    (ROOT/'logs/package-self-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not report['passed']:raise RuntimeError('Some packaged dependencies failed; see package-self-test.json')
    return report


def main():
    try:
        if '--initialize' in sys.argv:initialize();return
        if '--self-test' in sys.argv:self_test();return
        if not (ROOT/'logs/installation-ready.json').exists():initialize()
        from typed_ui import main as run
        run()
    except Exception:
        (ROOT/'logs').mkdir(exist_ok=True)
        text=traceback.format_exc();(ROOT/'logs/launch-error.txt').write_text(text,encoding='utf-8')
        if '--initialize' not in sys.argv and '--self-test' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,'NAVA AI could not start. Details are saved in '+str(ROOT/'logs/launch-error.txt'),'NAVA AI',0x10)
        raise

if __name__=='__main__':main()
