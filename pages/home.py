
import streamlit as st

def render():
    st.title("🏠 首頁")
    st.write("這是永傳家族傳承教練的首頁。左側可切換到各模組。")
    with st.expander("平台效能提示（為什麼這版切頁比較快？）", expanded=True):
        st.markdown("""
- **Lazy-Load**：只有當頁面真正被開啟時，才會載入該頁的重型元件（例如 Graphviz）。  
- **Submit Form**：所有輸入欄位改為**送出後再重算**，避免每打一個字整頁重跑。  
- **Cache**：影像、家族圖、表格轉換都快取，沒變更資料就不重算。  
        """)
