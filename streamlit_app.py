"""Deployment entry point for the intact CreditCheck v0.6 source bundle."""
from pathlib import Path
import hashlib
import runpy
import sys
import tempfile
import zipfile
import streamlit as st

BUNDLE=Path(__file__).resolve().parent/'Project01_CreditCheck_Gemini_v06.zip'

@st.cache_resource
def unpack_bundle():
    expected='1a0fd9ef7e4821089fb59abce7141a6038d7ad6d1505d67ea6ad45c680475a1e'
    if hashlib.sha256(BUNDLE.read_bytes()).hexdigest()!=expected:
        raise ValueError('ZIP giao diện không đúng bản v0.6. Upload lại tệp gốc trong gói cập nhật.')
    folder=Path(tempfile.mkdtemp(prefix='creditcheck_ui06_'))
    with zipfile.ZipFile(BUNDLE) as archive:archive.extractall(folder)
    return folder

folder=unpack_bundle()
# Source modules can survive a Streamlit rerun; switch to the new bundle once.
for name in ('core','phase2','phase3','traceability','gemini_service','sample_data','presentation','pdf_report'):
    module=sys.modules.get(name)
    if module is not None and getattr(module,'__file__',None) and not Path(module.__file__).resolve().is_relative_to(folder):
        del sys.modules[name]
sys.path.insert(0,str(folder/'app'))
runpy.run_path(str(folder/'streamlit_app.py'),run_name='__main__')
