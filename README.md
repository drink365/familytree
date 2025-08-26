# Gamification Module (Octalysis-aligned) for 永傳《影響力傳承》平台

這是一個可直接放入 Streamlit 專案的「任務與成就」模組，結合 Octalysis 八大動力，
透過任務、點數、等級、徽章、排行榜，提升使用者「從認知 → 行動 → 會談 → 成交」的動機。

## 快速開始

```bash
pip install streamlit
streamlit run app_gamification.py
```

> 首次啟動會在 `gamification/gamify.db` 建立 SQLite 資料庫。

## 專案結構
```
app_gamification.py
gamification/
  ├─ __init__.py
  ├─ missions.py   # 事件點數與任務清單（含 Octalysis 標記）
  └─ service.py    # SQLite 邏輯：使用者、事件、任務、徽章、排行榜
```

## 與既有平台整合

1. 將 `gamification` 資料夾整個拷貝到你的專案（或以子模組方式引用）。
2. 在任一頁面進行關鍵動作後呼叫：

```python
from gamification.service import award_event
# 例：完成預約
award_event(email=user_email, name=user_name, event="booked_consultation")
```

3. 如需調整點數或任務，修改 `gamification/missions.py`：
   - `EVENT_POINTS` 決定各事件的點數
   - `MISSIONS` 決定任務顯示、建議事件、Octalysis 標籤（CD1~CD8）

## 預設事件（可自由增刪）
- completed_readiness_assessment（完成傳承準備度評測）
- built_legacy_map（建立家族資產地圖）
- uploaded_policies（上傳現有保單）
- booked_consultation（預約顧問）
- completed_values_module（完成價值觀探索）
- invited_family_member（邀請家人共編）
- finished_tax_simulation（稅務試算）
- submitted_pre_meeting_form（預約前問卷）
- watched_video_module（影片＋小測驗）

## 徽章（示例）
- 起步者（≥ 100 分）
- 實踐者（≥ 300 分）
- 影響力領袖（≥ 800 分）
- 資產地圖達人（建立資產地圖 ≥ 3 次）

> 可於 `service._maybe_award_badges` 中新增規則。

## 注意
- 預設將資料庫建在 `gamification/gamify.db`。可用環境變數 `GAMIFY_DB_PATH` 覆蓋。
- 為便於整合，目前登入僅以 Email 做唯一識別。正式版可綁定你平臺的會員系統。
- UI 中文案以客戶端為導向，可依你的品牌語氣微調。
