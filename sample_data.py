"""Sample loading only. No HTTP server or global user state."""
import json
from pathlib import Path
from core import make_state, ensure
from traceability import sync
ROOT=Path(__file__).resolve().parent.parent
def load_sample(cid):
    ensure(cid in ['HS01','HS02','HS03','HS04','HS05'],'Hồ sơ mẫu không tồn tại.')
    folder=ROOT/'runtime/cases'/cid
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    files={d['source_type']:(folder/d['path']).read_bytes() for d in manifest['documents'] if d['available']}
    coverage=next(d for d in manifest['documents'] if d['source_type']=='bank_statement')
    state=make_state(cid,files,coverage if coverage['available'] else None)
    sync(state)
    return state
