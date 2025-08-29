
import streamlit as st
from datetime import datetime
from utils.pdf_utils import build_branded_pdf_bytes, p, h2, title, spacer
def render():
    st.subheader("❤️ 價值觀探索（PDF）")
    c1, c2, c3 = st.columns(3)
    with c1:
        care = st.multiselect("想優先照顧", ["配偶", "子女", "父母", "夥伴", "公益"], default=["子女","配偶"])
    with c2:
        principles = st.multiselect("重要原則", ["公平", "感恩", "責任", "創新", "永續"], default=["公平","責任"])
    with c3:
        ways = st.multiselect("傳承方式", ["等分", "需求導向", "信託分期", "股權分流", "教育基金", "公益信託"], default=["信託分期","股權分流","教育基金"])
    bullets = []
    if "公平" in principles: bullets.append("重大資產依『公平＋公開』原則分配，避免模糊地帶。")
    if "責任" in principles: bullets.append("與公司治理連動：經營權與所有權分流，避免角色衝突。")
    if "信託分期" in ways:   bullets.append("子女教育/生活費以信託分期給付，達成『照顧但不溺愛』。")
    if "教育基金" in ways:   bullets.append("設立教育基金，明確用途與提領條件，受託人監管。")
    if "公益信託" in ways or "公益" in care: bullets.append("提撥固定比例成立公益信託，作為家族影響力的延伸。")
    if not bullets: bullets.append("將價值觀轉譯為具體的分配規則與審核條件，以降低爭議。")
    st.write({"優先照顧": ", ".join(care) if care else "（未選）","重要原則": ", ".join(principles) if principles else "（未選）","傳承方式": ", ".join(ways) if ways else "（未選）"})
    for b in bullets: st.markdown(f"- {b}")
    flow = [title("價值觀 × 行動準則"), spacer(6), h2("探索重點"), p(f"優先照顧：{', '.join(care) if care else '未選'}"), p(f"重要原則：{', '.join(principles) if principles else '未選'}"), p(f"傳承方式：{', '.join(ways) if ways else '未選'}"), spacer(6), h2("建議家規 × 資金規則（示意）")] + [p(f"- {b}") for b in bullets]
    pdf = build_branded_pdf_bytes(flow).strftime("%Y/%m/%d")}','永傳家族辦公室  gracefo.com'],
        body_flow=flow
    )
    st.download_button("⬇️ 下載價值觀 PDF", data=pdf, file_name=f"value_charter_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")
