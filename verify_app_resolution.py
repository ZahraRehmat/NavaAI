"""Resolve names against this PC's catalog and check routing without launching apps."""
import json
from pathlib import Path
from unittest.mock import Mock,patch
from agent import Agent

rows=[]
for task in ('open microsoft word','open ms excel','open power point','open whats app','open steem','open chorme','open vs code','open vs studio','open store','open task manger','open file explorer'):
    a=Agent(log=lambda _:None);a.dispatch=Mock(return_value='TEST: launch intercepted')
    try:
        with patch('file_control.open_requested_file',side_effect=AssertionError('Known app reached file matcher')),patch('planner.Planner',side_effect=AssertionError('Known app reached model')):
            result=a.run(task)
    except AssertionError as exc:result=str(exc)
    call=a.dispatch.call_args
    rows.append({'task':task,'passed':call is not None,'action':call.args[0] if call else None,'result':result})
path=Path(__file__).resolve().parent/'diagnostics'/'app-resolution-verification.json'
path.write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
assert all(row['passed'] for row in rows)
