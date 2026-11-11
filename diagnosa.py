import importlib
import os
import sys
import traceback
from importlib import metadata

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))

st.title("🔧 Diagnosa Aplikasi")

# ---------- 1) INFO ENVIRONMENT ----------
st.subheader("1) Info environment")
st.write("Python:", sys.version)
st.write("Streamlit:", st.__version__)
st.write("Folder file ini:", HERE)
st.write("Isi folder:", sorted(os.listdir(HERE)))
st.write("requirements.txt ada?", os.path.exists(os.path.join(HERE, "requirements.txt")))

PACKAGES = [  # (nama di pip, nama untuk import)
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("openpyxl", "openpyxl"),
    ("xlsxwriter", "xlsxwriter"),
    ("folium", "folium"),
    ("streamlit-folium", "streamlit_folium"),
]
for dist_name, module_name in PACKAGES:
    try:
        importlib.import_module(module_name)
        st.success(f"{dist_name} OK (versi {metadata.version(dist_name)})")
    except Exception as e:
        st.error(f"{dist_name} GAGAL: {type(e).__name__}: {e}")

fitur = ["rerun", "data_editor", "tabs", "download_button", "file_uploader"]
st.write("Fitur Streamlit yang dipakai app:", {f"st.{f}": hasattr(st, f) for f in fitur})

# ---------- 2) JALANKAN app.py DAN TAMPILKAN ERROR-NYA ----------
st.subheader("2) Menjalankan app.py")
app_path = os.path.join(HERE, "app.py")

if not os.path.exists(app_path):
    st.error("app.py tidak ditemukan di folder yang sama dengan file ini. Cek nama & lokasi file di repo.")
else:
    st.set_page_config = lambda *args, **kwargs: None  # app.py memanggilnya, padahal sudah ada elemen di atas
    st.divider()
    try:
        with open(app_path, encoding="utf-8") as f:
            code = compile(f.read(), app_path, "exec")
        exec(code, {"__name__": "__main__", "__file__": app_path})
    except Exception:
        st.error("❌ app.py gagal dijalankan. Salin seluruh teks di bawah ini dan kirim ke saya:")
        st.code(traceback.format_exc())
