"""Persistent, separate browser profile. DOM operations also work headlessly."""
import json
from urllib.parse import urlparse
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
DOM = r'''(token) => {
 document.querySelectorAll('[data-gwen-id]').forEach(e=>{e.removeAttribute('data-gwen-id');e.removeAttribute('data-gwen-token')});
 const nodes = [...document.querySelectorAll('a,button,input,textarea,select,[role="button"],[contenteditable="true"]')];
 return nodes.filter(e=>{
 if(!e.getClientRects().length || getComputedStyle(e).visibility==='hidden' || e.disabled || e.getAttribute('aria-disabled')==='true')return false;
 const r=e.getBoundingClientRect(); const l=Math.max(0,r.left),t=Math.max(0,r.top),right=Math.min(innerWidth,r.right),bottom=Math.min(innerHeight,r.bottom);
 if(right<=l || bottom<=t)return false;
 const hit=document.elementFromPoint((l+right)/2,(t+bottom)/2);
 return !!hit && (e===hit || e.contains(hit) || hit.closest('label')?.control===e);
 }).slice(0,120).map((e,i)=>{
 e.setAttribute('data-gwen-id',String(i));
 e.setAttribute('data-gwen-token',token);
 return {id:i,tag:e.tagName,role:e.getAttribute('role'),focused:e===document.activeElement,text:(e.innerText?.trim()||e.getAttribute('aria-label')||e.placeholder||e.title||'').slice(0,140),type:e.type||'',value:e.type==='password'?'[hidden]':String(e.value||'').slice(0,120),href:e.getAttribute('href')};
 });
}'''

