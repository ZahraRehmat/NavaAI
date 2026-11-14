"""Offline synthetic wake-name check. No microphone capture or app actions."""
import json,tempfile
from pathlib import Path
import pythoncom,win32com.client
from vosk import SetLogLevel
from vosk_speech import VoskRecognizer
from command_voice import CommandVoice


def main():
    SetLogLevel(-1);r=VoskRecognizer(config={'model':'models/vosk-model-small-en-us-0.15'})
    cases=[('Nava turn on',{'assistant_active':False},'power_on'),('Nava turn off',{},'power_off'),
           ('Nava listen',{},'handsfree'),('Nava show dictionary',{},'command_help'),
           ('Nava grid',{},'grid'),('Nava press enter',{},'press enter')]
    results=[];pythoncom.CoInitialize()
    try:
        with tempfile.TemporaryDirectory(prefix='nava-rename-speech-') as folder:
            for index,(spoken,context,expected) in enumerate(cases):
                path=Path(folder)/f'{index}.wav';voice=win32com.client.Dispatch('SAPI.SpVoice');stream=win32com.client.Dispatch('SAPI.SpFileStream')
                stream.Open(str(path),3,False);voice.AudioOutputStream=stream;voice.Speak(spoken);stream.Close()
                packet=r.transcribe_result(path,context);decision=CommandVoice({'handsfree':True,'assistant_active':context.get('assistant_active',True)}).route(packet,context)
                actual=decision.get('control',decision.get('text'));passed=actual==expected
                results.append({'spoken':spoken,'heard':packet['text'],'confidence':packet['confidence'],'outcome':actual,'expected':expected,'passed':passed})
                print(json.dumps(results[-1]),flush=True)
    finally:pythoncom.CoUninitialize()
    Path('diagnostics/nava-synthetic-speech.json').write_text(json.dumps({'scope':'Synthetic local SAPI speech; human accent recognition not verified','results':results},indent=2),encoding='utf-8')
    if not all(x['passed'] for x in results):raise SystemExit(1)

if __name__=='__main__':main()
