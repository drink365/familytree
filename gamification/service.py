# -*- coding: utf-8 -*-
import sqlite3, os, json, time, hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

from .missions import EVENT_POINTS, MISSIONS

DB_PATH = os.environ.get("GAMIFY_DB_PATH", os.path.join(os.path.dirname(__file__), "gamify.db"))

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    con = _connect()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        created_at TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event TEXT,
        points INTEGER,
        meta TEXT,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_missions (
        user_id INTEGER,
        mission_id TEXT,
        status TEXT,
        completed_at TEXT,
        PRIMARY KEY (user_id, mission_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_badges (
        user_id INTEGER,
        badge_code TEXT,
        title TEXT,
        awarded_at TEXT,
        PRIMARY KEY (user_id, badge_code),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    con.commit()
    con.close()

def get_or_create_user(name: str, email: str) -> Dict[str, Any]:
    con = _connect()
    cur = con.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("SELECT id, name, email, created_at FROM users WHERE email = ?", (email.strip().lower(),))
    row = cur.fetchone()
    if row:
        uid, nm, em, ca = row
    else:
        cur.execute("INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)", (name, email.strip().lower(), now))
        con.commit()
        uid = cur.lastrowid
        nm, em, ca = name, email, now
    con.close()
    return {"id": uid, "name": nm, "email": em, "created_at": ca}

def _event_points(event: str, fallback: int = 0) -> int:
    return EVENT_POINTS.get(event, fallback)

def log_event(user_id: int, event: str, points: Optional[int] = None, meta: Optional[Dict[str, Any]] = None) -> int:
    """Returns points awarded."""
    pts = points if points is not None else _event_points(event, 0)
    con = _connect()
    cur = con.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO events (user_id, event, points, meta, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, event, pts, json.dumps(meta or {}, ensure_ascii=False), now))
    con.commit()
    con.close()
    _maybe_award_badges(user_id)
    return pts

def complete_mission(user_id: int, mission_id: str) -> Dict[str, Any]:
    mission = MISSIONS.get(mission_id)
    if not mission:
        raise ValueError("Unknown mission_id")
    # Mark completed
    con = _connect()
    cur = con.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT OR REPLACE INTO user_missions (user_id, mission_id, status, completed_at) VALUES (?, ?, ?, ?)",
                (user_id, mission_id, "completed", now))
    con.commit()
    con.close()
    # Log event
    evt = mission.get("suggested_event")
    pts = mission.get("points", 0)
    awarded = log_event(user_id, evt or f"mission:{mission_id}", pts)
    return {"mission_id": mission_id, "awarded_points": awarded}

def user_points(user_id: int) -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT COALESCE(SUM(points),0) FROM events WHERE user_id = ?", (user_id,))
    val = cur.fetchone()[0] or 0
    con.close()
    return int(val)

def user_level(total_points: int) -> Tuple[int, int, int]:
    """Simple leveling: every 200 pts = +1 level; level 1 starts at 0.
    Returns (level, current, next_threshold)."""
    level = 1 + (total_points // 200)
    next_threshold = level * 200
    current = total_points
    return level, current, next_threshold

def leaderboard(limit: int = 20) -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("""
    SELECT u.id, u.name, u.email, COALESCE(SUM(e.points),0) as pts
    FROM users u
    LEFT JOIN events e ON u.id = e.user_id
    GROUP BY u.id, u.name, u.email
    ORDER BY pts DESC, u.id ASC
    LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    con.close()
    return [{"user_id": r[0], "name": r[1], "email": r[2], "points": int(r[3] or 0)} for r in rows]

def recent_feed(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("""
    SELECT event, points, meta, created_at FROM events
    WHERE user_id = ?
    ORDER BY id DESC
    LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    con.close()
    feed = []
    for ev, pts, meta, ts in rows:
        try:
            meta_obj = json.loads(meta) if meta else {}
        except Exception:
            meta_obj = {}
        feed.append({"event": ev, "points": int(pts or 0), "meta": meta_obj, "created_at": ts})
    return feed

def mission_status(user_id: int) -> Dict[str, str]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT mission_id, status FROM user_missions WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    con.close()
    return {mid: st for (mid, st) in rows}

def available_missions(user_id: int) -> List[Dict[str, Any]]:
    status = mission_status(user_id)
    items = []
    for mid, m in MISSIONS.items():
        st = status.get(mid)
        if st != "completed":
            items.append(m)
    return items

def _maybe_award_badges(user_id: int) -> None:
    """Award badges on thresholds/events; idempotent via upsert key."""
    pts = user_points(user_id)
    rules = [
        ("starter", "起步者", 100),
        ("practitioner", "實踐者", 300),
        ("influencer", "影響力領袖", 800),
        ("legacy_mapper", "資產地圖達人", None, "built_legacy_map", 3),
    ]
    # Count events
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT event, COUNT(*) FROM events WHERE user_id = ? GROUP BY event", (user_id,))
    counts = {ev: c for ev, c in cur.fetchall()}
    # Insert badges
    now = datetime.utcnow().isoformat()
    for code, title, threshold, *rest in rules:
        ok = False
        if threshold is not None:
            ok = pts >= threshold
        else:
            # event-based rule
            ev = rest[0] if len(rest) > 0 else None
            times = rest[1] if len(rest) > 1 else 1
            if ev:
                ok = counts.get(ev, 0) >= times
        if ok:
            cur.execute("INSERT OR IGNORE INTO user_badges (user_id, badge_code, title, awarded_at) VALUES (?, ?, ?, ?)", (user_id, code, title, now))
    con.commit()
    con.close()

def list_badges(user_id: int) -> List[Dict[str, Any]]:
    con = _connect()
    cur = con.cursor()
    cur.execute("SELECT badge_code, title, awarded_at FROM user_badges WHERE user_id = ? ORDER BY awarded_at DESC", (user_id,))
    rows = cur.fetchall()
    con.close()
    return [{"code": r[0], "title": r[1], "awarded_at": r[2]} for r in rows]

def log_custom_points(user_id: int, title: str, points: int, meta: Optional[Dict[str, Any]] = None) -> int:
    return log_event(user_id, f"custom:{title}", points, meta or {})

# Integration helpers (call from other pages)
def award_event(email: str, name: str, event: str, points: Optional[int] = None, meta: Optional[Dict[str, Any]] = None) -> int:
    """Convenience: ensure user exists, then log event. Returns points awarded."""
    u = get_or_create_user(name=name, email=email)
    return log_event(u["id"], event, points, meta)
