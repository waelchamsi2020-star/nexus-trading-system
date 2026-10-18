"""Read the bundled school reference. Text never becomes executable code."""
import hashlib
import json
import sys
from pathlib import Path


def catalog(root=None):
    base=Path(root) if root is not None else Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[2]))
    folder=base/'docs/school-catalog'
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for name in ('catalog.json','reference-ar.md','reference-en.md'):
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=manifest['files'].get(name):
            raise ValueError('School reference fingerprint mismatch')
    value=json.loads((folder/'catalog.json').read_text(encoding='utf-8'))
    entries=value.get('schools',[])
    if value.get('schema_version')!=1 or len(entries)!=58 or len({s['id'] for s in entries})!=58:
        raise ValueError('Incomplete school reference')
    if value.get('catalog_version')!=manifest.get('catalog_version'):
        raise ValueError('School reference version mismatch')
    for category,count in (('technical',30),('fundamental',20),('approach',8)):
        if [s['order'] for s in entries if s['category']==category]!=list(range(1,count+1)):
            raise ValueError('School reference category order mismatch')
    return value


def schools(root=None):
    return catalog(root)['schools']
