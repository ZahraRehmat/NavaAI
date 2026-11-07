"""Reproducible controller and optional local-model integration checks."""
import argparse, json, threading, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from catalog import Catalog
from browser_control import Browser
from planner import Planner, parse_action

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model',action='store_true'); args=ap.parse_args()
    c=Catalog()
    assert c.resolve('store')['name']=='Microsoft Store'
    assert 'code' not in c.resolve('vs studio')['name'].lower()
    assert c.resolve('vs code')['name']=='Visual Studio Code'
    assert 'chrome' in c.resolve('chrome')['name'].lower()
    assert parse_action('```json\n{"action":"done","message":"ok"}\n```')['action']=='done'
    try: c.resolve('zzzz-unknown-nonexistent-app-7234')
    except ValueError: pass
    else: raise AssertionError('Unknown app incorrectly matched')
    print('PASS app directory, aliases, ambiguity rules, JSON parsing',flush=True)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
            self.wfile.write(b'''<html><head><title>Gwen test</title></head><body><label>Name <input aria-label="Name"></label><button onclick="document.querySelector('#result').innerText=document.querySelector('input').value">Apply</button><p id="result"></p><select><option value="a">A</option><option value="b">B</option></select></body></html>''')
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    b=Browser(profile_name='verification')
    try:
        b.open('chrome',True)
        b.act({'action':'navigate','url':f'http://127.0.0.1:{server.server_port}'})
        obs=b.observe(); inp=next(e['id'] for e in obs['elements'] if e['tag']=='INPUT'); button=next(e['id'] for e in obs['elements'] if e['tag']=='BUTTON')
        b.act({'action':'browser_fill','id':inp,'text':'Gwen verified'})
        b.act({'action':'browser_click','id':button})
        assert b.page.locator('#result').inner_text()=='Gwen verified'
        b.act({'action':'browser_new_tab'}); assert len(b.context.pages)>=2
        b.act({'action':'browser_tab','index':0}); assert b.page.title()=='Gwen test'
        print('PASS real background Chrome navigation, DOM observation, typing, clicking and tabs',flush=True)
        if args.model:
            config=json.loads(Path('config.json').read_text()); stop=threading.Event()
            t=time.perf_counter(); planner=Planner(config,stop,print)
            obs=b.observe()
            history=[]
            for _ in range(5):
                a=planner.next('Replace the Name input with Gwen model test. Do not click Apply yet.',b.observe(),None,history,[])
                print('MODEL browser action:',a,flush=True)
                assert a['action'] in ('browser_click','browser_fill','browser_press'),a
                if a['action']=='browser_click': assert int(a['id'])==inp,a
                b.act(a); history.append({'action':a,'result':'Completed'})
                if b.page.locator('input').input_value()=='Gwen model test': break
            assert b.page.locator('input').input_value()=='Gwen model test'
            # Exercise real vision encoder using a neutral synthetic screen.
            from PIL import Image, ImageDraw
            image=Image.new('RGB',(800,500),'white'); draw=ImageDraw.Draw(image)
            draw.rectangle((500,300,740,460),fill='navy'); draw.text((545,365),'CONTINUE',fill='white',font_size=25)
            a=planner.next('Click the center of the blue CONTINUE button in the screenshot.',{'mode':'desktop'},image,[],[])
            print('MODEL vision action:',a,flush=True)
            assert a['action']=='click',a
            assert 625<=float(a['x'])<=925 and 600<=float(a['y'])<=920,a
            print(f'PASS local model DOM planning + screenshot grounding ({time.perf_counter()-t:.1f}s)',flush=True)
            large={'mode':'browser','text':'Long web page content. '*12000,'elements':[{'id':i,'tag':'BUTTON','text':'Target' if i==99 else 'Other button '+str(i),'href':'x'*5000} for i in range(120)]}
            a=planner.next('Click Target.',large,None,[{'error':'old diagnostic '*2000}],[])
            assert planner.last_prompt_tokens<=config.get('max_prompt_tokens',1600)
            print('PASS large-page model inference: bounded text input',planner.last_prompt_tokens,'tokens; device',planner.device,flush=True)
            from agent import Agent
            agent=Agent(log=print,stop=stop)
            agent.browser=b; agent.mode='browser'; agent.planner=planner
            agent.run('Replace the Name input with Gwen complete test.',background=True,step_limit=6)
            assert b.page.locator('input').input_value()=='Gwen complete test'
            agent.run('Click the Apply button.',background=True,step_limit=6)
            assert b.page.locator('#result').inner_text()=='Gwen complete test'
            assert agent.context[-2]['task'].startswith('Replace the Name')
            assert agent.context[-1]['task']=='Click the Apply button.'
            print('PASS sequential user instructions, agent observe-plan-act loop and task memory',flush=True)
    finally:
        b.close(); server.shutdown()
    Path('verification.txt').write_text('Controller integration checks passed.'+ (' Local Qwen browser planning and synthetic vision grounding passed.' if args.model else ' Model checks not requested.'),encoding='utf8')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        Path('verification.txt').write_text('FAILED: '+repr(exc),encoding='utf8')
        raise
