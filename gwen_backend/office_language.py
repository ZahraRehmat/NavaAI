"""Natural Office requests -> typed operations; unfamiliar wording uses the local model."""
import re
from office_tools import TOOL_APPS,DESCRIPTIONS,clean_target

COLORS='light blue|dark blue|light green|dark green|light gray|dark gray|orange|purple|yellow|magenta|violet|crimson|maroon|silver|black|white|green|blue|cyan|pink|gray|grey|red|navy|teal|gold'
CELL=r'\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?'
def operation(action,target='',value='',**extra):return dict(action=action,target=target,value=str(value),**extra)

def target_from(text):
    cell=re.search(r'\b('+CELL+r')\b',text,re.I)
    if cell:return cell[1].upper()
    quoted=re.search(r'["\'](.+?)["\']',text)
    if quoted:return quoted[1]
    if re.search(r'\b(?:selected|selection|it|this|these)\b',text,re.I):return ''
    if re.search(r'\b(?:all text|whole document|entire document|all slides|whole presentation)\b',text,re.I):return re.search(r'\b(all text|whole document|entire document|all slides|whole presentation)\b',text,re.I)[1]
    match=re.search(r'\b(?:of|for)\s+(.+?)\s+to\b',text,re.I)
    if match:return clean_target(match[1])
    match=re.match(r'(?:make|set|change|turn)\s+(?:the\s+)?(.+?)\s+(?:font|text|size|colou?r|bold|italic|underline|bigger|smaller|larger|'+COLORS+r')\b',text,re.I)
    if match:return clean_target(match[1])
    return ''

