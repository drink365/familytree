
# -*- coding: utf-8 -*-
import streamlit as st
import sqlite3, os, json, uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

# ---------- Timezone ----------
TZ = timezone(timedelta(hours=8))  # Asia/Taipei

# ---------- Paths & DB ----------
ROOT = os.path.dirname(__file__)
DB_DIR = os.path.join(ROOT, "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "legacy.db")

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id TEXT PRIMARY KEY, family_name TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS assets(
        user_id TEXT PRIMARY KEY, json TEXT, updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS plans(
        user_id TEXT PRIMARY KEY, json TEXT, updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS versions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, family_name TEXT,
        assets_json TEXT, plan_json TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS badges(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, name TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS meta(
        key TEXT PRIMARY KEY, value TEXT)""")
    conn.commit()
    return conn

CONN = init_db()

# ---------- Meta (global) ----------
def meta_get(key, default=None):
    c = CONN.cursor()
    c.execute("SELECT value FROM meta WHERE key=?", (key,))
    row = c.fetchone()
    return (json.loads(row[0]) if row else default)

def meta_set(key, value):
    c = CONN.cursor()
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, json.dumps(value)))
    CONN.commit()

def setup_monthly_challenge():
    now = datetime.now(TZ)
    deadline = meta_get("consult_deadline")
    if deadline: deadline = datetime.fromisoformat(deadline)
    if not deadline or now > deadline:
        first_of_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        last = first_of_next - timedelta(seconds=1)
        last = last.replace(hour=23, minute=59, second=59, microsecond=0)
        meta_set("consult_deadline", last.isoformat())
        meta_set("consult_slots_total", 10)
        meta_set("consult_slots_left", 10)

setup_monthly_challenge()

def consult_state():
    return {
        "deadline": datetime.fromisoformat(meta_get("consult_deadline")),
        "slots_total": meta_get("consult_slots_total", 10),
        "slots_left": meta_get("consult_slots_left", 10),
    }

def consult_decrement():
    left = meta_get("consult_slots_left", 0)
    if left <= 0: return False
    meta_set("consult_slots_left", left - 1)
    return True

# ---------- User workspace ----------
def get_qs():
    try: return dict(st.query_params)
    except Exception: return st.experimental_get_query_params()

def set_qs(params: dict):
    try:
        st.query_params.clear(); st.query_params.update(params)
    except Exception:
        st.experimental_set_query_params(**params)

def get_or_create_user_id() -> str:
    qs = get_qs()
    mode = qs.get("mode")  # may be view/edit
    if isinstance(mode, list): mode = mode[0] if mode else None
    incoming = qs.get("user")
    if isinstance(incoming, list): incoming = incoming[0] if incoming else None
    if incoming:
        st.session_state["user_id"] = incoming
        st.session_state["mode"] = mode or "edit"
        return incoming
    uid = "u_" + str(uuid.uuid4())[:8]
    st.session_state["user_id"] = uid
    st.session_state["mode"] = mode or "edit"
    qs["user"] = uid
    set_qs(qs)
    return uid

USER_ID = get_or_create_user_id()

def is_view_mode() -> bool:
    return st.session_state.get("mode") == "view"

# ---------- CRUD ----------
DEFAULT_ASSETS = {"公司股權":0,"不動產":0,"金融資產":0,"保單":0,"海外資產":0,"其他":0}
DEFAULT_PLAN   = {"股權給下一代":40,"保單留配偶":30,"慈善信託":10,"留現金緊急金":20}

def user_get():
    c = CONN.cursor()
    c.execute("SELECT id,family_name,created_at FROM users WHERE id=?", (USER_ID,))
    return c.fetchone()

def user_create_if_missing():
    if not user_get():
        c = CONN.cursor()
        c.execute("INSERT INTO users(id,family_name,created_at) VALUES(?,?,?)",
                  (USER_ID,"",datetime.now(TZ).isoformat()))
        CONN.commit()

def family_name_get() -> str:
    row = user_get(); return row[1] if row else ""

def family_name_set(name: str):
    if is_view_mode(): return
    c = CONN.cursor()
    c.execute("UPDATE users SET family_name=? WHERE id=?", (name, USER_ID)); CONN.commit()

def assets_get() -> Dict:
    c = CONN.cursor(); c.execute("SELECT json FROM assets WHERE user_id=?", (USER_ID,))
    row = c.fetchone(); return (json.loads(row[0]) if row else DEFAULT_ASSETS.copy())

def assets_set(data: Dict):
    if is_view_mode(): return
    c = CONN.cursor()
    c.execute("INSERT OR REPLACE INTO assets(user_id,json,updated_at) VALUES(?,?,?)",
              (USER_ID, json.dumps(data), datetime.now(TZ).isoformat()));
    CONN.commit()

def plan_get() -> Dict:
    c = CONN.cursor(); c.execute("SELECT json FROM plans WHERE user_id=?", (USER_ID,))
    row = c.fetchone(); return (json.loads(row[0]) if row else DEFAULT_PLAN.copy())

def plan_set(data: Dict):
    if is_view_mode(): return
    c = CONN.cursor()
    c.execute("INSERT OR REPLACE INTO plans(user_id,json,updated_at) VALUES(?,?,?)",
              (USER_ID, json.dumps(data), datetime.now(TZ).isoformat()));
    CONN.commit()

def version_insert(family, assets, plan):
    if is_view_mode(): return
    c = CONN.cursor()
    c.execute("""INSERT INTO versions(user_id,family_name,assets_json,plan_json,created_at)
                 VALUES(?,?,?,?,?)""",
              (USER_ID, family, json.dumps(assets), json.dumps(plan), datetime.now(TZ).isoformat()))
    CONN.commit()

def versions_list():
    c = CONN.cursor()
    c.execute("""SELECT family_name,assets_json,plan_json,created_at FROM versions
                 WHERE user_id=? ORDER BY id DESC""", (USER_ID,))
    rows = c.fetchall(); out = []
    for fam, aj, pj, ts in rows:
        out.append({"family": fam, "assets": json.loads(aj),
                    "plan": json.loads(pj), "time": datetime.fromisoformat(ts)})
    return out

def badge_add(name: str):
    if is_view_mode(): return
    c = CONN.cursor(); c.execute("SELECT 1 FROM badges WHERE user_id=? AND name=?", (USER_ID,name))
    if c.fetchone(): return
    c.execute("INSERT INTO badges(user_id,name,created_at) VALUES(?,?,?)",
              (USER_ID, name, datetime.now(TZ).isoformat())); CONN.commit()

def badges_list():
    c = CONN.cursor(); c.execute("SELECT name FROM badges WHERE user_id=? ORDER BY id", (USER_ID,))
    return [r[0] for r in c.fetchall()]

def booking_insert():
    if is_view_mode(): return False
    c = CONN.cursor()
    c.execute("INSERT INTO bookings(user_id,created_at) VALUES(?,?)",
              (USER_ID, datetime.now(TZ).isoformat())); CONN.commit(); return True

# ---------- Analytics (Plausible optional) ----------
def inject_analytics():
    try:
        domain = st.secrets["PLAUSIBLE_DOMAIN"]
        import streamlit.components.v1 as components
        components.html(
            f'<script defer data-domain="{domain}" src="https://plausible.io/js/script.js"></script>', height=0)
    except Exception:
        pass

def plausible_event(name: str, props: dict | None = None):
    try:
        import json as _json
        import streamlit.components.v1 as components
        payload = _json.dumps(props or {})
        components.html(
            f'<script>window.plausible && window.plausible({_json.dumps(name)}, {{props: {payload}}});</script>',
            height=0,
        )
    except Exception:
        pass

# ---------- Clarity computation ----------
def current_gap_estimate():
    assets = st.session_state.get("assets", DEFAULT_ASSETS.copy())
    total_asset = sum(assets.values())
    if total_asset <= 0: return None
    plan = st.session_state.get("plan", DEFAULT_PLAN.copy())
    base_rate = st.session_state.get("risk_rate_with_plan", 0.10)
    effective_rate = max(0.05, base_rate - (plan["慈善信託"]/100)*0.03)
    est_tax = int(total_asset * 10_000 * effective_rate)
    cash_liq = int(total_asset * 10_000 * (
        plan["留現金緊急金"]/100 + plan["保單留配偶"]/100*0.8
    ))
    gap = max(0, est_tax - cash_liq)
    return {"total_asset": total_asset, "est_tax": est_tax, "cash_liq": cash_liq,
            "gap": gap, "plan_charity_pct": plan["慈善信託"]}

def progress_score():
    checks = [
        st.session_state.get("mission_ack", False),
        st.session_state.get("profile_done", False),
        st.session_state.get("assets_done", False),
        st.session_state.get("plan_done", False),
        st.session_state.get("quiz_done", False),
        st.session_state.get("advisor_booked", False),
    ]
    return int(sum(map(int, checks)) / 6 * 100)

def maybe_fire_clarity_moment():
    est = current_gap_estimate()
    if not est: return
    prog = progress_score()
    has_version = len(versions_list()) > 0
    booked = bool(st.session_state.get("advisor_booked", False))
    if prog >= 60 and est["gap"] >= 0 and (has_version or booked):
        plausible_event("Clarity Moment", {
            "gap": est["gap"], "progress": prog,
            "has_version": int(has_version), "booked": int(booked),
        })

# ---------- UI helpers ----------
def section_title(emoji, title): st.markdown(f"### {emoji} {title}")
def guidance_note(text): st.markdown(f":bulb: **引導**：{text}")
def chip(text):
    st.markdown(f"<span style='padding:4px 8px;border-radius:12px;border:1px solid #ddd;'> {text} </span>",
                unsafe_allow_html=True)

RANDOM_TIPS = [
    "家族憲章可明確價值觀與決策機制，降低紛爭風險。",
    "跨境資產需同步考量不同稅制的課稅時點與估值規則。",
    "保單身故金可快速補足遺產稅與流動性缺口。",
    "先做資產盤點，再決定工具；先談價值觀，再定分配比例。",
    "信託可把『錢給誰、何時給、給多少、何條件下給』寫清楚。",
    "『用不完的錢如何安心交棒』是第三階段的關鍵提問。",
]

def unlock_random_tip():
    tips = st.session_state.setdefault("tips_unlocked", [])
    left = [t for t in RANDOM_TIPS if t not in tips]
    if not left: return None
    import random; tip = random.choice(left)
    tips.append(tip); st.session_state["tips_unlocked"] = tips; return tip

def init_session_defaults():
    user_create_if_missing()
    ss = st.session_state
    ss.setdefault("mission_ack", False)
    ss.setdefault("profile_done", False)
    ss.setdefault("assets_done", False)
    ss.setdefault("plan_done", False)
    ss.setdefault("quiz_done", False)
    ss.setdefault("advisor_booked", False)
    ss.setdefault("family_name", family_name_get())
    ss.setdefault("assets", assets_get())
    ss.setdefault("plan", plan_get())
    ss.setdefault("risk_rate_no_plan", 0.18)
    ss.setdefault("risk_rate_with_plan", 0.10)

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🧭 目前進度")
        prog = progress_score()
        st.progress(prog, text=f"完成度 {prog}%")
        st.caption("完成各區塊互動以提升完成度。")

        st.markdown("## 🏅 徽章")
        got = badges_list()
        if not got: st.caption("尚未解鎖徽章。")
        else:
            for b in got: chip(f"🏅 {b}")

        st.divider()
        st.markdown("**邀請家族成員共建**")
        base = ""  # 留空由瀏覽器自動補全
        st.code(f"{base}?user={USER_ID}")
        st.caption("唯讀連結：在上方網址後加上 `&mode=view`。")
