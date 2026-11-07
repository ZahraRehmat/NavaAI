from agent import Agent
from browser_control import Browser
from urllib.parse import urlsplit,parse_qs

a=Agent(); a.browser=Browser(profile_name='youtube-verification'); a.mode='desktop'; a.active_target='Task Manager'
try:
    a.run('search mr beast on youtube',background=True)
    url=a.browser.page.url
    assert urlsplit(url).hostname in ('www.youtube.com','youtube.com') and parse_qs(urlsplit(url).query).get('search_query')==['mr beast'],url
    print('PASS YouTube site search without Google or VLM',flush=True)
    result=a.run('open first video',background=True)
    assert '/watch?' in a.browser.page.url,result
    assert a.planner is None
    print('PASS first YouTube video selected from current results without VLM',flush=True)
finally: a.close()
