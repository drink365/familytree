
import os
import base64
from io import BytesIO
from PIL import Image, ImageFilter
import streamlit as st

@st.cache_data(show_spinner=False)
def logo_b64_highres(path: str, target_px_width: int, mtime: float, size: int) -> str:
    """將 Logo 轉為高解析 base64（以檔案 mtime/size 作為 cache key）"""
    img = Image.open(path).convert("RGBA")
    if img.width < target_px_width:
        ratio = target_px_width / img.width
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=2))
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")
