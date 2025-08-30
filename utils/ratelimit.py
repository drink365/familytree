
import os, json, time, hashlib
DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)
STORE = os.path.join(DATA_DIR, "ratelimit.json")

def _load():
    if not os.path.exists(STORE):
        return {}
    try:
        with open(STORE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(d):
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(d, f)

def should_allow(email: str, cooldown: int = 30, content_hash: str | None = None) -> bool:
    """
    True = 允許；False = 在 cooldown 內重複提交。
    以 email 為主鍵；若提供 content_hash，則同內容亦會被視為重複。
    """
    now = int(time.time())
    email_key = (email or "").strip().lower()
    if not email_key:
        return True
    d = _load()
    ent = d.get(email_key, {})
    last_ts = int(ent.get("ts", 0))
    last_hash = ent.get("hash")

    if now - last_ts < cooldown:
        # 在冷卻時間內，再比較內容是否完全相同（更嚴格）
        if not content_hash or content_hash == last_hash:
            return False

    # 更新記錄
    d[email_key] = {"ts": now, "hash": content_hash or ""}
    _save(d)
    return True

def hash_payload(payload: dict) -> str:
    s = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
