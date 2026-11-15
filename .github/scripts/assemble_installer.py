"""Reassemble temporary release upload parts; never publish an unchecked binary."""
import concurrent.futures
import hashlib
import json
import os
import subprocess
from pathlib import Path

REPO = os.environ['GH_REPO']
RELEASE = os.environ['RELEASE_ID']
TAG = 'v1.0.0-preview.1'
FILENAME = 'NAVA-AI-Setup-1.0.0-win-x64.exe'
EXPECTED = '39bddc10fd70e3abc732813b5befa6540193c2a1ce5979a1239bd96d978c594e'
TOTAL = 869637148
CHUNK = 16 * 1024 * 1024


def api(path, method='GET'):
    result = subprocess.run(['gh', 'api', '--method', method, path],
        check=True, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    if REPO != 'ZahraRehmat/NavaAI' or not RELEASE.isdigit():
        raise ValueError('Unexpected release destination')
    base = 'repos/' + REPO
    release = api(base + '/releases/' + RELEASE)
    if not release['draft'] or release['tag_name'] != TAG:
        raise ValueError('Only the expected draft release can be assembled')
    assets = api(base + '/releases/' + RELEASE + '/assets?per_page=100')
    names = {asset['name']: asset for asset in assets}
    parts = Path('upload-parts'); parts.mkdir(exist_ok=True)
    expected_names = ['nava-installer-part-' + str(i).zfill(3) + '.bin'
        for i in range((TOTAL + CHUNK - 1) // CHUNK)]
    for i, name in enumerate(expected_names):
        asset = names.get(name)
        if not asset or asset['state'] != 'uploaded' or asset['size'] != min(CHUNK, TOTAL - i * CHUNK):
            raise ValueError('Missing/incomplete part: ' + name)

    def download(name):
        asset = names[name]
        with (parts / name).open('wb') as output:
            subprocess.run(['gh', 'api', base + '/releases/assets/' + str(asset['id']),
                '-H', 'Accept: application/octet-stream'], stdout=output, check=True)
        if (parts / name).stat().st_size != asset['size']:
            raise ValueError('Downloaded part length mismatch: ' + name)
        print('Downloaded ' + name, flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download, expected_names))
    digest = hashlib.sha256()
    with Path(FILENAME).open('wb') as output:
        for name in expected_names:
            with (parts / name).open('rb') as stream:
                while data := stream.read(1024 * 1024):
                    output.write(data); digest.update(data)
    if Path(FILENAME).stat().st_size != TOTAL or digest.hexdigest() != EXPECTED:
        raise ValueError('Installer SHA-256 mismatch; refusing upload')
    print('Full installer checksum verified: ' + EXPECTED, flush=True)
    existing = names.get(FILENAME)
    if existing:
        if existing['state'] != 'uploaded' or existing['size'] != TOTAL or existing.get('digest') not in (None, 'sha256:' + EXPECTED):
            raise ValueError('Conflicting final asset exists; no overwrite performed')
    else:
        subprocess.run(['gh', 'release', 'upload', TAG, FILENAME, '--repo', REPO], check=True)
    final = api(base + '/releases/' + RELEASE + '/assets?per_page=100')
    binary = next(asset for asset in final if asset['name'] == FILENAME)
    if binary['state'] != 'uploaded' or binary['size'] != TOTAL or binary.get('digest') not in (None, 'sha256:' + EXPECTED):
        raise ValueError('Final release asset verification failed')
    for name in expected_names:
        api(base + '/releases/assets/' + str(names[name]['id']), 'DELETE')
    print('Verified single installer uploaded; temporary parts removed. Release remains draft for publication checks.', flush=True)


if __name__ == '__main__':
    main()
