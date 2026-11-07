"""Restore and SHA-256 verify the original project into a NEW directory only."""
import argparse,base64,hashlib,json,os,shutil,tempfile,zipfile
from pathlib import Path

BLOCK=4*1024*1024
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(BLOCK),b''):h.update(block)
    return h.hexdigest()

def extract_checked(archive,destination):
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            target=(destination/item.filename).resolve()
            if not target.is_relative_to(destination.resolve()):raise ValueError('Unsafe path in checkpoint archive')
        z.extractall(destination)

def restore(source,destination,key_file):
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    manifest=json.loads((source/'CHECKPOINT_MANIFEST.json').read_text(encoding='utf8'))
    key_info=json.loads(key_file.read_text(encoding='utf8'))
    if key_info['checkpoint']!=manifest['checkpoint']:raise ValueError('The recovery key belongs to a different checkpoint.')
    if destination.exists():raise ValueError('Destination already exists. Choose a NEW folder; existing work will never be overwritten.')
    # Check every encrypted part before creating any restored project.
    for part in manifest['runtime']['parts']:
        path=source/part['path']
        if not path.is_file() or path.stat().st_size!=part['bytes'] or digest(path)!=part['sha256']:
            raise ValueError('Missing/corrupt LFS archive: '+part['path']+'. Run git lfs pull first.')
    with tempfile.TemporaryDirectory(prefix='gwen-restore-') as temp:
        encrypted=Path(temp)/'runtime.aes';archive=Path(temp)/'runtime.zip'
        with encrypted.open('wb') as target:
            for part in manifest['runtime']['parts']:
                with (source/part['path']).open('rb') as stream:shutil.copyfileobj(stream,target,BLOCK)
        magic=manifest['runtime']['magic'].encode();key=base64.b64decode(key_info['key_base64'])
        with encrypted.open('rb') as stream:
            if stream.read(len(magic))!=magic:raise ValueError('Invalid encrypted checkpoint header')
            nonce=stream.read(12);stream.seek(-16,2);tag=stream.read(16)
            remaining=encrypted.stat().st_size-len(magic)-12-16;stream.seek(len(magic)+12)
            decryptor=Cipher(algorithms.AES(key),modes.GCM(nonce,tag)).decryptor();decryptor.authenticate_additional_data(magic)
            with archive.open('wb') as target:
                while remaining:
                    block=stream.read(min(BLOCK,remaining));remaining-=len(block);target.write(decryptor.update(block))
                target.write(decryptor.finalize())
        if digest(archive)!=manifest['runtime']['plain_zip_sha256']:raise ValueError('Decrypted runtime archive did not verify.')
        destination.mkdir(parents=True)
        extract_checked(archive,destination)
        for name in manifest['directories']:(destination/name).mkdir(parents=True,exist_ok=True)
        for index,row in enumerate(manifest['files']):
            target=destination/row['path']
            if row['storage']=='git':
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/row['path'],target)
            if not target.is_file() or target.stat().st_size!=row['bytes'] or digest(target)!=row['sha256']:
                raise ValueError('Restore verification failed: '+row['path'])
            os.utime(target,ns=(row['mtime_ns'],row['mtime_ns']))
            if index%1500==0:print(json.dumps({'phase':'verify_restore','files':index+1,'total':len(manifest['files'])}),flush=True)
    result={'passed':True,'checkpoint':manifest['checkpoint'],'verified_files':len(manifest['files']),'destination':str(destination)}
    print(json.dumps(result),flush=True);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',required=True,type=Path);parser.add_argument('--key-file',required=True,type=Path)
    args=parser.parse_args();restore(Path(__file__).resolve().parent,args.destination.resolve(),args.key_file.resolve())
