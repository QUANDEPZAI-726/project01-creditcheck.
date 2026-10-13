"""Deployment entry point for the intact CreditCheck v0.7 source bundle."""
from pathlib import Path
import hashlib
import runpy
import sys
import tempfile
import zipfile
import streamlit as st

BUNDLE=Path(__file__).resolve().parent/'Project01_CreditCheck_Gemini_v07.zip'

@st.cache_resource
def unpack_bundle():
    expected='68fb1be3126d55a9f530c384fe341702e87a02c6ae680579f5c5f3bed2bdc3c0'
    if hashlib.sha256(BUNDLE.read_bytes()).hexdigest()!=expected:
        raise ValueError('ZIP giao diện không đúng bản v0.7. Upload lại tệp gốc trong gói cập nhật.')
    folder=Path(tempfile.mkdtemp(prefix='creditcheck_ui07_'))
    with zipfile.ZipFile(BUNDLE) as archive:archive.extractall(folder)
    return folder

folder=unpack_bundle()
# Source modules can survive a Streamlit rerun; switch to the new bundle once.
for name in ('core','phase2','phase3','traceability','gemini_service','sample_data','presentation','pdf_report','assisted_io'):
    module=sys.modules.get(name)
    if module is not None and getattr(module,'__file__',None) and not Path(module.__file__).resolve().is_relative_to(folder):
        del sys.modules[name]
sys.path.insert(0,str(folder/'app'))
runpy.run_path(str(folder/'streamlit_app.py'),run_name='__main__')
logo_path = Path(__file__).resolve().parent / (
    "1790301130067_5325247545233387896_g6287506212488219102_01bae03835e1c999662e363ca9e66ec9.jpg"
)

if logo_path.exists():
    st.sidebar.image(str(logo_path), width=160)
else:
    st.sidebar.error("Không tìm thấy ảnh logo")
