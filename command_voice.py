"""Conservative voice session routing, separate from recognition and input."""
import re,time
from direct_commands import is_action_request,is_question
from speech_context import correct

def power_intent(text):
    match=re.fullmatch(r'(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)[,:]?\s+(?:turn|switch)\s+(on|off)[.!]?',text.strip(),re.I)
    return ('power_on' if match[1].lower()=='on' else 'power_off') if match else None


def normalize_repetition(text):
    """Collapse only explicit, identical repeated commands/targets, not homophones."""
    # Dictation payloads must remain literal.
    if re.match(r'^(?:type|write|dictate)\b',text,re.I):return text
    verbs=r'(?:open|launch|close|quit|stop|force close|force stop|terminate)'
    repeated=re.fullmatch(r'('+verbs+r'\s+.+?)\s+\1',text,re.I)
    if repeated:return repeated[1]
    named=re.fullmatch(r'(.+?)\s+('+verbs+r')\s+\1',text,re.I)
    if named:return named[2]+' '+named[1]
    return text

class CommandVoice:
    def __init__(self,config=None):
        self.config=config or {};self.handsfree=bool(self.config.get('handsfree',False));self.armed_until=0;self.dictating=False
        self.active=bool(self.config.get('assistant_active',True))
        self.selecting=False;self.recent_dictation=''
        if not self.active:self.handsfree=False

    def route(self,result,context=None):
        context=context or {};raw=result.get('text','').strip()
        if not raw:return {'kind':'ignore'}
        wake=re.match(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)\b[,:]?\s*(.*)$',raw,re.I)
        text=normalize_repetition(wake[1].strip() if wake else raw)
        low=text.lower().rstrip('.!?').strip().removeprefix('please ')
        confidence=float(result.get('confidence',0))
        power=power_intent(raw)
        if power and confidence>=self.config.get('review_confidence',.86):
            self.active=power=='power_on';self.handsfree=self.active;self.armed_until=0;self.dictating=False
            self.selecting=False
            return {'kind':'control','control':power}
        if power or not self.active:return {'kind':'ignore'}
        if low in ('stop','stop now','cancel','cancel task','stop the task') and confidence>=.5:
            self.dictating=False;self.selecting=False;return {'kind':'control','control':'stop'}
        if not (wake or self.handsfree or self.dictating or self.selecting or time.monotonic()<self.armed_until):return {'kind':'ignore'}
        if confidence<self.config.get('minimum_confidence',.72):
            return {'kind':'review','text':text,'raw':raw,'reason':'Speech confidence is low; repeat or review the command.','confirmable':False}
        from voice_controls import DICTATION_ON,DICTATION_OFF
        if low in DICTATION_OFF:
            self.dictating=False;return {'kind':'control','control':'dictation_off'}
        if low in DICTATION_ON:
            self.dictating=True;self.selecting=False
            return {'kind':'control','control':'dictation_on'}
        if context.get('office')=='excel':
            from excel_commands import parse as parse_excel
            if parse_excel(text):
                if context.get('busy'):return {'kind':'review','text':text,'raw':raw,'reason':'Wait for the current Excel command to finish.','confirmable':False}
                return {'kind':'command','text':text,'raw':raw,'code':''}
        from selection_commands import ON,OFF,range_command,canonical
        if low in ON:
            self.dictating=False;self.selecting=True
            return {'kind':'control','control':'selection_on'}
        if low in OFF:
            self.selecting=False;return {'kind':'control','control':'selection_off'}
        if self.selecting:
            from direct_commands import parse_direct
            if low in DICTATION_ON:
                self.selecting=False;self.dictating=True;return {'kind':'control','control':'dictation_on'}
            edit=parse_direct(text)
            if edit and edit['kind'] in ('keys','punctuate'):
                return {'kind':'command','text':text,'raw':raw,'code':''}
            command=range_command(text,mode=True)
            if command:
                if context.get('busy'):return {'kind':'review','text':text,'raw':raw,'reason':'Wait for the current task to finish, then repeat the range.','confirmable':False}
                return {'kind':'command','text':canonical(command),'raw':raw,'code':''}
            edit=parse_direct(text)
            if not edit or edit['kind'] not in ('keys','punctuate'):
                return {'kind':'review','text':text,'raw':raw,'reason':'Say the start and end words, for example Islamabad to Karachi, or stop selection.','confirmable':False}
            return {'kind':'command','text':text,'raw':raw,'code':''}
        if self.dictating:
            from direct_commands import parse_direct
            edit=parse_direct(text)
            if edit and edit['kind'] in ('keys','select_text','font_delta','punctuate'):
                return {'kind':'command','text':text,'raw':raw,'code':'','dictation_input':True}
            from dictation_punctuation import raw_dictation
            payload=raw_dictation(edit['text'] if edit and edit['kind']=='type' else raw)
            if not payload:return {'kind':'ignore'}
            self.recent_dictation=(self.recent_dictation+' '+payload)[-1000:]
            return {'kind':'command','text':'type '+payload,'raw':raw,'code':'','dictation_input':True}
        # Wake/listen and the command can be spoken in one breath.
        if wake:
            joined=re.fullmatch(r'(?:listen|start listening)(?:\s+gwen)?\s+(.+)',text,re.I)
            if re.fullmatch(r'listen\s+gwen',text,re.I):text='listen';low='listen'
            elif joined:
                self.handsfree=True;self.armed_until=0
                text=joined[1].strip();low=text.lower().rstrip('.!?').strip()
        controls={'listen':'handsfree','start listening':'handsfree','listen continuously':'handsfree','hands free':'handsfree','hands-free':'handsfree',
                  'type':'dictation_on','start dictation':'dictation_on','typing mode':'dictation_on',
                  'sleep':'sleep','go to sleep':'sleep','stop listening':'sleep','pause listening':'sleep',
                  'show chat':'show','hide chat':'hide','mute microphone':'mic_off','microphone off':'mic_off',
                  'confirm command':'confirm','confirm':'confirm','yes':'confirm','no':'reject','reject command':'reject'}
        controls.update({phrase:'dictation_on' for phrase in DICTATION_ON})
        if not text or low in ('wake up','listen once'):
            self.armed_until=time.monotonic()+12;return {'kind':'control','control':'armed'}
        if low in controls:
            control=controls[low]
            if control=='dictation_on':self.dictating=True
            if control=='handsfree':self.handsfree=True;self.armed_until=0
            if control=='sleep':self.handsfree=False;self.armed_until=0
            return {'kind':'control','control':control}
        from grid_commands import toggle_intent
        toggle=toggle_intent(text)
        if toggle:text='gwen grid' if toggle=='smart_unavailable' else 'grid off'
        # A high-confidence wake word must not hide a weakly heard app name.
        if re.match(r'^(?:open|launch|start|click)\s+',text,re.I):
            words=result.get('words',[])
            ignored={'gwen','guen','glen','glenn','hey','okay','listen','open','launch','start','click','on','the'}
            from dropdown_control import dropdown_intent
            dropdown=dropdown_intent(text)
            if dropdown:
                ignored.update(('dropdown','drop','down','arrow','menu'))
                if dropdown.casefold()=='font':ignored.update(('selection','selecting','selector','list','names','family'))
            content=[w for w in words if w.get('word','').lower().strip('.,!?') not in ignored]
            if any(float(w.get('probability',0))<.65 for w in content):
                return {'kind':'review','text':text,'raw':raw,'reason':'The target name was unclear. Repeat it or confirm the heard command.','confirmable':True}
        correction=correct(text,context)
        if correction.review:return {'kind':'review','text':correction.text,'raw':raw,'reason':correction.reason,'confirmable':False}
        text=correction.text
        from grid_commands import parse
        try:grid_command=parse(text,True) if context.get('grid_active') else parse(text,False)
        except ValueError:return {'kind':'review','text':text,'raw':raw,'reason':'That command sequence is unclear. Please repeat one action at a time.','confirmable':False}
        if not (is_action_request(text) or is_question(text) or grid_command):return {'kind':'review','text':text,'raw':raw,'reason':'Please say a complete command.','confirmable':False}
        if context.get('busy'):return {'kind':'review','text':text,'raw':raw,'reason':'Another task was running when you spoke. Repeat after it finishes.','confirmable':False}
        weak_code=correction.code and (confidence<self.config.get('review_confidence',.86) or any(float(w.get('probability',0))<.45 for w in result.get('words',())))
        self.armed_until=0
        if weak_code:return {'kind':'review','text':text,'raw':raw,'reason':'Please confirm the recognized letters/numbers or repeat them using NATO spelling.','confirmable':True,'code':correction.code}
        return {'kind':'command','text':text,'raw':raw,'code':correction.code}

def stale(context,current,code=''):
    """Speech uses the grid the speaker saw, not a later grid reusing its labels."""
    before=context.get('interaction') or {};after=current.get('interaction') or {}
    if before and after and (before.get('hwnd'),before.get('pid'))!=(after.get('hwnd'),after.get('pid')):return True
    if code and context.get('office')=='excel' and before.get('title')!=after.get('title'):return True
    if context.get('grid_active')!=current.get('grid_active'):return True
    if context.get('grid_active'):
        if context.get('grid_version')!=current.get('grid_version'):return True
        if code and context.get('label_keys',{}).get(code)!=current.get('label_keys',{}).get(code):return True
    return False
