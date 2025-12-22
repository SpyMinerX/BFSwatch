#!/usr/bin/env python3
import os
import re
import sqlite3
import hashlib
import smtplib
from email.message import EmailMessage
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, redirect, url_for, render_template_string, flash
from apscheduler.schedulers.background import BackgroundScheduler

URL = "https://www.bms-fw.bayern.de/Navigation/Public/lastminute.aspx"
TIMEOUT = 25

DB_PATH = os.environ.get("BFSWATCH_DB", "bfswatch.sqlite3")

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER)
SMTP_STARTTLS = os.environ.get("SMTP_STARTTLS", "1") == "1"

RUN_HOUR = int(os.environ.get("RUN_HOUR", "8"))
RUN_MINUTE = int(os.environ.get("RUN_MINUTE", "5"))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-me")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            mode TEXT NOT NULL,
            pattern TEXT NOT NULL,
            only_with_free INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            fingerprint TEXT NOT NULL,
            notified_at TEXT NOT NULL,
            UNIQUE(subscription_id, fingerprint)
        )""")

def fetch_html():
    r = requests.get(URL, timeout=TIMEOUT, headers={"User-Agent": "bfswatch"})
    r.raise_for_status()
    return r.text

def parse_courses(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 4:
            continue
        free = None
        for c in reversed(cells):
            if c.isdigit():
                free = int(c)
                break
        rows.append({
            "title": cells[2],
            "row": " | ".join(cells),
            "free": free
        })
    return rows

def send_mail(to, subject, body):
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        if SMTP_STARTTLS:
            s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()

def run_check():
    html = fetch_html()
    courses = parse_courses(html)
    with db() as conn:
        subs = conn.execute("SELECT * FROM subscriptions").fetchall()
    for sub in subs:
        rx = re.compile(sub["pattern"], re.IGNORECASE)
        for c in courses:
            if not rx.search(c["row"]):
                continue
            if sub["only_with_free"] and (c["free"] is None or c["free"] <= 0):
                continue
            fp = fingerprint(c["row"])
            with db() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM notifications WHERE subscription_id=? AND fingerprint=?",
                    (sub["id"], fp)
                ).fetchone()
                if exists:
                    continue
                send_mail(
                    sub["email"],
                    "BFSwatch: Neuer freier Lehrgangsplatz",
                    c["row"]
                )
                conn.execute(
                    "INSERT INTO notifications VALUES (NULL, ?, ?, ?)",
                    (sub["id"], fp, datetime.utcnow().isoformat())
                )

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = request.form["email"]
        pattern = request.form["pattern"]
        with db() as conn:
            conn.execute(
                "INSERT INTO subscriptions VALUES (NULL, ?, 'regex', ?, 1, ?)",
                (email, pattern, datetime.utcnow().isoformat())
            )
        return redirect("/")
    return render_template_string("""
    <h1>BFSwatch</h1>
    <form method="post">
      Email: <input name="email"><br>
      Regex: <input name="pattern"><br>
      <button>Add</button>
    </form>
    """)

init_db()
scheduler = BackgroundScheduler()
scheduler.add_job(run_check, "cron", hour=RUN_HOUR, minute=RUN_MINUTE)
scheduler.start()
