"""Product branding and exact command wake name."""
import re
DISPLAY_NAME='NAVA AI'
WAKE_WORD='Nava'
WAKE=re.compile(r'^(?:(?:hey|okay|ok)\s+)?nava\b[,:]?\s*',re.I)
WRONG_WAKE=re.compile(r'^(?:(?:hey|okay|ok)\s+)?(?:gwen|guen|glen|glenn|nava\s*ai)\b',re.I)

def invalid_wake(text):return bool(WRONG_WAKE.match(text.strip()))

def strip_wake(text):
    # Prefixes inside literal typing payloads are ordinary text.
    if invalid_wake(text):return text
    return WAKE.sub('',text,count=1)
