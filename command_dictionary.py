"""Read-only command help. This catalog never supplies recognition vocabulary."""
import re
from dataclasses import dataclass

ALIASES={
 'show commands':'show','commands on':'show','turn on commands':'show',
 'show dictionary':'show','open dictionary':'show','show command overlay':'show',
 'hide commands':'hide','commands off':'hide','turn off commands':'hide',
 'hide dictionary':'hide','close dictionary':'hide','hide command overlay':'hide',
 'open full dictionary':'master','show full dictionary':'master','open master dictionary':'master',
 'hide full dictionary':'close_master','close full dictionary':'close_master',
 'next commands page':'next','previous commands page':'previous',
 'commands more transparent':'lighter','commands less transparent':'darker',
 'dictionary scroll down':'down','dictionary scroll up':'up',
}

def intent(text):
    text=re.sub(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn)[,:]?\s+','',text.strip(),flags=re.I)
    text=re.sub(r'^please\s+','',text,flags=re.I).strip().rstrip('.!?')
    action=ALIASES.get(text.casefold())
    if action:return {'action':action}
    match=re.fullmatch(r'(?:search|find)\s+(?:commands|dictionary)(?:\s+for)?\s+(.+)',text,re.I)
    if match:return {'action':'search','query':match[1].strip()}
    return None

@dataclass(frozen=True)
class Entry:
    scope:str
    section:str
    command:str
    description:str

ENTRIES=[]
def group(scope,section,rows):
    for command,description in rows:ENTRIES.append(Entry(scope,section,command,description))

