"""Deployment entry point for CreditCheck v0.28. Upload with the matching bundle."""
from pathlib import Path
import hashlib
import os
import runpy
import sys
import tempfile
import zipfile
import streamlit as st

DEPLOY_ROOT = Path(__file__).resolve().parent
BUNDLE = DEPLOY_ROOT / 'Project01_CreditCheck_Gemini_v28.zip'
EXPECTED = 'eb2f5c9410674be63825223221f77350be68d12cab78ae9f35e12fd46e79cf11'

@st.cache_resource
def unpack_bundle(expected):
    if not BUNDLE.exists():
        st.error('Thiếu Project01_CreditCheck_Gemini_v28.zip. Upload ZIP này cạnh streamlit_app.py rồi khởi động lại app.')
        st.stop()
    if hashlib.sha256(BUNDLE.read_bytes()).hexdigest() != expected:
        st.error('ZIP và file khởi chạy chưa cùng bản v0.28. Thay cả streamlit_app.py và nguyên Project01_CreditCheck_Gemini_v28.zip trong cùng một lần cập nhật. Không giải nén ZIP này trên GitHub.')
        st.stop()
    folder = Path(tempfile.mkdtemp(prefix='creditcheck_ui28_'))
    with zipfile.ZipFile(BUNDLE) as archive:
        archive.extractall(folder)
    return folder

folder = unpack_bundle(EXPECTED)
for name in ('core','phase2','phase3','traceability','gemini_service','sample_data','presentation','pdf_report','assisted_io','input_security','privacy_excel','ui_shell','design_tokens','assistant_ui','financial_charts','experience','intake_ui'):
    module = sys.modules.get(name)
    if module is not None and getattr(module,'__file__',None) and not Path(module.__file__).resolve().is_relative_to(folder):
        del sys.modules[name]
sys.path.insert(0,str(folder/'app'))
os.environ['CREDITCHECK_DEPLOY_ROOT'] = str(DEPLOY_ROOT)
runpy.run_path(str(folder/'streamlit_app.py'),run_name='__main__')
