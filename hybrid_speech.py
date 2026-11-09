"""Offline general English decoding plus fast contextual grid-code recognition."""
import re,time


class HybridRecognizer:
    def __init__(self,log=lambda _:None,config=None):
        from vosk_speech import VoskRecognizer
        from speech import LocalRecognizer
        config=config or {}
        self.commands=VoskRecognizer(log,{**config,'engine':'vosk'})
        self.english=LocalRecognizer(log,{**config,'engine':'whisper','model':config.get('dictation_model','models/whisper-base.en')})

    def transcribe(self,audio,context=None):return self.transcribe_result(audio,context)['text']

    def transcribe_result(self,audio,context=None):
        from command_voice import power_intent
        from direct_commands import parse_direct
        context=context or {};started=time.monotonic()
        command=self.commands.transcribe_result(audio,{**context,'dictation':False})
        # A chooser temporarily supersedes dictation/selection. Never send short
        # letter answers through the free-sentence decoder or control rescue.
        if context.get('dialog_active'):return command
        if context.get('assistant_active') is not False:
            from voice_controls import compact_phrases
            if command['text'] not in compact_phrases() or command.get('confidence',0)<.86:
                compact=self.commands.transcribe_controls(audio)
                command=self.prefer_control(command,compact)
        text=re.sub(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)[,:]?\s*','',command['text'],flags=re.I)
        low=text.strip().lower().rstrip('.! ')
        from selection_commands import ON,OFF
        from voice_controls import DICTATION_ON,DICTATION_OFF
        control=low in DICTATION_ON|DICTATION_OFF|{'listen','start listening','sleep','stop','cancel','show chat','hide chat','microphone off','mute microphone','yes','no','confirm','confirm command'}
        ready=command.get('confidence',0)>=.72 and '[unk]' not in command['text']
        if context.get('assistant_active') is False:return command
        if power_intent(command['text']) and command.get('confidence',0)>=.86:return command
        if ready and low in ON|OFF:return command
        if ready and context.get('office')=='excel':
            from excel_commands import parse as parse_excel
            if parse_excel(text):return command
        if context.get('selection'):
            edit=parse_direct(text)
            if ready and ((edit and edit['kind'] in ('keys','punctuate')) or control):return command
            result=self.english.transcribe_result(audio,context)
            self.selection_sentence(result)
            result['backend']='whisper-base.en';result['seconds']=time.monotonic()-started
            return result
        if context.get('dictation') and ready:
            edit=parse_direct(text)
            known={'ctrl','alt','shift','enter','tab','esc','backspace','delete','space','up','down','left','right','home','end','pageup','pagedown','insert'}
            safe_keys=edit and edit['kind']=='keys' and all(k in known or re.fullmatch(r'[a-z0-9]|f(?:[1-9]|1\d|2[0-4])',k) for k in edit['keys'])
            if control or safe_keys or (edit and edit['kind'] in ('font_delta','punctuate')):return command
        if context.get('dictation'):
            result=self.english.transcribe_result(audio,context)
            from direct_commands import parse_direct
            edit=parse_direct(result['text'])
            control=result['text'].lower().strip().rstrip('.! ')
            if (edit and edit['kind'] in ('keys','font_delta','select_text','punctuate')) or control in ('stop dictation','finish typing','end dictation','stop','cancel'):
                self.consensus(command,result)
        else:
            payload=bool(re.match(r'^(?:listen\s+)?(?:type|write|dictate|select from|select and copy|selection|copy from)\s+',text,re.I))
            # Ordinary commands always remain on their command recognizer.
            if not payload:return command
            result=self.english.transcribe_result(audio,context)
            # Correct only a wake-name spelling independently heard by Vosk.
            if re.match(r'^(?:gwen|guen|glen|glenn)\b',command['text'],re.I):
                result['text']=re.sub(r'^(?:when|glen|glenn|guen)\b','Gwen',result['text'],flags=re.I)
            self.consensus(command,result)
            if result.get('confidence',0)<.72 and command.get('confidence',0)>=.86 and '[unk]' not in command['text']:
                candidate=parse_direct(re.sub(r'^(?:listen|start listening)\s+','',text,flags=re.I))
                if candidate and candidate['kind']=='type':return command
        result['backend']='whisper-base.en';result['seconds']=time.monotonic()-started
        return result

    @staticmethod
    def prefer_control(primary,compact):
        from voice_controls import compact_phrases
        if not isinstance(compact,dict) or compact.get('text') not in compact_phrases():return primary
        words=compact.get('words',[])
        if compact.get('confidence',0)<.9 or not words or min(w.get('probability',0) for w in words)<.65:return primary
        filler={'gwen','guen','glen','glenn','hey','please','on','off','the','a','to','it','this','that','here','me','my'}
        before=set(re.findall(r'[a-z]+',primary.get('text','').lower()))-filler
        after=set(re.findall(r'[a-z]+',compact['text'].lower()))-filler
        if not before.intersection(after):return primary
        return {**compact,'primary_text':primary['text'],'primary_confidence':primary.get('confidence',0)}

    @staticmethod
    def selection_sentence(result):
        """One range per utterance; do not append a decoder's trailing sentence."""
        from selection_commands import range_command
        first=re.split(r'(?<=[.!?])\s+',result['text'].strip(),maxsplit=1)[0]
        if first==result['text'].strip() or not range_command(first,mode=True):return
        words=result.get('words',[]);count=len(re.findall(r'\w+(?:[’\'-]\w+)*',first))
        spoken=[w for w in words if re.search(r'\w',w.get('word',''))][:count]
        if len(spoken)!=count:return
        result['text']=first;result['words']=spoken
        result['confidence']=sum(w['probability'] for w in spoken)/count
        result['recognition_note']='Selection mode accepts one complete range sentence per utterance.'

    @staticmethod
    def consensus(command,result):
        from direct_commands import parse_direct
        def payload(value):return re.sub(r'^(?:gwen|guen|glen|glenn)[,:]?\s*','',value.strip(),flags=re.I)
        a=parse_direct(payload(command['text']));b=parse_direct(payload(result['text']))
        # No confidence transfer across different actions or dictated content.
        if a and a==b and a['kind'] in ('keys','font_delta','select_text','punctuate'):
            result['confidence']=max(result['confidence'],command['confidence']);result['consensus']=True
        controls={'listen','start listening','sleep','stop','cancel','type','start dictation','typing mode','stop dictation','finish typing','end dictation'}
        ca=payload(command['text']).lower().rstrip('.! ');cb=payload(result['text']).lower().rstrip('.! ')
        if ca==cb and ca in controls:
            result['confidence']=max(result['confidence'],command['confidence']);result['consensus']=True
