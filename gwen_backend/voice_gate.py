"""Wake/session logic shared by live microphone and deterministic tests."""
import re,time
from direct_commands import is_action_request,is_question,normalize_command

class VoiceGate:
    def __init__(self): self.handsfree=False; self.armed_until=0

    def arm(self,seconds=12): self.armed_until=time.monotonic()+seconds

    def accept(self,text):
        text=text.strip().rstrip('.!?').strip()
        if not text: return None
        wake=re.match(r'^(?:(?:hey|okay|ok)\s+)?(gwen|guen|glen|when|queen)\b[,:]?\s*(.*)$',text,re.I)
        if wake and wake[1].lower() in ('when','queen','glen') and not re.match(r'^(?:listen|scroll|click|open|type|press|stop|sleep|show|hide|mute|question|explain)\b',wake[2],re.I): wake=None
        if wake: text=wake[2].strip()
        accepted=bool(wake) or self.handsfree or time.monotonic()<self.armed_until
        if text.lower().removeprefix('please ') in ('stop','cancel','stop now','stop scrolling','stop the task','cancel task','cancel the task'): return {'control':'stop'}
        if not accepted: return None
        if not text or text.lower() in ('wake up','listen once'):
            self.arm(); return {'control':'armed'}
        if text.lower() in ('listen','start listening','hands free','hands-free','listen continuously'):
            self.handsfree=True; self.armed_until=0; return {'control':'handsfree'}
        if text.lower() in ('sleep','go to sleep','stop listening','pause listening'):
            self.handsfree=False; self.armed_until=0; return {'control':'sleep'}
        if text.lower() in ('show chat','open chat window','show yourself'): return {'control':'show'}
        if text.lower() in ('hide chat','hide yourself'): return {'control':'hide'}
        if text.lower() in ('mute microphone','microphone off','turn off microphone'): return {'control':'mic_off'}
        if text.lower() in ('reset','reset conversation','clear chat'): return {'command':'/reset'}
        if not (is_action_request(text) or is_question(text)):
            return {'control':'unclear'} if wake or time.monotonic()<self.armed_until else None
        self.armed_until=0
        return {'command':normalize_command(text)}