group('general','Windows & apps',[
 ('open Notepad','Open or switch to a named app'),('switch to Chrome','Bring an open app forward'),
 ('close this app','Request closing the active app'),('close Word','Request closing a named app'),
 ('force close Notepad','Force-stop a named app; unsaved work can be lost'),
 ('minimize this app','Minimize the active window'),('maximize this app','Maximize the active window'),
 ('restore this app','Restore the active window size'),('open FYP folder','Find and open a folder'),
 ('open README.md','Find and open a file; use your actual name'),('click on Save','Choose an observed named control'),
 ('open dropdown','Mark the available dropdown choices'),('scroll down','Scroll the current target'),
 ('scroll up','Scroll upward'),('press escape','Dismiss a menu or dialog'),('stop','Stop the current action'),
])
group('general','Keyboard & clipboard',[
 ('copy it','Copy selected text'),('paste','Paste the clipboard into the focused field'),('cut it','Cut selected text'),
 ('select all','Select all in the focused control'),('undo','Undo the last edit'),('redo','Redo an edit'),
 ('press enter','Press Enter; the app decides its meaning'),('press tab','Move to the next field'),
 ('press control s','Send the app save shortcut'),('type hello','Type literal text after the word type'),
])
group('dictation','Voice typing',[
 ('dictation on','Start speaking text into the focused field'),('dictation stop','Stop voice typing'),
 ('press enter','Press Enter, including a newline or Send'),('erase it','Delete selection or the last word'),
 ('erase letter','Delete one character'),('punctuate it','Add punctuation to the current text'),
 ('copy it','Copy selected text'),('paste','Paste copied data'),('undo','Undo the last edit'),
 ('select word example','Select the named word; replace example'),('erase word example','Delete the named word'),
 ('move cursor to example','Move the caret before a named word'),('move cursor after word example','Move the caret after a named word'),
 ('move cursor forward','Move one character forward'),('move cursor backward a word','Move one word backward'),
 ('go to end of line','Move the caret to the line end'),('go to start of line','Move the caret to the line start'),
 ('type press enter','Type the words literally instead of pressing Enter'),
])
group('selection','Text selection',[
 ('selection mode','Start selection by spoken endpoints'),('Islamabad to Karachi','Select and copy text between your endpoint words'),
 ('first work to last testing','Disambiguate repeated endpoint words'),('select word example','Select a single named word'),
 ('copy it','Copy the current selection'),('paste','Paste selected/copied data into a focused field'),
 ('stop selection','Return to normal commands'),
])
group('grid','Smart grid mouse',[
 ('open grid','Show adaptive labels over controls'),('grid off','Hide the grid and release the mouse'),
 ('A','Click the displayed label A; use your label'),('move to A','Move the pointer without clicking'),
 ('double click A','Open the item at a displayed label'),('right click A','Open that target’s context menu'),
 ('scroll down on A','Scroll downward over a labelled target'),('scroll up on A','Scroll upward over a labelled target'),
 ('hold A','Hold the mouse at a label'),('drag A to F','Drag between two displayed labels'),
 ('release','Release held mouse buttons'),('move left 10 pixels','Nudge the mouse'),
 ('refresh grid','Refresh the observed targets'),('open A dropdown','Expand the labelled menu arrow'),
])
group('browser','Chrome / Edge',[
 ('open youtube on new tab','Open a website in a new tab'),('open new tab','Create a blank browser tab'),
 ('close this tab','Close the selected tab'),('next tab','Switch to the next tab'),('previous tab','Switch to the previous tab'),
 ('switch to tab YouTube','Select a tab by its title'),('select second tab','Select a numbered tab'),
 ('open google.com','Navigate the selected browser'),('search for weather','Search using the current browser'),
 ('click on Sign in','Choose a visible page control by name'),('go back','Go back in browser history'),('go forward','Go forward in history'),
])
group('youtube','YouTube playback',[
 ('pause video','Pause the current video'),('resume video','Resume playback'),
 ('forward five seconds','Seek forward 5 seconds'),('rewind five seconds','Seek backward 5 seconds'),
 ('forward ten seconds','Seek forward 10 seconds'),('rewind ten seconds','Seek backward 10 seconds'),
 ('play next video','Request the next video'),('play previous video','Request previous video; usually needs a playlist'),
 ('skip ad','Click Skip when YouTube makes it available'),('search cats on youtube','Search YouTube for your own words'),
])
group('notepad','Notepad editor',[
 ('dictation on','Speak into the focused Notepad text'),('selection mode','Select text by its start and end words'),
 ('select word example','Select a word in this editor'),('erase word example','Erase a word in this editor'),
 ('move cursor after word example','Place the caret after a word'),('press enter','Start the next line'),
 ('undo','Undo the previous edit'),('paste','Paste into the editor'),('press control s','Open Notepad’s Save action'),
 ('open dropdown','Mark available menus or dropdowns'),
])
group('explorer','Files & Desktop',[
 ('open FYP folder','Open a folder using your own name'),('open first folder','Open an ordinal folder in the current location'),
 ('open example.pdf','Open a file using its name'),('double click A','Open a file through its grid label'),
 ('go back','Go back to the previous folder'),('go forward','Go forward to a visited folder'),
 ('go up','Open the parent folder'),('go home','Open Explorer Home'),('open dropdown','Mark available dropdown controls'),
])
group('whatsapp','WhatsApp',[
 ('open WhatsApp','Open or focus WhatsApp'),('open Alex chat','Find a chat using your actual contact name'),
 ('click on Search','Choose the visible Search control'),('dictation on','Dictate into the focused message box'),
 ('press enter','Use Enter; it may send the message'),('open grid','Label accessible chat and message controls'),
])
group('store','Microsoft Store',[
 ('open store','Open Microsoft Store'),('search Instagram on store','Search Store for your own app name'),
 ('click on Netflix','Choose a visible app result'),('click on Get','Click the observed Get button'),
 ('open grid','Label visible Store controls'),
])
group('taskmanager','Task Manager',[
 ('open task manager','Open Task Manager'),('search WhatsApp','Search the Task Manager process list'),
 ('open grid','Label the visible process controls'),
])
for app in ('word','excel','powerpoint'):
    group(app,'Font, paragraph & tables',[
      ('bold','Apply bold to the selection'),('italic','Apply italic to the selection'),('underline','Underline the selection'),
      ('set font size to 16','Set the selection’s point size'),('increase font','Increase selected text size'),('decrease font','Decrease selected text size'),('set font to Arial','Change the font family'),
      ('make text red','Set the selected text colour'),('set fill color yellow','Change the selection’s background'),('set table fill blue','Fill a selected table'),('remove bullets','Remove list formatting'),('align center','Centre the selection'),
      ('add bullets','Make the selection a bulleted list'),('add numbered list','Make a numbered list'),
      ('open font selection dropdown','Expand the font-family menu'),('open font size dropdown','Expand the point-size menu'),
      ('remove table','Remove table structure; preserve text/data'),('delete table','Delete the table and its contents'),
      ('add row to table','Insert a table row'),('add column to table','Insert a table column'),
      ('save','Save the current Office document'),('set zoom to 120','Set the view zoom percentage'),
    ])
