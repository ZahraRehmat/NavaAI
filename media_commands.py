"""Explicit playback commands; bare navigation words keep their existing meaning."""
import re


def intent(text,browser_active=False):
    low=text.casefold().strip().rstrip('.!')
    low=re.sub(r'\s+(?:on|in)\s+youtube$',' youtube',low)
    site='youtube' if re.search(r'\byoutube\b',low) else None
    clean=re.sub(r'\byoutube\b','',low);clean=' '.join(clean.split())
    if re.fullmatch(r'skip (?:(?:the|this|current) )?ads?',clean):
        return {'action':'media_skip_ad','site':'youtube'}
    m=re.fullmatch(r'(pause|play|resume|unpause|continue|stop)\s*(?:(?:the|this|current)\s+)?(?:video|playback|media)?',clean)
    if m and (browser_active or site or re.search(r'video|playback|media',clean)):
        return {'action':'media_pause' if m[1] in ('pause','stop') else 'media_play','site':site}
    m=re.fullmatch(r'(?:play |go to |skip to )?(?:the )?(next|previous|prev) video',clean)
    if m:return {'action':'media_next' if m[1]=='next' else 'media_previous','site':'youtube'}
    m=re.fullmatch(r'(fast forward|forward|rewind|skip ahead|skip back|go forward|go back|seek forward|seek backward)(?: (?:the )?video)?(?: (?:by|for))? (5|10|five|ten)(?: (?:seconds?|secs?))?(?: (?:in|on) (?:the )?video)?',clean)
    if m:
        seconds={'five':5,'ten':10}.get(m[2],int(m[2]) if m[2].isdigit() else 0)
        return {'action':'media_seek','seconds':seconds*(-1 if m[1] in ('rewind','skip back','go back','seek backward') else 1),'site':'youtube'}
    return None
