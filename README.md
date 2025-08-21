# familytree (Streamlit)
家族樹＋法定繼承人（台灣民法）最小可用專案。

## 部署（Streamlit Cloud）
1. 將本專案上傳到 GitHub（根目錄需有：`app.py`, `requirements.txt`, `runtime.txt`）。
2. Streamlit Cloud → Create app：Repository/Branch/Main file path=`app.py` → Deploy。
3. 若卡在 oven：請確認使用 Python 3.11（`runtime.txt`）並於 Manage app → App actions → Restart。

## 法規邏輯（簡化）
- 配偶為當然繼承人。
- 血親順位：直系卑親屬 > 父母 > 兄弟姊妹 > 祖父母。
- 代位：僅直系卑親屬（per stirpes）。不含父母/兄弟姊妹/祖父母之代位。
