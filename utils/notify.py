# -*- coding: utf-8 -*-
"""
通知工具：儲存聯絡表單，並以 SMTP 寄送通知信（UTF-8 安全）
"""
import os
import csv
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from email.header import Header

# 優先讀取 Streamlit secrets；若不存在再讀環境變數
try:
    import streamlit as st
    _SECRETS = dict(st.secrets) if hasattr(st, "secrets") else {}
except Exception:
    _SECRETS = {}

DATA_DIR = os.environ.get("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_PATH = os.path.join(DATA_DIR, "contacts.csv")

def save_contact(payload):
    exists = os.path.exists(CSV_PATH)
    fields = ["ts","name","email","phone","topic","when_date","when_ampm","msg"]
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        row = {k: ("" if payload.get(k) is None else str(payload.get(k))) for k in fields}
        row["ts"] = datetime.now().isoformat(timespec="seconds")
        w.writerow(row)

def _get(k, default=""):
    return _SECRETS.get(k) or os.environ.get(k, default)

def _smtp_config():
    return {
        "host":   _get("SMTP_HOST"),
        "port":   int(_get("SMTP_PORT", "587")),
        "user":   _get("SMTP_USER"),
        "pwd":    _get("SMTP_PASS"),
        "sender": _get("SMTP_SENDER") or _get("SMTP_USER"),
        "to":     _get("CONTACT_TO") or _get("SMTP_TO") or _get("SMTP_SENDER") or _get("SMTP_USER"),
        "tls":    str(_get("SMTP_TLS","1")).lower() not in ("0","false","no"),
    }

def _hdr(text):
    return str(Header(text, "utf-8"))

def send_email(payload):
    cfg = _smtp_config()
    # 設定不完整就略過寄信
    if not all([cfg["host"], cfg["user"], cfg["pwd"], cfg["sender"], cfg["to"]]):
        return False

    subject = u"[影響力平台] 新的聯絡需求：%s｜%s" % (payload.get("name",""), payload.get("topic",""))
    lines = [
        u"提交時間：%s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        u"稱呼：%s" % payload.get("name",""),
        u"Email：%s" % payload.get("email",""),
        u"電話：%s" % payload.get("phone",""),
        u"主題：%s" % payload.get("topic",""),
        u"期望：%s %s" % (payload.get("when_date",""), payload.get("when_ampm","")),
        u"訊息：%s" % ((payload.get("msg","") or "").strip()),
    ]
    body = "\n".join(lines)

    # 郵件內容（UTF-8）
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = Header(subject, "utf-8")

    # 顯示名稱用品牌；Envelope 與標頭的 email 一律萃取純 email
    sender_email = parseaddr(cfg["sender"])[1]
    msg["From"] = formataddr((_hdr("永傳家族辦公室"), sender_email))
    msg["Reply-To"] = payload.get("email", "")

    to_raw = str(cfg["to"]).replace(";", ",").split(",")
    to_list = [parseaddr(t.strip())[1] for t in to_raw if parseaddr(t.strip())[1]]
    msg["To"] = ", ".join(to_list)

    envelope_from = sender_email  # 必須是 ASCII 純 email

    if cfg["tls"]:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls(context=context)
            server.login(cfg["user"], cfg["pwd"])
            server.sendmail(envelope_from, to_list, msg.as_string())
    else:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context) as server:
            server.login(cfg["user"], cfg["pwd"])
            server.sendmail(envelope_from, to_list, msg.as_string())
    return True
