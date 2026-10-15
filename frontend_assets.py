"""Register a fresh component when its bundled assets change."""

from functools import lru_cache
import hashlib
import json
from pathlib import Path

import streamlit as st


@lru_cache(maxsize=8)
def _register(name: str, html: str, css: str, js: str):
    digest = hashlib.sha256(json.dumps([html, css, js]).encode()).hexdigest()
    return st.components.v2.component(
        name=f"{name}_{digest}", html=html, css=css, js=js,
    )


def register_frontend(name: str, html: str, frontend: Path, bundle: str):
    return _register(
        name, html,
        (frontend / "network.css").read_text(encoding="utf-8"),
        (frontend / "dist" / bundle).read_text(encoding="utf-8"),
    )
