
import os, csv, smtplib, ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr

DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "contacts.csv")

def save_contact(payload: dict) -> None:
    exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ts","name","email","phone","topic","when_date","when_ampm","msg"])
        if not exists:
            w.writeheader()
        payload = {k: ("" if v is None else str(v)) for k, v in payload.items()}
        payload["ts"] = datetime.now().isoformat(timespec="seconds")
        w.writerow(payload)

def _smtp_config_from_env():
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pwd  = os.environ.get("SMTP_PASS")
    port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ.get("SMTP_SENDER", user or "")
    to = os.environ.get("CONTACT_TO", os.environ.get("SMTP_TO", sender or ""))
    tls = os.environ.get("SMTP_TLS", "1") not in ("0","false","False")
    return dict(host=host, user=user, pwd=pwd, port=port, sender=sender, to=to, tls=tls)

def send_email(payload: dict) -> bool:
    cfg = _smtp_config_from_env()
    if not all([cfg["host"], cfg["user"], cfg["pwd"], cfg["sender"], cfg["to"]]):
        return False  # not configured
    subject = f"[影響力平台] 新的聯絡需求：{payload.get('name','')}｜{payload.get('topic','')}"
    lines = [
        f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"稱呼：{payload.get('name','')}",
        f"Email：{payload.get('email','')}",
        f"電話：{payload.get('phone','')}",
        f"主題：{payload.get('topic','')}",
        f"期望日期：{payload.get('when_date','')} {payload.get('when_ampm','')}",
        f"訊息：{payload.get('msg','').strip()}",
    ]
    body = "\n".join(lines)

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr(("影響力平台", cfg["sender"]))
    msg["To"] = cfg["to"]

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
        if cfg["tls"]:
            server.starttls(context=context)
        server.login(cfg["user"], cfg["pwd"])
        server.sendmail(cfg["sender"], [cfg["to"]], msg.as_string())
    return True
