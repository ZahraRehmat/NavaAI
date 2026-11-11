"""Compact scanner health without document text, screenshots or control labels."""
from collections import Counter

def summarize(roots,raw_rows,visible_rows,errors=(),traversals=None):
    raw=Counter(row.get('hwnd') for row in raw_rows);visible=Counter(row.get('hwnd') for row in visible_rows)
    scope_counts=Counter(row.get('scope','app') for row in visible_rows)
    per_root=[{'hwnd':root['hwnd'],'pid':root.get('pid'),'class':root.get('kind',''),
               'scope':root['scope'],'raw_targets':raw[root['hwnd']],'visible_targets':visible[root['hwnd']],
               'traversal':(traversals or {}).get(root['hwnd'],{})} for root in roots]
    return {'visible_by_scope':dict(scope_counts),'taskbar_only':bool(scope_counts['taskbar'] and not(scope_counts['app'] or scope_counts['desktop'])),
            'roots':per_root,'errors':list(errors)}

def warning(health):
    if health.get('taskbar_only'):
        return 'Only taskbar controls detected. Run Diagnose Grid.cmd with an affected app visible; application scanning needs inspection.'
    return ''
