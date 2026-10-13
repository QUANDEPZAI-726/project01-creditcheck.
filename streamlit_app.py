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

import sys
import re

folder = unpack_bundle()
sys.path.insert(0, str(folder / "app"))

import gemini_service as gs

if not hasattr(gs.GeminiClient, "_original_generate"):
    gs.GeminiClient._original_generate = gs.GeminiClient.generate

def diagnostic_generate(self, prompt):
    try:
        return self._original_generate(prompt)
    except gs.GeminiError as error:
        cause = error.__context__
        if cause is None:
            raise

        detail = str(getattr(cause, "message", None) or str(cause))
        detail = detail.replace(self.api_key, "[KEY HIDDEN]")
        detail = re.sub(
            r"(?:AIza[A-Za-z0-9_-]+|AQ\.[A-Za-z0-9_.-]+)",
            "[KEY HIDDEN]",
            detail
        )
        status = getattr(cause, "code", None) or type(cause).__name__
        raise gs.GeminiError(
            f"Gemini [{status}]: {detail[:500]}"
        ) from None

gs.GeminiClient.generate = diagnostic_generate

runpy.run_path(
    str(folder / "streamlit_app.py"),
    run_name="__main__"
)
