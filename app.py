import streamlit as st
from datetime import date

# --------------------------
# 基本設定
# --------------------------
st.set_page_config(
    page_title="《影響力》傳承策略平台",
    page_icon="🏛️",
    layout="wide"
)

# --------------------------
# CSS
# --------------------------
CSS = """
<style>
.block-container { padding-top: 2.0rem; padding-bottom: 3.0rem; }
.center { text-align: center; }
.subtle { color: #6b7280; }
.value-card {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 18px;
  height: 100%;
  background: #fff;
}
.spacer { height: 12px; }
.footer {
  margin-top: 32px;
  color: #6b7280;
  font-size: 0.95rem;
  text-align: center;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --------------------------
# 頁面狀態
# --------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "home"

def go(page_key: str):
    st.session_state["page"] = page_key
    st.rerun()

# --------------------------
# 側邊欄（保留原本的）
# --------------------------
with st.sidebar:
    st.title("《影響力》傳承策略平台")
    if st.button("🏠 首頁", use_container_width=True):
        go("home")
    if st.button("📅 預約諮詢", use_container_width=True):
        go("booking")
    st.markdown("---")
    st.markdown("由永傳家族辦公室專業團隊打造")
    st.markdown("聯絡信箱：123@gracefo.com")

# --------------------------
# 首頁
# --------------------------
def render_home():
    st.markdown("<div class='center'><h1>留下的不只財富，更是愛與責任</h1></div>", unsafe_allow_html=True)
    st.markdown("<h3 class='center subtle'>讓每一分資源，守護最重要的人</h3>", unsafe_allow_html=True)
    st.markdown("<h4 class='center subtle'>智慧工具 × 專業顧問 × 家族永續</h4>", unsafe_allow_html=True)
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)

    # 兩顆主按鈕
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        colA, colB = st.columns(2)
        with colA:
            if st.button("回到首頁", use_container_width=True):
                go("home")
        with colB:
            if st.button("📅 預約諮詢", use_container_width=True):
                go("booking")

    st.markdown("---")

    # 三大價值主張
    st.markdown("### 我們的核心價值")
    v1, v2, v3 = st.columns(3)
    with v1:
        st.markdown("<div class='value-card'>", unsafe_allow_html=True)
        st.markdown("#### 🏛️ 專業合規")
        st.write("法律、稅務與財務整合思考，讓傳承結構合法且穩健。")
        st.markdown("</div>", unsafe_allow_html=True)
    with v2:
        st.markdown("<div class='value-card'>", unsafe_allow_html=True)
        st.markdown("#### 🤖 智能工具")
        st.write("AI 輔助盤點與模擬，降低溝通成本，提升提案效率。")
        st.markdown("</div>", unsafe_allow_html=True)
    with v3:
        st.markdown("<div class='value-card'>", unsafe_allow_html=True)
        st.markdown("#### 🌳 永續家族")
        st.write("不只傳承財富，更延續價值觀與家族共識。")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='footer'>由永傳家族辦公室專業團隊打造｜聯絡信箱：123@gracefo.com</div>",
        unsafe_allow_html=True
    )

# --------------------------
# 預約諮詢
# --------------------------
def render_booking():
    st.markdown("### 📅 預約諮詢")
    st.caption("請留下您的聯絡資訊，我們將盡快與您安排時間。")

    with st.form("booking_form"):
        name = st.text_input("姓名*", value="")
        phone = st.text_input("手機*", value="")
        email = st.text_input("Email*", value="")
        meet_date = st.date_input("希望日期", value=date.today())
        slot = st.selectbox("時段偏好", options=["上午","下午","不限"], index=2)
        channel = st.selectbox("諮詢方式", options=["視訊","電話","面談（台北）"], index=0)
        need = st.text_area("想討論的重點", height=100, placeholder="例如：退休現金流、長照、跨境資產、子女公平…")
        consent = st.checkbox("我同意提供上述資訊以安排諮詢", value=True)
        submitted = st.form_submit_button("送出預約")

    if submitted:
        if not (name and phone and email and consent):
            st.error("請完整填寫必填欄位並勾選同意。")
        else:
            st.success("✅ 已收到您的預約，我們會盡快與您聯繫。")
            st.markdown(
                f"- 姓名：{name}\n"
                f"- 手機：{phone}\n"
                f"- Email：{email}\n"
                f"- 日期：{meet_date}\n"
                f"- 時段：{slot}\n"
                f"- 方式：{channel}\n"
                f"- 重點：{need if need else '（未填）'}"
            )
            if st.button("回到首頁"):
                go("home")

    st.markdown(
        "<div class='footer'>由永傳家族辦公室專業團隊打造｜聯絡信箱：123@gracefo.com</div>",
        unsafe_allow_html=True
    )

# --------------------------
# 主畫面
# --------------------------
if st.session_state["page"] == "home":
    render_home()
elif st.session_state["page"] == "booking":
    render_booking()
else:
    render_home()
