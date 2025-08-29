
import os, csv, smtplib, ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header

# Try Streamlit secrets first
try:
    import streamlit as st
    _SECRETS = dict(st.secrets) if hasattr(st, "secrets") else {}
except Exception:
    _SECRETS = {}

DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "contacts.csv")

def save_contact(payload: dict) -> None:
    exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        fields = ["ts","name","email","phone","topic","when_date","when_ampm","msg"]
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        row = {k: ("" if payload.get(k) is None else str(payload.get(k))) for k in fields}
        row["ts"] = datetime.now().isoformat(timespec="seconds")
        w.writerow(row)

def _get(k, default=""):
    return _SECRETS.get(k) or os.environ.get(k, default)

def _smtp_config():
    return dict(
        host   = _get("SMTP_HOST"),
        port   = int(_get("SMTP_PORT", "587")),
        user   = _get("SMTP_USER"),
        pwd    = _get("SMTP_PASS"),
        sender = _get("SMTP_SENDER") or _get("SMTP_USER"),
        to     = _get("CONTACT_TO") or _get("SMTP_TO") or _get("SMTP_SENDER") or _get("SMTP_USER"),
        tls    = str(_get("SMTP_TLS","1")).lower() not in ("0","false","no"),
    )

def _hdr(s: str) -> str:
    return str(Header(s, "utf-8"))

def send_email(payload: dict) -> bool:
    cfg = _smtp_config()
    # Incomplete config -> silently skip
    if not all([cfg["host"], cfg["user"], cfg["pwd"], cfg["sender"], cfg["to"]]):
        return False

    subject = f"[影響力平台] 新的聯絡需求：{payload.get('name','')}｜{payload.get('topic','')}"
    lines = [
        f"提交時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"稱呼：{payload.get('name','')}",
        f"Email：{payload.get('email','')}",
        f"電話：{payload.get('phone','')}",
        f"主題：{payload.get('topic','')}",
        f"期望：{payload.get('when_date','')} {payload.get('when_ampm','')}",
        f"訊息：{(payload.get('msg') or '').strip()}",
    ]
    body = "\n".join(lines)

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((_hdr("影響力平台"), cfg["sender"]))

    # multiple recipients: comma or semicolon
    to_list = [e.strip() for e in str(cfg["to"]).replace(";", ",").split(",") if e.strip()]
    msg["To"] = ", ".join(to_list)

    # TLS (587) vs SSL (465)
    if cfg["tls"]:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls(context=context)
            server.login(cfg["user"], cfg["pwd"])
            server.sendmail(cfg["sender"], to_list, msg.as_string())
    else:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context) as server:
            server.login(cfg["user"], cfg["pwd"])
            server.sendmail(cfg["sender"], to_list, msg.as_string())
    return True
