"""Bound endpoint recognition to current-app vocabulary, without inventing text."""
import re
from selection_commands import range_command

def tokens(text):return re.findall(r"\w+(?:[-’']\w+)*",text.casefold())

def known(phrase,hints):
    from text_input import endpoint_spec
    phrase,_=endpoint_spec(phrase)
    pattern=r'(?<!\w)'+r'\s+'.join(re.escape(word) for word in phrase.casefold().split())+r'(?!\w)'
    return bool(phrase and re.search(pattern,hints.casefold()))

def aligned_words(packet):
    words=[word for word in packet.get('words',[]) if tokens(word.get('word',''))]
    return words if [token for word in words for token in tokens(word['word'])]==tokens(packet.get('text','')) and all(len(tokens(word['word']))==1 for word in words) else []

def fast_range(packet,context):
    hints=context.get('selection_hints','')
    text=re.sub(r'^(?:gwen|guen|glen|glenn)[,:]?\s+','',packet.get('text',''),flags=re.I)
    parsed=range_command(text,mode=True)
    if not hints or not parsed or '[unk]' in text or packet.get('confidence',0)<.86:return False
    if not all(known(parsed[side],hints) for side in ('start','end')):return False
    words=packet.get('words',[])
    return bool(words and min(word.get('probability',0) for word in words)>=.65)

def trim_unreliable_tail(packet,context):
    hints=(context or {}).get('selection_hints','');words=aligned_words(packet)
    parsed=range_command(packet.get('text',''),mode=True)
    if not hints or not words or not parsed:return
    # Never shorten an endpoint phrase already present in the current app.
    if known(parsed['end'],hints):return
    for count in range(len(words)-1,2,-1):
        tail=words[count:];prefix=' '.join(word['word'] for word in words[:count])
        candidate=range_command(prefix,mode=True)
        if not candidate or not all(known(candidate[side],hints) for side in ('start','end')):continue
        if min(word.get('probability',0) for word in tail)>=.35:continue
        if min(word.get('probability',0) for word in words[:count])<.65:continue
        packet.update(text=prefix,words=words[:count],confidence=sum(word['probability'] for word in words[:count])/count,
                      recognition_note='Removed an unsupported low-confidence tail after endpoints found in current-app vocabulary.')
        return

def endpoint_error(packet):
    parsed=range_command(packet.get('text',''),mode=True);words=aligned_words(packet)
    if not parsed or not words:return ''
    end_count=len(tokens(parsed['end']));start_count=len(tokens(parsed['start']))
    end_at=len(words)-end_count;start_at=end_at-1-start_count
    if start_at<0:return ''
    for side,part in (('start',words[start_at:end_at-1]),('end',words[end_at:])):
        if part and min(word.get('probability',0) for word in part)<.35:
            return 'The '+side+' words were unclear. Repeat the start and end words; nothing was selected.'
    return ''
