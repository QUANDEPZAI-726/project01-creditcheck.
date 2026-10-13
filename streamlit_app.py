from pathlib import Path
import hashlib
import runpy
import tempfile
import zipfile
import streamlit as st

BUNDLE = Path(__file__).resolve().parent / "Project01_CreditCheck_Gemini_v05.zip"

@st.cache_resource
def unpack_bundle():
    expected = "6d51b5567d60a92b04d4b5851806b708553380d42fc399b6726edefe2d1267f4"
    if hashlib.sha256(BUNDLE.read_bytes()).hexdigest() != expected:
        raise ValueError("ZIP không đúng phiên bản v0.5.")

    folder = Path(tempfile.mkdtemp(prefix="creditcheck_"))
    with zipfile.ZipFile(BUNDLE) as archive:
        archive.extractall(folder)
    return folder

runpy.run_path(
    str(unpack_bundle() / "streamlit_app.py"),
    run_name="__main__"
)