def parse_extended(task):
    raw=re.sub(r'^\s*(?:please\s+|can you\s+|could you\s+)','',task,flags=re.I).strip().rstrip('.!')
    low=raw.casefold();target=target_from(raw)
    if re.match(r'^(?:type|write|enter|put)\s+',low) and not re.match(r'^(?:enter|put)\s+(?:the\s+)?formula\b',low):return None
    if re.search(r'\bthen\b',low):return None
    table_target=re.search(r'\btable\s*(\d+)\b',low)
    chosen_table='table '+table_target[1] if table_target else 'table'
    if re.search(r'\btable\b',low) and re.search(r'\b(?:outline|borders?|lines?)\b',low):
        shade=re.search(r'(#[0-9a-f]{6}|\b(?:'+COLORS+r')\b)',low)
        if shade:return operation('table_borders',chosen_table,shade[1])
    if re.fullmatch(r'(?:delete|erase)\s+(?:(?:this|the|selected|current)\s+)?table(?:\s*\d+)?(?:\s+(?:and|with)\s+(?:its\s+)?(?:contents|data|text))?',low) or re.fullmatch(r'remove\s+(?:the\s+)?table\s+and\s+(?:its\s+)?(?:contents|data|text)',low):
        return operation('table_delete',chosen_table)
    match=re.fullmatch(r'(?:delete|clear|erase|empty|remove)\s+(?:(?:the|these|selected|current)\s+)?(?:(?:contents|content|values|data)\s+(?:of|from|in)\s+)?(?:(?:cell|cells|range)\s*)?('+CELL+r'|selection|cells|cell)(?:\s+(?:contents|content|values|data))?(?:\s+(?:and\s+)?shift\s+(up|left))?',raw,re.I)
    if match:return operation('cells_delete' if match[2] else 'cells_clear','' if match[1].lower() in ('selection','cells','cell') else match[1].upper(),match[2].lower() if match[2] else '')
    if re.search(r'\bhighlight\b',low):
        shade=re.search(r'\b('+COLORS+r'|none)\b',low)
        if shade:return operation('highlight',target,shade[1])
    match=re.fullmatch(r'(?:select|go to|goto|choose|click)\s+(?:(?:the\s+)?(?:cell|range|cells)\s+)?('+CELL+r')',raw,re.I)
    if match:return operation('select',match[1].upper())
    if re.search(r'\b(?:font|text|lettering|letters|size)\b',low) or re.match(r'(?:make|increase|decrease|enlarge|shrink)\b',low):
        steps=[]
        size=re.search(r'(?:font\s*size|size|to)\s*(?:to\s+)?(\d+(?:\.\d+)?)\s*(?:pt|points?)?\b',low)
        if size and not re.search(r'\b(?:colou?r|fill|background)\b',low):steps.append(operation('font_size',target,size[1]))
        if not size and re.search(r'\b(?:bigger|larger|increase|enlarge|grow|smaller|decrease|shrink)\b',low):
            delta=re.search(r'\bby\s+(\d+(?:\.\d+)?)',low);value=float(delta[1]) if delta else 2
            if re.search(r'\b(?:smaller|decrease|shrink)\b',low):value=-value
            steps.append(operation('font_size_delta',target,value))
        rgb=re.search(r'#[0-9a-f]{6}\b',low)
        named=re.search(r'\b('+COLORS+r')\b',low)
        if rgb or named:
            value=rgb[0] if rgb else named[1]
            is_fill=bool(re.search(r'\b(?:background|fill|shading)\b',low))
            action='table_fill' if is_fill and 'table' in low else 'fill_color' if is_fill else 'font_color'
            steps.append(operation(action,'table' if action=='table_fill' else target,value))
        if steps:
            for style in ('bold','italic','underline'):
                if re.search(r'\b'+style+r'\b',low):steps.append({'action':'format','style':style,'target':target,'value':not bool(re.search(r'\b(?:remove|unbold|not)\b',low))})
            return steps[0] if len(steps)==1 else {'action':'batch','steps':steps}
    if re.search(r'\b(?:colou?r|fill|background|shade|paint)\b',low):
        match=re.search(r'(#[0-9a-f]{6}|\b(?:'+COLORS+r')\b)',low)
        if match:
            fill=bool(re.search(r'\b(?:background|fill|shad\w*|paint)\b',low))
            action='table_fill' if 'table' in low else 'fill_color' if fill else 'font_color'
            return operation(action,'table' if action=='table_fill' else target,match[1])
    match=re.search(r'(?:set|change|use)\s+(?:the\s+)?font(?:\s+(?:family|name))?(?:\s+(?:of|for)\s+.+?\s+to|\s+to)?\s+(.+)',raw,re.I)
    if match and not re.search(r'\b(?:size|bigger|smaller|colou?r)\b',match[1],re.I):return operation('font_name',target,match[1].strip('"\''))
    if re.search(r'\bbullet(?:s| points?)?\b',low) or re.search(r'\bnumbered (?:list|points)\b',low):
        op='list_remove' if re.search(r'\b(?:remove|clear|disable)\b',low) else 'numbering' if 'numbered' in low else 'bullets'
        content=raw.split(':',1)[1].strip() if ':' in raw else ''
        return operation(op,target,content)
    if re.fullmatch(r'(?:remove|convert|unlist)\s+(?:the\s+)?table(?:\s+(?:structure|formatting))?(?:\s+(?:but\s+)?(?:keep|preserve)\s+(?:the\s+)?(?:data|text|values))?',low):return operation('table_remove','table')
    if re.match(r'(?:add|insert)\s+(?:a\s+)?row\s+(?:to|in)\s+(?:the\s+)?table',low):return operation('table_row_add','table')
    if re.match(r'(?:add|insert)\s+(?:a\s+)?column\s+(?:to|in)\s+(?:the\s+)?table',low):return operation('table_column_add','table')
    match=re.fullmatch(r'(?:align|alignment|make|set)\s+(.*?)\s*(left|right|center|centre|justified|justify)',raw,re.I)
    if match:return operation('align',clean_target(match[1]),'justify' if match[2].lower()=='justified' else match[2].lower())
    match=re.fullmatch(r'(?:center|centre|left align|right align)\s*(.*)',raw,re.I)
    if match:return operation('align',clean_target(match[1]),'left' if low.startswith('left') else 'right' if low.startswith('right') else 'center')
    match=re.fullmatch(r'(?:apply|use|set)\s+(?:the\s+)?(heading\s*[1-9]|normal|title)(?:\s+style)?',raw,re.I)
    if match:return operation('style',target,match[1])
    if re.fullmatch(r'(?:increase indent|indent)(?:\s+.*)?',low):return operation('indent',target,1)
    if re.fullmatch(r'(?:decrease indent|outdent)(?:\s+.*)?',low):return operation('indent',target,-1)
    if 'wrap' in low and 'text' in low:return operation('wrap_text',target,'off' if re.search(r'\b(?:no|disable|off|remove|unwrap)\b',low) else 'on')
    if re.match(r'(?:auto\s*fit|autofit)\b',low):return operation('autofit',target,'rows' if 'row' in low else 'columns')
    match=re.search(r'\b(column width|row height)\s*(?:to\s*)?(\d+(?:\.\d+)?)',low)
    if match:return operation(match[1].replace(' ','_'),target,match[2])
    if re.match(r'unmerge\b',low):return operation('unmerge',target)
    if re.match(r'merge\b',low):return operation('merge',target)
    if 'border' in low:return operation('borders',target,'none' if re.search(r'\b(?:remove|clear|no)\b',low) else 'all')
    if 'freeze' in low:return operation('freeze_panes',target,'off' if 'unfreeze' in low else 'on')
    if re.match(r'sort\b',low):return operation('sort',target,'descending' if re.search(r'descending|z to a|largest',low) else 'ascending')
    match=re.fullmatch(r'(?:set|enter|put)\s+(?:the\s+)?formula\s+('+CELL+r')\s+(?:to|as|=)\s*(=.+)',raw,re.I)
    if match:return operation('formula',match[1].upper(),match[2])
    match=re.fullmatch(r'(?:format|make|set)\s+(.*?)\s+(?:as\s+)?(percentage|percent|currency|date|number|text|pkr)',raw,re.I)
    if match:return operation('number_format',clean_target(match[1]),match[2].lower())
    match=re.fullmatch(r'(?:add|insert|new|create)\s+(?:a\s+)?(?:work)?sheet(?:\s+(?:named|called)\s+(.+))?',raw,re.I)
    if match:return operation('sheet_add','',match[1] or '')
    match=re.fullmatch(r'(?:select|open|switch to|go to)\s+sheet\s+(.+)',raw,re.I)
    if match:return operation('sheet_select',match[1].strip('"\''))
    match=re.fullmatch(r'rename\s+(?:the\s+)?sheet\s+(.+?)\s+to\s+(.+)',raw,re.I)
    if match:return operation('sheet_rename',match[1].strip('"\''),match[2].strip('"\''))
    if re.fullmatch(r'(?:add|new|insert|create)\s+(?:a\s+)?(?:blank\s+)?slide',low):return operation('slide_add')
    match=re.fullmatch(r'(select|open|go to|duplicate)\s+slide\s+(\d+)',low)
    if match:return operation('slide_duplicate' if match[1]=='duplicate' else 'slide_select','',match[2])
    match=re.fullmatch(r'(?:add|insert)\s+(?:a\s+)?text\s*box\s*:\s*(.+)',raw,re.I|re.S)
    if match:return operation('text_box','',match[1])
    if re.fullmatch(r'(?:insert|add)\s+(?:a\s+)?page break',low):return operation('page_break')
    if re.search(r'\b(?:portrait|landscape)\b',low):return operation('page_orientation','',re.search(r'portrait|landscape',low)[0])
    match=re.fullmatch(r'(?:set\s+)?zoom\s+(?:to\s+)?(\d+)%?',low)
    if match:return operation('zoom','',match[1])
    if low in ('save','save document','save workbook','save presentation'):return operation('save')
    if low in ('undo','redo'):return operation(low)
    match=re.fullmatch(r'(?:run|execute|office command)\s+(?:office\s+command\s+)?([A-Za-z][A-Za-z0-9_]+)',raw,re.I)
    if match:return operation('mso','',match[1])
    return None

