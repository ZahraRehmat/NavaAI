"""Live navigation checks using a test-only profile, preserving Gwen's browser."""
from agent import Agent
from browser_control import Browser
from urllib.parse import urlsplit, parse_qs

a=Agent(); a.browser=Browser(profile_name='search-regression'); a.mode='desktop'; a.active_target='Task Manager'
try:
    a.run('search youtube on chrome',background=True)
    url=a.browser.page.url
    if 'google.com/sorry/' in url:
        assert 'CAPTCHA' in a.context[-1]['result']
        print('BLOCKED Google search: CAPTCHA correctly reported; browser route used, no desktop fallback',flush=True)
    else:
        assert 'google.' in urlsplit(url).hostname and parse_qs(urlsplit(url).query).get('q')==['youtube'], url
        print('PASS exact Chrome text-search command from desktop mode',flush=True)
    a.run('search youtube.com on chrome',background=True)
    assert urlsplit(a.browser.page.url).hostname in ('youtube.com','www.youtube.com'),a.browser.page.url
    assert a.planner is None
    print('PASS exact Chrome domain command without VLM or desktop clicks',flush=True)
finally: a.close()
