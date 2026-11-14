"""Editor-scoped vocabulary for recognizing spoken word targets."""
import re


def read_editor(target):
    from text_input import FocusedText
    access=FocusedText(target);access.check()
    document=access.pattern.DocumentRange
    readonly=document.GetAttributeValue(40015)
    if not isinstance(readonly,(bool,int)) or readonly!=0:return ''
    visible=access.pattern.GetVisibleRanges();parts=[]
    for index in range(min(32,visible.Length)):
        parts.append(visible.GetElement(index).GetText(1500))
        if sum(map(len,parts))>=5000:break
    access.check()
    return {'text':'\n'.join(parts)[:5000],'identity':list(access.identity)}


def expected_action(packet,context):
    from word_commands import word_intent
    text=packet.get('text','')
    expected=word_intent(text)
    if expected:return expected
    if not context.get('grid_active') and context.get('word_hints') and re.fullmatch(r'(?:nava\s+)?select\s+(?!(?:all|from|cell|tab|text|and)\b).+',text,re.I):return 'select'
    return None


def phrases(context,action,model):
    words=list(dict.fromkeys(re.findall(r"[a-z]+(?:'[a-z]+)?",context.get('word_hints','').casefold())))[:200]
    words=[w for w in words if model.vosk_model_find_word(w)>=0]
    prefixes={'move_end':('move cursor to end of word ','move cursor to the end of word ','move cursor after word '),'move':('move cursor to ','move cursor to word '),
              'select':('select word ','select '),'erase':('erase word ','delete word ','remove word ')}
    return [wake+prefix+word for word in words for prefix in prefixes.get(action,()) for wake in ('','nava ')]


def contextual_candidate(primary,candidate,context):
    from word_commands import parse_word,recover_word_packet
    from selection_recognition import known
    action=expected_action(primary,context)
    if not action:return primary
    text=candidate.get('text','').strip()
    # Short select TARGET is a word command only inside an observed editor;
    # grid labels and application controls keep their normal interpretation.
    short=re.fullmatch(r'((?:nava\s+)?select)\s+(?!word\b)(.+)',text,re.I)
    if action=='select' and short and known(short[2],context.get('word_hints','')):
        words=list(candidate.get('words',[]));at=1 if not text.lower().startswith('nava ') else 2
        words.insert(at,{'word':'word','probability':1})
        candidate={**candidate,'text':short[1]+' word '+short[2],'words':words}
    parsed=parse_word(re.sub(r'^nava\s+','',candidate.get('text',''),flags=re.I))
    if not parsed or not known(parsed['word'],context.get('word_hints','')):return primary
    # Give the existing recovery guard a canonical primary action when the
    # short select syntax was observed in an editable field.
    anchor=primary if expected_action(primary,{}) else {**primary,'text':'select word'}
    recovered=recover_word_packet(anchor,candidate)
    if recovered is anchor:return primary
    return {**recovered,'primary_text':primary.get('text'),'primary_confidence':primary.get('confidence',0)}