group('word','Word document',[
 ('new document','Create a blank document'),('insert table 3 by 4','Insert a visible 3-row, 4-column table'),
 ('set table borders blue','Change visible table lines to blue'),('highlight yellow','Highlight selected text'),
 ('apply heading 1','Apply a heading style'),('insert page break','Insert a page break'),
 ('set page landscape','Change page orientation'),('increase indent','Indent the selected paragraph'),('decrease indent','Reduce paragraph indentation'),
])
group('excel','Excel cells & sheets',[
 ('select G6','Select a cell by its native address'),('select from B2 to N6','Select a cell range'),
 ('edit J7','Open a cell for editing'),('copy cell A9','Copy a cell’s contents'),('paste copied data in cell K10','Paste at a cell address'),
 ('make a table','Convert the selected range into an Excel table'),('make B2:N6 into a table','Create a table from a named range'),
 ('open cell dropdown','Expand the current cell’s available list'),('clear cells B2:N6','Clear values without shifting cells'),
 ('delete cells B2:N6 shift up','Delete cells and shift the remaining cells up'),
 ('set table borders blue','Set table line colour'),('autofit columns','Fit column widths to data'),
 ('set column width to 20','Set the selected column width'),('set row height to 24','Set the selected row height'),
 ('merge cells','Merge the selected cells'),('unmerge cells','Unmerge the selection'),('wrap text','Wrap text within cells'),
 ('freeze panes','Freeze at the active cell'),('sort A1:D10 ascending','Sort a selected/addressed range'),
 ('set formula A1 to =SUM(B1:B5)','Enter a formula'),('format A1 as currency','Set a cell number format'),
 ('add sheet named Budget','Add a worksheet'),('select sheet Budget','Switch to a sheet'),('rename sheet Budget to Costs','Rename a worksheet'),
])
group('powerpoint','PowerPoint slides',[
 ('new presentation','Create a presentation'),('add slide','Insert a new slide'),('select slide 2','Switch to a numbered slide'),
 ('duplicate slide 2','Duplicate a slide'),('insert table 3 by 4','Insert a table on the slide'),
 ('add text box: Hello','Add a text box with your text'),
])
group('help','Command help',[
 ('show commands','Show this adaptive transparent overlay'),('hide commands','Hide command help'),
 ('open full dictionary','Open the searchable master dictionary'),('search dictionary for font','Find commands using your own keyword'),
 ('next commands page','Show more contextual commands'),('previous commands page','Go back through contextual commands'),
 ('commands more transparent','Make the overlay more see-through'),('commands less transparent','Make the overlay easier to read'),
 ('dictionary scroll down','Scroll the master dictionary'),('close full dictionary','Close the full dictionary'),
])
group('power','Gwen modes',[
 ('gwen turn on','Activate the assistant and microphone'),('gwen turn off','Return to wake-listener standby'),
 ('show chat','Show the typed-command panel'),('hide chat','Hide the typed-command panel'),('microphone off','Release the microphone; F9 turns it back on'),
])

def app_scopes(target):
    target=target or {};title=target.get('title','');low=title.casefold();kind=target.get('class_name','')
    from office_control import office_kind
    office=office_kind(target)
    if office:return [office]
    from routing import browser_channel
    if browser_channel(target):return (['youtube'] if re.search(r'\byoutube\b',low) else [])+['browser']
    if kind in ('CabinetWClass','ExploreWClass','Progman','WorkerW'):return ['explorer']
    for scope,pattern in [('notepad',r'notepad$'),('whatsapp',r'whats\s*app$'),('store',r'(?:microsoft |ms )?store$'),('taskmanager',r'task manager$')]:
        if re.search(pattern,low):return [scope]
    return []

def contextual(state):
    if not state.get('active',True):return []
    scopes=app_scopes(state.get('target'))
    scopes+=['dictation'] if state.get('dictating') else []
    scopes+=['selection'] if state.get('selecting') else []
    if state.get('grid'):scopes+=['grid']
    scopes+=['general']
    result=[];seen=set()
    for scope in scopes:
        for row in ENTRIES:
            if state.get('dictating') and row.command=='dictation on':continue
            if state.get('selecting') and row.command=='selection mode':continue
            if row.scope==scope and row.command not in seen:
                result.append(row);seen.add(row.command)
    return result

def search(query='',scope='All'):
    words=re.findall(r'\w+',query.casefold())
    return [row for row in ENTRIES if (scope=='All' or row.scope==scope) and all(word in (row.command+' '+row.description+' '+row.scope+' '+row.section).casefold() for word in words)]
