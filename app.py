# -*- coding: utf-8 -*-
import streamlit as st

st.set_page_config(page_title="影響力｜傳承決策平台", page_icon="📦", layout="wide")

st.title("📦 保單策略規劃｜影響力傳承平台")
st.caption("為高資產家庭設計最適保障結構，讓每一分資源，都能守護最重要的事。")

st.markdown("""
### 你可以做什麼？
1. **3分鐘快篩**：快速看見「傳承準備度」與可能的**流動性缺口**  
2. **缺口與保單模擬**：調整年期與幣別，估算**保額**與**年繳**  
3. **一頁式提案 PDF**：帶走可討論的行動方案，促成家族共識與第二次會面
""")

c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/01_QuickScan.py", label="🚦 開始快篩（3 分鐘）", icon="🚦")
with c2:
    st.page_link("pages/02_GapPlanner.py", label="💧 缺口與保單模擬", icon="💧")
with c3:
    st.page_link("pages/03_Proposal.py", label="📄 下載一頁式提案", icon="📄")

st.divider()
st.markdown("""
**隱私聲明**：本平台不會將資料上傳至第三方伺服器；資料僅保存於您的瀏覽器工作階段。  
**免責聲明**：本工具僅供教育與規劃參考，非法律與稅務意見；請與您的專業顧問確認後再做決策。
""")
