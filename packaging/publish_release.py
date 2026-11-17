"""Upload a verified installer using the configured Git credential helper."""
import argparse,hashlib,http.client,json,subprocess,urllib.error,urllib.parse,urllib.request
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',required=True);parser.add_argument('--tag',required=True)
    parser.add_argument('--asset',type=Path,required=True);parser.add_argument('--notes',type=Path,required=True)
    parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    credential=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,check=True)
    fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
    headers={'Authorization':'Bearer '+fields['password'],'Accept':'application/vnd.github+json','User-Agent':'NAVA-release'}
    def api(path,data=None,method=None):
        body=json.dumps(data).encode() if data is not None else None
        request=urllib.request.Request('https://api.github.com/repos/'+args.repo+path,data=body,headers=headers,method=method)
        with urllib.request.urlopen(request,timeout=90) as response:return json.load(response)
    try:release=api('/releases/tags/'+args.tag)
    except urllib.error.HTTPError as error:
        if error.code!=404:raise
        release=api('/releases',{'tag_name':args.tag,'target_commitish':'main','name':'NAVA AI '+args.tag,'body':args.notes.read_text(encoding='utf-8'),'draft':True,'prerelease':False})
    size=args.asset.stat().st_size
    digest=hashlib.sha256(args.asset.read_bytes()).hexdigest()
    existing=next((a for a in release.get('assets',[]) if a['name']==args.asset.name),None)
    if existing:
        if existing['size']!=size or existing.get('digest')!='sha256:'+digest:raise RuntimeError('Conflicting release asset; refusing overwrite')
        uploaded=existing
    else:
        url=urllib.parse.urlsplit(release['upload_url'].split('{')[0]+'?name='+urllib.parse.quote(args.asset.name))
        connection=http.client.HTTPSConnection(url.hostname,timeout=600)
        connection.putrequest('POST',url.path+'?'+url.query)
        for key,value in headers.items():connection.putheader(key,value)
        connection.putheader('Content-Type','application/octet-stream');connection.putheader('Content-Length',str(size));connection.endheaders()
        sent=0;milestone=0
        with args.asset.open('rb') as stream:
            while data:=stream.read(1024*1024):
                connection.send(data);sent+=len(data)
                if sent//(32*1024*1024)>milestone:
                    milestone=sent//(32*1024*1024);print('Uploaded '+str(round(sent/size*100,1))+'%',flush=True)
        response=connection.getresponse();body=response.read()
        if response.status!=201:raise RuntimeError('Release upload failed: '+str(response.status)+' '+body.decode()[:500])
        uploaded=json.loads(body);connection.close()
    if uploaded['size']!=size or uploaded.get('digest')!='sha256:'+digest:raise RuntimeError('GitHub asset checksum verification failed')
    if args.publish:
        release=api('/releases/'+str(release['id']),{'draft':False,'body':args.notes.read_text(encoding='utf-8')},'PATCH')
    print(json.dumps({'release':release['html_url'],'download':uploaded['browser_download_url'],'sha256':digest,'bytes':size,'draft':release['draft']}),flush=True)

if __name__=='__main__':main()
