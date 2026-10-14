"""Deployment entry point for CreditCheck v0.13."""
from pathlib import Path
import hashlib
import os
import runpy
import sys
import tempfile
import zipfile
import streamlit as st

DEPLOY_ROOT = Path(__file__).resolve().parent
BUNDLE = DEPLOY_ROOT / 'Project01_CreditCheck_Gemini_v13.zip'

@st.cache_resource
def unpack_bundle():
    expected = '2df1d26959cc2a6111b3d4e87fc25f91e842d5955c871931bc697aa41bfd0664'
    if hashlib.sha256(BUNDLE.read_bytes()).hexdigest() != expected:
        raise ValueError('ZIP giao diện không đúng bản v0.13. Upload lại nguyên ZIP trong gói cập nhật.')
    folder = Path(tempfile.mkdtemp(prefix='creditcheck_ui13_'))
    with zipfile.ZipFile(BUNDLE) as archive:
        archive.extractall(folder)
    return folder

folder = unpack_bundle()
for name in ('core','phase2','phase3','traceability','gemini_service','sample_data','presentation','pdf_report','assisted_io','input_security','privacy_excel','ui_shell','design_tokens'):
    module = sys.modules.get(name)
    if module is not None and getattr(module,'__file__',None) and not Path(module.__file__).resolve().is_relative_to(folder):
        del sys.modules[name]
sys.path.insert(0,str(folder/'app'))
os.environ['CREDITCHECK_DEPLOY_ROOT'] = str(DEPLOY_ROOT)
runpy.run_path(str(folder/'streamlit_app.py'),run_name='__main__')
