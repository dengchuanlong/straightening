"""Index the portable model-analysis release; omit local binary model bundles."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
files=[]
for folder in ['scripts','data','analysis','figures','tables']:
    files.extend(p for p in (ROOT/folder).glob('**/*') if p.is_file()
                 and '__pycache__' not in p.parts and p.name not in ['manifest.json','revision_release_manifest.json'])
files.extend(p for p in [ROOT/'reproduce.py',ROOT/'requirements.txt',ROOT/'README_REPRODUCIBILITY.md',ROOT/'.gitignore'] if p.exists())
result=json.loads((ROOT/'analysis/results.json').read_text(encoding='utf-8'))
out=dict(schema='portable-straightening-revision-manifest-v1',training_seeds=[40,41,42],paired_bootstrap_seed=43,
    data_origin='AUTHOR_SUPPLIED_PROVENANCE_PENDING',native_fe_provenance_verified=False,
    results_sha256=hashlib.sha256((ROOT/'analysis/results.json').read_bytes()).hexdigest(),
    files=[dict(path=str(p.relative_to(ROOT)).replace('\\','/'),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(set(files))])
(ROOT/'analysis/revision_release_manifest.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(dict(files=len(out['files']),bytes=sum(p['bytes'] for p in out['files']))))
