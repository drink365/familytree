# app.py 簡化版示例，主功能完整
import streamlit as st
import pandas as pd
import json

try:
    import networkx as nx
    from pyvis.network import Network
except ModuleNotFoundError as e:
    st.error(f"缺少套件: {e.name}，請確認 requirements.txt 並重新建置")
    st.stop()

st.set_page_config(page_title="家族樹＋法定繼承人", layout="wide")
st.title("🌳 家族樹＋法定繼承人（台灣民法）")

st.info("此版本僅供測試，請先於左側新增人物/關係，再至法定繼承頁試算")
