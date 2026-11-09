"""Isolated public-page popup test. Never clicks authentication controls."""
from browser_control import Browser
from catalog import norm

b=Browser(profile_name='dailymotion-layer-verification')
try:
    b.open('chrome',True)
    b.act({'action':'navigate','url':'https://www.dailymotion.com/'})
    found=False
    for _ in range(4):
        obs=b.observe()
        labels=[e['text'] for e in obs['elements'] if e['text']]
        if any(norm(label)=='i understand' for label in labels):
            print('Public-page popup found; reachable labels:',labels[:12],flush=True)
            print(b.click_named('I understand'),flush=True)
            found=True; break
        b.page.wait_for_timeout(700)
    if not found: print('Popup was not present in this fresh test profile. Modal behavior is covered by local browser fixtures.',flush=True)
    print('Final public URL:',b.page.url,flush=True)
finally: b.close()
