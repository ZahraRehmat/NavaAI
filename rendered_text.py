"""Select rendered read-only DOM text in an owned browser connection."""

SNAPSHOT=r"""()=>{
 const root=document.body;if(!root)return null;
 const entries=[];let text='',visited=0;
 const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
 let node;
 while((node=walk.nextNode())&&++visited<=10000){
   const parent=node.parentElement;if(!parent||!node.data.trim())continue;
   if(parent.closest('script,style,noscript,template,input,textarea,[hidden],[aria-hidden="true"]'))continue;
   const style=getComputedStyle(parent);
   if(style.visibility!=='visible'||style.display==='none'||style.userSelect==='none')continue;
   const r=document.createRange();r.selectNodeContents(node);
   if(![...r.getClientRects()].some(b=>b.width>0&&b.height>0&&b.right>0&&b.bottom>0&&b.left<innerWidth&&b.top<innerHeight))continue;
   if(text)text+='\n';
   const start=text.length;text+=node.data;
   entries.push({node,start,end:text.length,value:node.data});
   if(text.length>100000)throw Error('Focus a smaller visible text area before selecting.');
 }
 return {root,entries,text};
}"""

SELECT=r"""(state,p)=>{
 if(!state.root.isConnected||state.entries.some(e=>!e.node.isConnected||!state.root.contains(e.node)||e.node.data!==e.value))
   throw Error('The page text changed while choosing; repeat selection.');
 const first=state.entries.find(e=>p.left>=e.start&&p.left<e.end);
 const last=state.entries.find(e=>p.right>e.start&&p.right<=e.end);
 if(!first||!last)throw Error('The requested text range is no longer available.');
 const r=document.createRange();r.setStart(first.node,p.left-first.start);r.setEnd(last.node,p.right-last.start);
 const s=state.root.ownerDocument.getSelection();s.removeAllRanges();s.addRange(r);
 if(s.isCollapsed)throw Error('This page did not allow text selection.');
 return s.toString();
}"""


def browser_document_select(page,start,end,copy=False,chooser=None):
    from text_input import span_offsets,copy_selected,SelectionResolutionError
    candidates=[];handles=[]
    try:
        for frame in page.frames:
            try:
                state=frame.evaluate_handle(SNAPSHOT);handles.append(state)
                text=state.evaluate('s=>s&&s.text')
                if not text:continue
                span_offsets(text,start,end,chooser=lambda *args:0)
                candidates.append((state,text,frame))
            except Exception:continue
        if not candidates:raise ValueError('Could not find both endpoints in visible selectable page text. Bring the text into view and repeat.')
        index=0
        if len(candidates)>1:
            if not chooser:raise SelectionResolutionError('More than one page frame contains these words. Say longer endpoint phrases.')
            options=[{'label':frame.url,'detail':' '.join(text.split())[:160],
                      'selection_role':'text area','selection_phrase':'matching text'} for _,text,frame in candidates[:26]]
            index=chooser('Which page text?',options)
            if index is None:raise SelectionResolutionError('Selection cancelled. Nothing was selected or copied.')
            if not isinstance(index,int) or not 0<=index<len(options):raise SelectionResolutionError('Invalid page text choice.')
        state,text,frame=candidates[index]
        left,right=span_offsets(text,start,end,chooser=chooser)
        payload={'left':len(text[:left].encode('utf-16-le'))//2,
                 'right':len(text[:right].encode('utf-16-le'))//2}
        actual=state.evaluate(SELECT,payload)
        if not actual:raise ValueError('The page did not expose selectable text for that range.')
        return copy_selected(actual) if copy else 'Selected the requested page text.'
    finally:
        for handle in handles:handle.dispose()
