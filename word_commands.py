"""Explicit word commands preserve the user's quoted or spoken target."""
import re


def parse_word(text):
    patterns=(
        ('move_end',r'move\s+(?:the\s+)?(?:text\s+cursor|cursor|caret)\s+(?:to\s+(?:the\s+)?end\s+of\s+(?:the\s+)?word|after\s+(?:the\s+)?word)\s+(.+)'),
        ('move',r'move\s+(?:the\s+)?(?:text\s+cursor|cursor|caret)\s+(?:to\s+(?:the\s+)?(?:start|beginning)\s+of\s+(?:the\s+)?word|before\s+(?:the\s+)?word)\s+(.+)'),
        ('move',r'move\s+(?:the\s+)?(?:text\s+cursor|cursor|caret)\s+to\s+(?:the\s+)?(?:word\s+)?(.+)'),
        ('erase',r'(?:erase|delete|remove)\s+(?:the\s+)?word\s+(.+)'),
        ('select',r'select\s+(?:the\s+)?word\s+(.+)'))
    for action,pattern in patterns:
        match=re.fullmatch(pattern,text.strip().rstrip('.! '),re.I|re.S)
        if not match:continue
        word=match[1].strip()
        if action=='move' and word.casefold()=='word':return None
        if action=='move' and not re.search(r'\bto\s+(?:the\s+)?word\s+',text,re.I) and re.fullmatch(r'(?:the\s+)?(?:start|beginning|end) of (?:the |this |current )?line',word,re.I):return None
        if len(word)>=2 and (word[0],word[-1]) in (("\"","\""),("'","'"),('“','”')):
            word=word[1:-1].strip()
        if word:return {'kind':'word_action','action':action,'word':word}
    return None


def word_intent(text):
    text=re.sub(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)[,:]?\s*','',text.strip(),flags=re.I)
    for action,pattern in (('move_end',r'move\s+(?:the\s+)?(?:text\s+cursor|cursor|caret)\s+(?:to\s+(?:the\s+)?end\s+of\s+(?:the\s+)?word|after\s+(?:the\s+)?word)\b'),
                           ('move',r'move\s+(?:the\s+)?(?:text\s+cursor|cursor|caret)\s+(?:to|tool|too)\b'),
                           ('select',r'select\s+(?:the\s+)?word\b'),
                           ('erase',r'(?:erase|delete|remove)\s+(?:the\s+)?word\b')):
        if re.match(pattern,text,re.I):return action
    return None


def recover_word_packet(primary,general,hints=""):
    """A free-vocabulary decode must retain the same explicit word action."""
    expected=word_intent(primary.get('text',''))
    from selection_recognition import tokens,aligned_words,known
    anchors=[w for w in primary.get('words',[]) if tokens(w.get('word','')) and w['word'].casefold() not in ('gwen','guen','glen','glenn','hey','okay','ok')]
    required=2 if expected in ('move','move_end') else 1
    anchored=len(anchors)>=required and all(w.get('probability',0)>=.8 for w in anchors[:required])
    text=re.sub(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)[,:]?\s*','',general.get('text',''),flags=re.I)
    if expected=='move' and anchored and re.match(r'^move closer to ',text,re.I):
        text=re.sub(r'^move closer to ','move cursor to ',text,flags=re.I)
        updated=[dict(w,word='cursor') if w.get('word','').casefold()=='closer' else dict(w) for w in general.get('words',[])]
        general={**general,'text':text,'words':updated}
    first=re.split(r'(?<=[.!?])\s+',text,maxsplit=1)[0]
    first_parsed=parse_word(first)
    aligned=aligned_words(general);count=len(tokens(first))
    if (first!=text and hints and first_parsed and known(first_parsed['word'],hints) and aligned
        and any(w.get('probability',0)<.35 for w in aligned[count:])):
        kept=aligned[:count];text=first
        general={**general,'text':first,'words':kept,'confidence':sum(w['probability'] for w in kept)/len(kept)}

    parsed=parse_word(text);words=general.get('words',[])
    from selection_recognition import aligned_words,tokens
    aligned=aligned_words(general)
    count=len(tokens(parsed['word'])) if parsed else 0
    target=aligned[-count:] if count and len(aligned)>=count else []
    # Function words are not the target. Weak 'to' must not veto a clearly
    # heard word, while weak target words still require a repeat.
    content=[w for w in aligned[:-count] if w['word'].casefold().strip('.,!?') not in {'to','the','word'}] if target else []
    if (not expected or not parsed or parsed['action']!=expected or '[unk]' in text
        or general.get('confidence',0)<.72 or not target
        or min(w.get('probability',0) for w in target)<.65
        or (not anchored and any(w.get('probability',0)<.65 for w in content))):return primary
    return {**general,'primary_text':primary.get('text'),'primary_confidence':primary.get('confidence',0),
            'recognition_note':'Named-word target decoded with open vocabulary; command action preserved.'}
