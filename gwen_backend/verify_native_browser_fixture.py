"""UI test fixture: isolated Chrome, local navigation and intercepted search only."""
import json,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from browser_control import Browser

root=Path(__file__).resolve().parent;events=[]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/opened':events.append({'kind':'open','url':self.path})
        self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers()
        self.wfile.write(b'<title>Gwen isolated browser fixture</title><h1>Gwen browser test</h1><p>Isolated profile. No personal tabs.</p>')
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
b=Browser(profile_name='native-address-bar-verification')
try:
    b.open('chrome',False)
    def search(route):
        events.append({'kind':'search','url':route.request.url})
        route.fulfill(status=200,content_type='text/html',body='<title>Gwen isolated browser fixture</title><h1>Search request captured locally</h1>')
    b.context.route('https://www.google.com/search?*',search)
    b.page.goto(f'http://127.0.0.1:{server.server_port}/ready')
    print(json.dumps({'ready':True,'open_command':f'open http://127.0.0.1:{server.server_port}/opened','search_command':'search gwen navigation verification','title':b.page.title()}),flush=True)
    end=time.monotonic()+240
    while time.monotonic()<end and {e['kind'] for e in events}!={'open','search'}:b.page.wait_for_timeout(300)
    result={'passed':{e['kind'] for e in events}=={'open','search'},'events':events}
    (root/'diagnostics'/'native-browser-ui-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result),flush=True)
finally:b.close();server.shutdown()