class Browser:
    def __init__(self, profile_name=None): self.pw=None; self.context=None; self.channel=None; self.headless=False; self.selected=None; self.profile_name=profile_name; self.elements={};self.process_id=None;self.closed=False

    def open(self, channel='chrome', headless=False):
        if channel not in ('chrome','msedge','chromium'): raise ValueError('Browser must be chrome, msedge, or chromium')
        if self.context:
            try:
                if self.closed or not self.context.browser.is_connected():self.close()
            except Exception:self.close()
        if self.context and (channel!=self.channel or headless!=self.headless): self.close()
        if not self.context:
            self.pw=sync_playwright().start()
            try:
                profile=ROOT/'browser_profiles'/(self.profile_name or channel)
                self.context=self.pw.chromium.launch_persistent_context(str(profile), channel=channel, headless=headless, viewport={'width':1280,'height':800}, accept_downloads=True, downloads_path=str(ROOT/'downloads'))
                self.closed=False
                self.context.on('close',lambda *_:setattr(self,'closed',True))
                self.context.set_default_timeout(8000)
                try:
                    session=self.context.browser.new_browser_cdp_session()
                    processes=session.send('SystemInfo.getProcessInfo')['processInfo'];session.detach()
                    self.process_id=next(int(p['id']) for p in processes if p['type']=='browser')
                except Exception:self.process_id=None
            except Exception:
                self.pw.stop(); self.pw=None
                raise
            self.channel=channel; self.headless=headless
        return f'{channel} ready; background={headless}'

    @property
    def page(self):
        if not self.context: self.open()
        if self.selected and not self.selected.is_closed(): return self.selected
        pages=self.context.pages
        return pages[-1] if pages else self.context.new_page()

    def observe(self):
        p=self.page
        import uuid
        token=uuid.uuid4().hex; self.elements={}; elements=[]; texts=[]
        for frame in p.frames:
            try:
                if frame!=p.main_frame:
                    host=frame.frame_element()
                    if not host.is_visible(): continue
                    reachable=host.evaluate('e=>{const r=e.getBoundingClientRect();const h=e.ownerDocument.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return h===e||e.contains(h)}')
                    if not reachable: continue
                rows=frame.evaluate(DOM,token)
                for row in rows:
                    local=row['id']; index=len(elements); row['id']=index
                    self.elements[index]=frame.locator(f'[data-gwen-id="{local}"][data-gwen-token="{token}"]')
                    elements.append(row)
                if rows: texts.append(frame.locator('body').inner_text(timeout=1500)[:4000])
            except Exception: continue
        return {'url':p.url,'title':p.title(),'blocked':self.blocked_reason(),'tabs':[{'index':i,'url':t.url} for i,t in enumerate(self.context.pages)],'elements':elements,'text':'\n'.join(texts)[:10000]}

    def element(self,index):
        el=self.elements.get(index)
        if el is None: raise ValueError('Unknown or stale browser control ID. Observe the current page first.')
        return el

    def command(self,command,chooser=None):
        from browser_commands import tab_index
        op=command['action'];p=self.page
        if op=='tab_new':
            self.selected=self.context.new_page()
            if not self.headless:self.selected.bring_to_front()
            return 'Opened a new browser tab.'
        if op=='tab_close':
            pages=list(self.context.pages);index=pages.index(p);p.close()
            remaining=list(self.context.pages)
            self.selected=remaining[min(index,len(remaining)-1)] if remaining else None
            if self.selected and not self.headless:self.selected.bring_to_front()
            return 'Closed the selected browser tab.'
        if op=='tab_switch':
            pages=list(self.context.pages);rows=[{'name':page.title() or page.url,'detail':page.url} for page in pages]
            index=tab_index(command['target'],rows,pages.index(p),chooser)
            chosen=pages[index]
            if chosen.is_closed() or chosen.title() not in (rows[index]['name'],''):
                raise ValueError('The chosen tab changed or closed while selecting. Try again.')
            self.selected=chosen
            if not self.headless:chosen.bring_to_front()
            return 'Switched to tab: '+(chosen.title() or chosen.url)+'.'
        if op in ('media_pause','media_play'):
            if command.get('site')=='youtube' and 'youtube.com' not in (urlparse(p.url).hostname or ''):
                self.command({'action':'tab_switch','target':'youtube'},chooser);p=self.page
            players=[]
            for frame in p.frames:
                try:
                    for index,row in enumerate(frame.locator('video,audio').evaluate_all("es=>es.map(e=>{const r=e.getBoundingClientRect();return {paused:e.paused,area:r.width*r.height,visible:!!e.getClientRects().length,title:e.getAttribute('aria-label')||e.title||e.tagName.toLowerCase()}})")):
                        players.append({'frame':frame,'index':index,**row})
                except Exception:continue
            if not players:raise ValueError('No HTML video/audio player was found in this tab.')
            preferred=[r for r in players if r['visible'] and (op=='media_play' or not r['paused'])] or [r for r in players if r['visible']] or players
            preferred.sort(key=lambda r:-r['area'])
            if len(preferred)>1 and preferred[0]['area']<preferred[1]['area']*2.5:
                if not chooser:raise ValueError('Several media players are present. Select one in the page.')
                options=[dict(label=f"Player {i+1}: {r['title']}",detail=r['frame'].url,match_score=100) for i,r in enumerate(preferred)]
                index=chooser('Which media player?',options)
                if index is None:raise InterruptedError('Media selection cancelled.')
                chosen=preferred[index]
            else:chosen=preferred[0]
            element=chosen['frame'].locator('video,audio').nth(chosen['index'])
            if op=='media_pause':
                paused=element.evaluate('e=>{e.pause();return e.paused}')
                if not paused:raise ValueError('The player did not confirm a paused state.')
                return 'Video/audio paused.'
            paused=element.evaluate('async e=>{await e.play();return e.paused}')
            if paused:raise ValueError('Playback did not start; the site may require a manual Play click.')
            return 'Video/audio playing.'
        raise ValueError('Unknown browser command')

    def click_named(self,label,chooser=None):
        from label_matching import choose_label,NoLabelMatch,AmbiguousLabel,match_description,dialog_action,normalize_label
        obs=self.observe()
        if obs['blocked']: raise ValueError(obs['blocked'])
        candidates=obs['elements']
        if dialog_action(label):candidates=[e for e in candidates if normalize_label(e['text'])==normalize_label(label)]
        def pick(query,options):
            boxes=[]
            for index,option in enumerate(options):
                box=self.element(option['id']).bounding_box()
                if box:boxes.append(dict(box,letter=chr(65+index)))
            self.page.evaluate('''boxes=>{document.querySelector('#gwen-target-choices')?.remove();const root=document.createElement('div');root.id='gwen-target-choices';root.style.cssText='position:fixed;inset:0;z-index:2147483647;pointer-events:none';for(const b of boxes){const e=document.createElement('div');e.style.cssText=`position:absolute;left:${b.x}px;top:${b.y}px;width:${b.width}px;height:${b.height}px;border:3px solid #ffb000;box-sizing:border-box`;const badge=document.createElement('b');badge.textContent=b.letter;badge.style.cssText='position:absolute;left:0;top:0;background:#ffb000;color:#111827;border-radius:50%;font: bold 19px sans-serif;padding:3px 8px';e.append(badge);root.append(e)}document.documentElement.append(root)}''',boxes)
            try:return chooser(query,options,preview=self.page.screenshot())
            finally:
                try:self.page.evaluate("document.querySelector('#gwen-target-choices')?.remove()")
                except Exception:pass
        try:
            if chooser:
                from target_choices import select_target
                match=select_target(candidates,label,key='text',chooser=pick)['row']
            else:match=choose_label(candidates,label,key='text')['row']
        except NoLabelMatch:
            labels=list(dict.fromkeys(e['text'] for e in obs['elements'] if e['text']))[:8]
            raise ValueError('No reachable control matches "'+label+'". Visible controls: '+', '.join(labels))
        except AmbiguousLabel as exc:raise ValueError('Multiple reachable controls match "'+label+'". '+str(exc))
        # Recheck the selected DOM label after a popup; dynamic pages may change.
        if chooser:
            el=self.element(match['id'])
            current=el.evaluate("e=>(e.innerText?.trim()||e.getAttribute('aria-label')||e.placeholder||e.title||'').slice(0,140)")
            if current!=match['text']:raise ValueError('The selected browser label changed while choosing. Repeat the request.')
        self.act({'action':'browser_click','id':match['id']})
        return match_description(label,match['text'])+' Clicked the reachable '+match['text']+' control.'

    def blocked_reason(self):
        p=self.page
        host=(urlparse(p.url).hostname or '').lower()
        if (host=='google.com' or host.endswith('.google.com')) and urlparse(p.url).path.startswith('/sorry'):
            return 'Google CAPTCHA: complete the check manually in the visible browser. No result clicks were attempted.'
        title=p.title().lower()
        if title.strip() in ('just a moment...','verify you are human','attention required! | cloudflare'):
            return 'Browser verification challenge: manual help is required. No clicks were attempted.'
        return None

    def open_first(self,kind):
        blocked=self.blocked_reason()
        if blocked: raise ValueError(blocked)
        host=(urlparse(self.page.url).hostname or '').lower()
        if host=='youtube.com' or host.endswith('.youtube.com'):
            selector='a#video-title[href*="/watch?"], a#video-title-link[href*="/watch?"]'
        elif kind=='video': raise ValueError('Open YouTube search results before requesting the first video.')
        elif host.endswith(('google.com','bing.com','duckduckgo.com')):
            selector='a:has(h3), h2 a'
        else: raise ValueError('First-result selection is unavailable on this page. Specify the link title.')
        links=self.page.locator(selector)
        links.first.wait_for(state='attached',timeout=15000)
        for i in range(min(30,links.count())):
            link=links.nth(i)
            if link.is_visible():
                title=(link.get_attribute('title') or link.inner_text()).strip()[:160]
                link.click(timeout=12000)
                self.page.wait_for_load_state('domcontentloaded',timeout=15000)
                return 'Opened '+(title or 'first '+kind)+': '+self.page.url
        raise ValueError('No visible matching results. Nothing was clicked.')

    def act(self, a):
        p=self.page; op=a['action']; pages_before=list(self.context.pages)
        if op!='navigate':
            blocked=self.blocked_reason()
            if blocked: raise ValueError(blocked)
        if op=='navigate':
            url=a['url']
            if urlparse(url).scheme not in ('https','http'): raise ValueError('Only http/https navigation is supported')
            p.goto(url,wait_until='domcontentloaded',timeout=45000)
        elif op in ('browser_click','browser_fill','browser_select','browser_check','browser_hover'):
            el=self.element(int(a['id']))
            if op=='browser_click':
                el.click(trial=True,timeout=1500)
                el.click(timeout=4000)
            elif op=='browser_fill': el.fill(str(a['text']))
            elif op=='browser_select': el.select_option(str(a['value']))
            elif op=='browser_check': el.set_checked(bool(a.get('checked',True)))
            else: el.hover()
        elif op=='browser_press': p.keyboard.press(a['key'])
        elif op=='browser_upload':
            path=Path(a['path']).expanduser().resolve(strict=True)
            if not path.is_file(): raise ValueError('Upload path must be a file')
            self.element(int(a['id'])).set_input_files(str(path))
        elif op=='browser_read':
            text=p.locator('body').inner_text()
            if a.get('save_as'):
                name=Path(a['save_as']).name
                if not name or name in ('.','..') or ':' in name: raise ValueError('Invalid output filename')
                folder=ROOT/'downloads'; folder.mkdir(exist_ok=True)
                dest=folder/name
                if dest.exists(): raise ValueError('Output file exists; choose a new filename')
                dest.write_text(text,encoding='utf8')
                return 'Saved page text to '+str(dest)
            return text[:16000]
        elif op=='browser_close_tab':
            p.close(); self.selected=None
        elif op=='browser_scroll': p.mouse.wheel(0,max(-2000,min(2000,int(a['amount']))))
        elif op=='browser_back': p.go_back(wait_until='domcontentloaded')
        elif op=='browser_tab':
            index=int(a['index']); pages=self.context.pages
            if not 0<=index<len(pages): raise ValueError('Invalid tab index')
            # page property follows last page; keep explicit selection.
            self.selected=pages[index]
        elif op=='browser_new_tab': self.selected=self.context.new_page()
        else: raise ValueError('Unknown browser action: '+op)
        if op not in ('browser_tab','browser_new_tab','browser_close_tab'):
            new_pages=[page for page in self.context.pages if page not in pages_before]
            if new_pages: self.selected=new_pages[-1]
        return 'Browser action completed'

    def close(self):
        try:
            if self.context:self.context.close()
        except Exception:pass
        try:
            if self.pw:self.pw.stop()
        except Exception:pass
        self.context=None; self.pw=None; self.selected=None;self.process_id=None;self.closed=True
