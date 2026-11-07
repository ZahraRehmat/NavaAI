"""Actual local STT on generated WAVs plus short microphone device capture."""
import json
from pathlib import Path
import numpy as np
import sounddevice as sd
import pythoncom,win32com.client
from speech import LocalRecognizer
from voice_gate import VoiceGate
from direct_commands import parse_direct,is_question

root=Path(__file__).resolve().parent; fixtures=root/'voice_test_audio'; fixtures.mkdir(exist_ok=True)
recognizer=LocalRecognizer(print); gate=VoiceGate(); results=[]
phrases=['Gwen listen','Scroll down','Scroll up','Click here','What is a computer?','Gwen sleep']
pythoncom.CoInitialize()
try:
    for i,text in enumerate(phrases):
        path=fixtures/f'command-{i}.wav'
        voice=win32com.client.Dispatch('SAPI.SpVoice'); stream=win32com.client.Dispatch('SAPI.SpFileStream')
        stream.Open(str(path),3,False); voice.AudioOutputStream=stream; voice.Speak(text); stream.Close()
        heard=recognizer.transcribe(str(path)); outcome=gate.accept(heard)
        print(text,'->',heard,'->',outcome,flush=True)
        results.append({'spoken':text,'recognized':heard,'outcome':outcome})
        assert outcome is not None,(text,heard)
        if i in (1,2): assert parse_direct(outcome['command'])['kind']=='scroll'
        if i==3: assert parse_direct(outcome['command'])['kind']=='pointer'
        if i==4: assert is_question(outcome['command'])
    assert not gate.handsfree
finally: pythoncom.CoUninitialize()
info=sd.query_devices(kind='input')
audio=sd.rec(4800,samplerate=16000,channels=1,dtype='float32'); sd.wait()
assert audio.shape==(4800,1)
print('PASS default microphone opened:',info['name'],'peak:',round(float(np.max(np.abs(audio))),4),flush=True)
(root/'voice-verification.json').write_text(json.dumps({'speech_tests':results,'microphone':info['name'],'microphone_capture_samples':len(audio),'scope':'Synthetic spoken commands and device capture; human voice accuracy remains unverified.'},indent=2),encoding='utf8')
print('PASS local speech recognition, voice session gating, command parsing, and microphone device capture',flush=True)
