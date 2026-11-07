"""Isolated Chrome UI fixture for native Pause/Play and tab lifecycle commands."""
import json,time
from pathlib import Path
from browser_control import Browser

root=Path(__file__).resolve().parent;events=[];b=Browser(profile_name='tab-media-ui-verification')
try:
    b.open('chrome',False);media=b.page
    media.expose_function('record',lambda value:events.append(value))
    media.set_content('''<title>Gwen media fixture - YouTube</title><h1>Isolated media control test</h1><canvas id="c" width="100" height="100"></canvas><video id="v" muted width="320" height="200"></video><button id="toggle" aria-label="Pause (k)">Pause (k)</button><script>const v=document.querySelector('video'),b=document.querySelector('button');document.querySelector('canvas').getContext('2d').fillRect(0,0,80,80);v.srcObject=document.querySelector('canvas').captureStream(10);v.play();b.onclick=()=>{if(v.paused){v.play();record('media_play');b.textContent='Pause (k)'}else{v.pause();record('media_pause');b.textContent='Play (k)'}b.setAttribute('aria-label',b.textContent)}</script>''')
    reference=b.context.new_page();reference.set_content('<title>Gwen reference fixture</title><h1>Reference tab</h1>')
    reference.on('close',lambda *_:events.append('reference_closed'))
    b.context.on('page',lambda *_:events.append('tab_new'))
    media.bring_to_front()
    print('Fixture ready: pause video, play video, open new tab, switch to reference tab, close current tab.',flush=True)
    end=time.monotonic()+360
    while time.monotonic()<end and not {'media_pause','media_play','tab_new','reference_closed'}<=set(events):
        media.wait_for_timeout(200)
    result={'passed':{'media_pause','media_play','tab_new','reference_closed'}<=set(events),'events':events}
    (root/'diagnostics'/'tab-media-ui-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True)
finally:b.close()
