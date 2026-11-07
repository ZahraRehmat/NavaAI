"""Shared product-name comparisons; spacing/punctuation are not identity."""
import re

def compact_name(name):
    return ''.join(re.findall(r'[a-z0-9]+',str(name).lower()))

def alias_value(name,aliases):
    normalized=' '.join(re.findall(r'[a-z0-9]+',str(name).lower()))
    if normalized in aliases:return aliases[normalized]
    key=compact_name(name)
    values={value for alias,value in aliases.items() if compact_name(alias)==key}
    # Conflicting compact aliases remain ambiguous rather than picking one.
    return next(iter(values)) if len(values)==1 else name