def related(task):
    task=re.sub(r'^\s*(?:please\s+|can you\s+|could you\s+)','',task,flags=re.I)
    return bool(re.match(r'^(?:make|change|set|give|turn|increase|decrease|enlarge|shrink|format|select|insert|add|remove|delete|clear|erase|empty|merge|unmerge|align|center|centre|sort|freeze|unfreeze|autofit|wrap|duplicate|rename|apply|save|export|indent|outdent|execute|run)\s+\S',task.strip(),re.I))

def shortlisted_tools(kind,task):
    """Keep the small local model's choices relevant to the current intent."""
    available=tools_for(kind);low=task.lower();groups=[]
    if re.search(r'font|letter|typeface|text colou?r|bigger|smaller|larger|enlarge|shrink',low):
        groups+=['font_size','font_size_delta','font_name','font_color','fill_color','select','align']
    if re.search(r'bullet|numbered|list|paragraph|spacing|indent',low):groups+=['bullets','numbering','list_remove','line_spacing','indent','align','font_color']
    if re.search(r'\btable\b',low):groups+=[op for op in available if op.startswith('table_')]+['font_color','font_size','borders']
    if not groups:return available
    return {op:available[op] for op in dict.fromkeys(groups) if op in available}

def tools_for(kind):
    return {name:DESCRIPTIONS.get(name,name.replace('_',' ')) for name,apps in TOOL_APPS.items() if kind in apps}
