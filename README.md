
# 影響力傳承平台｜家族樹擴充版（Clarity-Focused）

**一句話目的**：把不確定，變成清晰的下一步。

## 功能
- 多頁架構（首頁＋資產盤點、策略模擬、快照與匯出、家族共編、預約諮詢、知識補給、差異對比）
- **家族樹**：新增成員、父母→子女關係、縮排樹視圖（無需外部套件）
- **故事與事件**：人生事件（結婚、移居、創業、出售等）→ 自動產生「建議下一步」；角色指派
- SQLite 持久化；分享工作區 `?user=<token>`；唯讀 `?mode=view`
- 全站共享名額（每月自動重置）
- 事件追蹤（Plausible 可選）；清晰時刻（Clarity Moment）偵測
- 雙版本報告（內部版/分享版，HTML + 原生 PDF）

## 執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

在 Secrets 設定 `PLAUSIBLE_DOMAIN="yourdomain.com"` 可啟用事件追蹤。
