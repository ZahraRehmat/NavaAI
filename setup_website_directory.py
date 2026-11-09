"""Refresh the local directory explicitly; never run during command execution."""
import argparse,json,re,urllib.request
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--list-id',default='8P8NV');parser.add_argument('--count',type=int,default=10000)
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Z0-9]{5}',args.list_id) or not 1000<=args.count<=100000:
        raise ValueError('Use a five-character Tranco list ID and 1,000–100,000 domains.')
    source='https://tranco-list.eu/download/'+args.list_id+'/1000000';rows=[]
    with urllib.request.urlopen(source,timeout=30) as response:
        for raw in response:
            fields=raw.decode('utf-8').strip().split(',')
            if len(fields)==2 and fields[0].isdigit() and re.fullmatch(r'[a-z0-9.-]+\.[a-z]{2,}',fields[1]):
                rows.append([int(fields[0]),fields[1]])
            if len(rows)>=args.count:break
    if len(rows)!=args.count:raise RuntimeError('Incomplete download; existing directory retained.')
    data={'source':'Tranco','list_id':args.list_id,'source_url':source,
          'reference_url':'https://tranco-list.eu/list/'+args.list_id,'domains':rows}
    path=Path(__file__).with_name('data')/'popular_websites.json';path.parent.mkdir(exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8');temporary.replace(path)
    print(f'Installed {len(rows):,} domains from Tranco {args.list_id}. Restart Gwen to reload.')


if __name__=='__main__':main()
