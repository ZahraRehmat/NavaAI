"""Constrain generation to typed actions; control IDs are current-observation enums."""
def schema_for(desktop,ids,point_action=None,describe_points=False,point_target=None):
    variants=[]
    def add(action,props=None):
        p={'action':{'type':'string','enum':[action]}}
        p.update(props or {})
        variants.append({'type':'object','properties':p,'required':list(p),'additionalProperties':False})
    string={'type':'string'}; number={'type':'number'}
    if desktop:
        for name in ('click','move','double_click','right_click','drag'):
            if point_action and name!=point_action:continue
            target={'type':'string','enum':[point_target]} if point_target is not None else {'type':'string','minLength':1}
            add(name,{'target':target} if describe_points else {'x':{'type':'integer','minimum':0,'maximum':1000},'y':{'type':'integer','minimum':0,'maximum':1000}})
        add('type',{'text':string}); add('press',{'key':string}); add('hotkey',{'keys':{'type':'array','items':string,'minItems':1,'maxItems':5}}); add('scroll',{'amount':{'type':'integer'}})
        if ids:
            add('ui_click',{'id':{'type':'integer','enum':sorted(ids)}})
            add('ui_fill',{'id':{'type':'integer','enum':sorted(ids)},'text':string})
    else:
        add('navigate',{'url':string})
        if ids:
            ident={'type':'integer','enum':sorted(ids)}
            add('browser_click',{'id':ident}); add('browser_fill',{'id':ident,'text':string})
            add('browser_select',{'id':ident,'value':string}); add('browser_check',{'id':ident,'checked':{'type':'boolean'}})
        add('browser_press',{'key':string}); add('browser_scroll',{'amount':{'type':'integer'}})
        add('browser_tab',{'index':{'type':'integer','minimum':0}})
        for name in ('browser_back','browser_new_tab','browser_close_tab','desktop_mode'): add(name)
    add('open_app',{'name':string}); add('open_browser',{'channel':{'type':'string','enum':['chrome','msedge','chromium']}})
    add('wait',{'seconds':number}); add('done',{'message':string}); add('ask',{'message':string})
    # Confirmation can wrap one typed action, never another confirmation.
    base=list(variants)
    add('confirm',{'message':string,'next_action':{'anyOf':base}})
    return {'anyOf':variants}
