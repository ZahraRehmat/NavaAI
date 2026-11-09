"""Exact mode-control aliases shared by recognition and voice routing."""
DICTATION_ON={'type','start dictation','dictation on','turn on dictation','enable dictation','start typing','typing on','typing mode','start typing mode'}
DICTATION_OFF={'stop dictation','dictation off','turn off dictation','disable dictation','finish typing','stop typing','end dictation','end typing','typing off'}


def compact_phrases():
    from selection_commands import ON,OFF
    phrases=DICTATION_ON|DICTATION_OFF|ON|OFF|{
        'listen','start listening','listen continuously','sleep','go to sleep','stop listening',
        'stop','cancel','stop now','cancel task','show chat','hide chat','microphone off','mute microphone',
        'press enter','hit enter','press return','press tab','press escape','press backspace',
        'copy','copy it','paste','paste it','select all','undo','redo',
        'punctuate it','punctuate this','punctuate the text','backspace','back space','erase it','erase that','delete last word','delete the last word','paste here',
        'add punctuation','add punctuation to it','erase last word','erase the last word','copy to clipboard','copy it to clipboard','paste the copied data','paste the stuff','paste the copied text','paste it here','paste it in this field',
        'grid on','grid off','open grid','close grid','turn on grid','turn off grid',
        'new tab','open new tab','close tab','close this tab','close current tab','next tab','previous tab','select tab two','select second tab',
        'make a table','create a table','make table from selected cells','make a table from selected cells',
        'create a table from selected cells','make selected cells into a table','format as table',
        'turn on','turn off','switch on','switch off'}
    return sorted(phrases|{'gwen '+p for p in phrases})
