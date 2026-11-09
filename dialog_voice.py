"""Exact, bounded voice answers for the resident chooser."""
import re
from speech_context import codes,number_words


def answer(text,count,kind='choice',labels=None,numbers=None):
    text=re.sub(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)[,:]?\s*','',text.strip(),flags=re.I)
    text=text.lower().rstrip('.!? ').strip()
    if text in ('cancel','cancel selection','cancel choice','none','none of these','reject'):
        return 'cancel'
    if kind=='confirm':
        return 0 if text in ('yes','confirm','confirm command') else 1 if text=='no' else None
    if text=='no':return 'cancel'
    if numbers:
        numeric=re.sub(r'^(?:option|choose|select|click|press|window|number)\s+','',text)
        numeric=number_words(numeric)
        if numeric.isdigit() and int(numeric) in numbers:return list(numbers).index(int(numeric))
    value=re.sub(r'^(?:option|choose|select|click|press|letter)\s+','',text)
    labels=list(labels) if labels is not None else [chr(65+i) for i in range(count)]
    matches=[v for v in codes(value) if v in labels]
    return labels.index(matches[0]) if len(matches)==1 and matches[0] in labels else None


def grammar(context):
    kind=context.get('dialog_kind','choice');count=min(26,max(0,context.get('dialog_count',26)))
    phrases={'cancel','cancel choice','cancel selection','none','none of these','reject','no',
             'stop','stop now','cancel task','gwen turn on','gwen turn off'}
    if kind=='confirm':phrases.update(('yes','confirm','confirm command'))
    else:
        # Canonical letters plus NATO spellings avoid competing homophones.
        nato='alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu'.split()
        labels=context.get('dialog_labels',[chr(65+i) for i in range(count)])
        for label in labels:
            for name in (' '.join(label.lower()),' '.join(nato[ord(ch)-65] for ch in label)):
                for prefix in ('','option ','choose ','select ','click ','press ','letter '):
                    phrases.add(prefix+name)
        names='one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty twenty-one twenty-two twenty-three twenty-four twenty-five twenty-six'.split()
        for number in context.get('dialog_numbers',[]):
            if isinstance(number,int) and 1<=number<=26:
                spoken=names[number-1].replace('-',' ')
                for prefix in ('','option ','choose ','select ','click ','press ','window ','number '):phrases.add(prefix+spoken)
    return sorted(phrases|{'gwen '+p for p in phrases if not p.startswith('gwen ')})+['[unk]']
