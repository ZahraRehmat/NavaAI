"""Offline index of Microsoft's published Fluent control identifiers."""
import json,re,zipfile,xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from rapidfuzz.fuzz import WRatio,token_set_ratio

ROOT=Path(__file__).resolve().parent/'data'/'office_controls'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
EXECUTABLE={'button','toggleButton','splitButton'}

@lru_cache(maxsize=3)
def controls(kind):
    source=ROOT/(kind+'controls.xlsx')
    if not source.exists():return []
    with zipfile.ZipFile(source) as archive:
        strings=[''.join(t.itertext()) for t in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        rows=ET.fromstring(archive.read('xl/worksheets/sheet1.xml')).findall('.//s:sheetData/s:row',NS)
        result={}
        for row in rows[1:]:
            cells={}
            for cell in row.findall('s:c',NS):
                value=cell.find('s:v',NS)
                if value is not None:cells[re.sub(r'\d','',cell.attrib['r'])]=strings[int(value.text)] if cell.attrib.get('t')=='s' else value.text
            name=cells.get('A','')
            if not name:continue
            item=result.setdefault(name,{'id':name,'type':cells.get('B',''),'contexts':[]})
            context=' / '.join(cells[k] for k in ('D','E') if cells.get(k))
            if context and context not in item['contexts']:item['contexts'].append(context)
        return list(result.values())

def words(value):return re.sub(r'([a-z])([A-Z])',r'\1 \2',value).replace('_',' ').lower()

def search_controls(kind,query,limit=12):
    query=re.sub(r'^(?:click|open|show|execute|run|apply)\s+','',query.strip(),flags=re.I)
    ranked=[]
    for row in controls(kind):
        label=words(row['id'])
        score=max(WRatio(query,label),token_set_ratio(query,label))
        if query.casefold()==row['id'].casefold():score=110
        if score>=58:ranked.append((score,row))
    ranked.sort(key=lambda x:-x[0])
    return [dict(row,score=round(score,1),executable_type=row['type'] in EXECUTABLE) for score,row in ranked[:limit]]

def summary():
    return {kind:{'indexed_controls':len(controls(kind)),'executable_button_types':sum(c['type'] in EXECUTABLE for c in controls(kind))} for kind in ('word','excel','powerpoint')}

def execute_control(app,kind,identifier):
    item=next((c for c in controls(kind) if c['id']==identifier),None)
    if item is None:raise ValueError('That command ID is not in the published '+kind+' catalog.')
    if item['type'] not in EXECUTABLE:raise ValueError('This is a '+item['type']+' control. Use its parameterized native tool or open its dialog; ExecuteMso cannot execute that control type.')
    # These categories require dedicated flows with their own explicit scope.
    if re.search(r'macro|visualbasic|trustcenter|security|signIn|account|send|publish|share|externaldata|connection',identifier,re.I):raise ValueError('This command needs its dedicated account, sharing, macro or security workflow.')
    if not app.CommandBars.GetEnabledMso(identifier):raise ValueError('Office reports that this command is disabled in the current selection/view.')
    app.CommandBars.ExecuteMso(identifier)
    return 'Invoked Office command '+identifier+'. If it opened a picker/dialog, that step still needs to be completed.'

if __name__=='__main__':
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/'index-summary.json').write_text(json.dumps(summary(),indent=2),encoding='utf8')
    print(json.dumps(summary()))
