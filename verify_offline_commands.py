"""Offline synthetic speech regression; temp audio only, no computer actions."""
import collections,ctypes,json,tempfile,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from speech import LocalRecognizer
from command_voice import CommandVoice

ROOT=Path(__file__).resolve().parent

def main():
    import pythoncom,win32com.client
    config=json.loads((ROOT/'voice_config.json').read_text(encoding='utf-8'))
    grid={'grid_active':True,'labels':['FG','6MJ','AB']}
    cases=[('Cell A two',{'office':'excel'},'select cell A2'),('Click six M J',grid,'click 6MJ'),
           ('Gwen grid',{},'gwen grid'),('Scroll down from F G',grid,'scroll down from FG'),
           ('Double click alpha bravo',grid,'double click AB'),('Gwen listen',{},'handsfree'),
           ('Gwen sleep',{},'sleep'),('Gwen cell A two',{'office':'excel'},'select cell A2'),
           ('Gwen click F G',grid,'click FG'),('Open Notepad',{},'open notepad'),
           ('Click WiFi',{},'click wifi'),('Open Chrome',{},'open chrome'),
           ('Gwen grid on',{},'gwen grid'),('Gwen listen type hello world',{},'type hello world'),
           ('Close Copilot',grid,'close copilot'),('Quit Copilot',grid,'quit copilot'),
           ('Type',{},'dictation_on'),('New mail',{'dictation':True},'type new mail'),
           ('Stop dictation',{'dictation':True},'dictation_off'),
           ('Gwen turn off',{},'power_off'),('Gwen turn on',{'assistant_active':False},'power_on'),
           ('Minimize this screen',grid,'minimize this screen'),('Maximize this app',grid,'maximize this app'),
           ('Close this screen',{},'close this screen'),('Minimize Chat G P T',{},'minimize chat g p t'),
           ('Open grid',{},'gwen grid'),('Turn on grid',{},'gwen grid'),
           ('Close grid',grid,'grid off'),('Turn off grid',grid,'grid off')]
    reports=[];pythoncom.CoInitialize()
    try:
        with tempfile.TemporaryDirectory(prefix='gwen-offline-voice-') as folder:
            with patch('socket.socket.connect',side_effect=AssertionError('Runtime network access forbidden')),patch('socket.socket.connect_ex',side_effect=AssertionError('Runtime network access forbidden')):
                recognizer=LocalRecognizer(config=config)
                for index,(spoken,context,expected) in enumerate(cases):
                    path=Path(folder)/f'{index}.wav';voice=win32com.client.Dispatch('SAPI.SpVoice');stream=win32com.client.Dispatch('SAPI.SpFileStream')
                    stream.Open(str(path),3,False);voice.AudioOutputStream=stream;voice.Speak(spoken);stream.Close()
                    result=recognizer.transcribe_result(path,context);session=CommandVoice(config);session.handsfree=True
                    session.dictating=bool(context.get('dictation'))
                    decision=session.route(result,context);actual=decision.get('text',decision.get('control'))
                    report={'spoken':spoken,'heard':result['text'],'expected':expected,'actual':actual,'confidence':round(result['confidence'],3),'decode_seconds':round(result['seconds'],3),'passed':actual==expected}
                    reports.append(report);print(json.dumps(report),flush=True)
                for name,audio in [('silence',np.zeros(32000,dtype=np.float32)),('synthetic_noise',np.random.default_rng(12).normal(0,.01,32000).astype(np.float32))]:
                    result=recognizer.transcribe_result(audio,grid);decision=CommandVoice(config).route(result,grid)
                    report={'input':name,'heard':result['text'],'decision':decision['kind'],'passed':decision['kind']!='command'};reports.append(report);print(json.dumps(report),flush=True)
    finally:pythoncom.CoUninitialize()
    report={'passed':all(item['passed'] for item in reports),'backend':'vosk small en-us 0.15','network_blocked_during_model_load_and_recognition':True,'raw_audio_saved':False,'tests':reports,'scope':'Synthetic Windows SAPI speech and artificial silence/noise. Human accent and room-noise accuracy remain unverified.'}
    (ROOT/'diagnostics'/'offline-command-speech-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not report['passed']:raise RuntimeError('An offline speech regression failed')

if __name__=='__main__':main()
