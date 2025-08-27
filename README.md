
# 影響力傳承平台｜互動原型（Clarity-Focused）

**一句話目的**：把不確定，變成清晰的下一步。

- ✅ 多頁架構（Streamlit `pages/`）
- ✅ SQLite 持久化（users/assets/plan/versions/badges/bookings/meta）
- ✅ 可分享連結：`?user=<token>`；唯讀模式：`?mode=view`
- ✅ 全站共享的「本月諮詢名額」與月度重置
- ✅ 事件追蹤（Plausible 可選，未設定也可執行）
- ✅ 清晰時刻（Clarity Moment）偵測：完成度≥60% + 計出缺口 + 快照/預約/下載其一

## 本地執行
```bash
pip install -r requirements.txt
streamlit run app.py
```
> 首次啟動會在 `data/legacy.db` 建立資料庫。

## 參數
- `?user=<token>`：指定工作區（分享此連結給家族成員即共編）
- `?mode=view`：唯讀模式（關閉所有寫入與預約行為）

## 事件追蹤（選配）
在 Streamlit Secrets 設定：
```toml
PLAUSIBLE_DOMAIN="yourdomain.com"
```
即可送出自訂事件：`Gap Calculated` / `Saved Snapshot` / `Booked Consult` / `Downloaded Report` / `Clarity Moment`
