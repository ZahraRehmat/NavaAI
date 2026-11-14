"""Exact mode-control aliases shared by recognition and voice routing."""
DICTATION_ON={'dictation start','type','start dictation','dictation on','turn on dictation','enable dictation','start typing','typing on','typing mode','start typing mode'}
DICTATION_OFF={'dictation stop','stop dictation','dictation off','turn off dictation','disable dictation','finish typing','stop typing','end dictation','end typing','typing off'}


def compact_phrases():
    from selection_commands import ON,OFF
    phrases=DICTATION_ON|DICTATION_OFF|ON|OFF|{
        'listen','start listening','listen continuously','sleep','go to sleep','stop listening',
        'stop','cancel','stop now','cancel task','show chat','hide chat','microphone off','mute microphone',
        'press enter','hit enter','press return','press tab','press escape','press backspace',
        'copy','copy it','paste','paste it','select all','undo','redo',
        'control z','ctrl z','control y','control c','control v','control x','undo last action','redo last action',
        'erase letter','erase last letter','erase character','delete last character','erase alphabet','control plus z',
        'move cursor forward','move cursor backward','move cursor forward a word','move cursor backward a word','move cursor up','move cursor down','move cursor left','move cursor right','previous line','move to next line',
        'go to start of line','go to end of line',
        'punctuate it','punctuate this','punctuate the text','backspace','back space','erase it','erase that','delete last word','delete the last word','paste here',
        'add punctuation','add punctuation to it','erase last word','erase the last word','copy to clipboard','copy it to clipboard','paste the copied data','paste the stuff','paste the copied text','paste it here','paste it in this field',
        'grid on','grid off','open grid','close grid','turn on grid','turn off grid',
        'skip ad','skip this ad','skip the ad','skip ads',
        'pause','resume','pause video','pause the video','pause youtube','resume video','resume youtube','play video','unpause video',
        'forward five seconds','forward ten seconds','rewind five seconds','rewind ten seconds','play next video','play previous video',
        'new tab','open new tab','close tab','close this tab','close current tab','next tab','previous tab','select tab two','select second tab',
        'make a table','create a table','make table from selected cells','make a table from selected cells',
        'create a table from selected cells','make selected cells into a table','format as table',
        'turn on','turn off','switch on','switch off'}
    from command_dictionary import ALIASES
    phrases.update(ALIASES)
    return sorted(phrases|{'nava '+p for p in phrases})
