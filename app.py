import os
import re
import sqlite3
from datetime import datetime, timezone
from io import BytesIO

import qrcode
from qrcode.image.svg import SvgPathImage
from flask import Flask, abort, redirect, render_template_string
from flask import request, send_file, url_for

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "hustle.db")

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                service TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

def parse_sale(message):
    amount_match = re.search(
        r'(?:R\s*)?(\d+(?:\.\d{1,2})?)', message, re.I
    )
    if not amount_match:
        return None

    amount = float(amount_match.group(1))
    if not 1 <= amount <= 1000000:
        return None

    text = message.lower()
    services = [
        (("braid", "braids", "ama braid", "izinwele",
          "ukuluka", "hair"), "Braids"),
        (("clean", "cleaning", "ukuhlanza"), "Cleaning"),
        (("food", "plate", "meal", "food sale"), "Food"),
        (("repair", "fix", "ukulungisa"), "Repairs"),
        (("nail", "nails"), "Nails"),
    ]
    found = [name for words, name in services
             if any(word in text for word in words)]

    if len(found) != 1:
        return {"amount": amount, "service": None}
    return {"amount": amount, "service": found[0]}

PAGE = """
<!doctype html>
<html lang="en">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HUSTLE | Business Passport</title>
<style>
body{font-family:system-ui;max-width:720px;margin:25px auto;padding:0 16px;
background:#111;color:#fff}
h1{color:#e8bd50} .card{background:#202020;border:1px solid #444;
border-radius:14px;padding:16px;margin:14px 0}
input,button{box-sizing:border-box;width:100%;padding:13px;margin:6px 0;
border-radius:8px;border:1px solid #666;font-size:16px}
button{background:#e8bd50;color:#111;font-weight:bold}
small,.muted{color:#bbb}a{color:#e8bd50}
table{width:100%;text-align:left}td,th{padding:8px 3px;border-bottom:1px solid #444}
</style>
<h1>HUSTLE</h1>
<p>Turn your hustle into opportunity.</p>
{% if public %}
<div class="card">
<h2>Business Passport</h2>
<p><b>Business:</b> Demo Hustler</p>
<p><b>Recorded sales:</b> R{{ '%.2f'|format(total) }}</p>
<p><b>Sales recorded:</b> {{ sales|length }}</p>
<p><b>Top service:</b> {{ top_service }}</p>
<p class="muted">These are seller-recorded transactions.
They are not independently verified payments or proof of creditworthiness.</p>
</div>
{% else %}
<div class="card">
<h2>1. Record a cash sale</h2>
<p>Example: <b>R250 ama braid</b></p>
<form method="post" action="/sale">
<input name="message" required maxlength="200"
placeholder="e.g. R250 ama braid">
<button>Record sale</button>
</form>
{% if error %}<p>{{ error }}</p>{% endif %}
</div>
<div class="card">
<h2>2. Sales ledger</h2>
{% if sales %}
<table><tr><th>Amount</th><th>Service</th><th>Time</th></tr>
{% for s in sales %}
<tr><td>R{{ '%.2f'|format(s.amount) }}</td>
<td>{{ s.service }}</td><td>{{ s.created_at }}</td></tr>
{% endfor %}</table>
{% else %}<p>No sales recorded yet.</p>{% endif %}
<h3>Total recorded: R{{ '%.2f'|format(total) }}</h3>
</div>
<div class="card">
<h2>3. Public business passport</h2>
<p>Scan this QR code to open the public profile.</p>
<img src="/qr" width="220" height="220" alt="Business passport QR">
<p><a href="/p/demo">Open public passport</a></p>
</div>
{% endif %}
</html>
"""

@app.get("/")
def home():
    with connect() as db:
        sales = db.execute(
            "SELECT * FROM sales ORDER BY id DESC"
        ).fetchall()
    total = sum(s["amount"] for s in sales)
    return render_template_string(
        PAGE, sales=sales, total=total, public=False,
        error=request.args.get("error"), top_service="Not available"
    )

@app.post("/sale")
def add_sale():
    message = request.form.get("message", "").strip()
    parsed = parse_sale(message)
    if not parsed:
        return redirect("/?error=Please+include+a+valid+amount")
    if not parsed["service"]:
        return redirect(
            "/?error=Service+unclear.+Try+braids,+cleaning,+food,+repairs+or+nails"
        )

    with connect() as db:
        db.execute(
            "INSERT INTO sales(amount,service,created_at) VALUES(?,?,?)",
            (parsed["amount"], parsed["service"],
             datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
        )
    return redirect("/")

@app.get("/p/demo")
def passport():
    with connect() as db:
        sales = db.execute(
            "SELECT * FROM sales ORDER BY id DESC"
        ).fetchall()
    total = sum(s["amount"] for s in sales)
    counts = {}
    for sale in sales:
        counts[sale["service"]] = counts.get(sale["service"], 0) + 1
    top = max(counts, key=counts.get) if counts else "Not available"
    return render_template_string(
        PAGE, sales=sales, total=total, public=True,
        top_service=top, error=None
    )

@app.get("/qr")
def qr():
    target = url_for("passport", _external=True)
    image = qrcode.make(target, image_factory=SvgPathImage)
    output = BytesIO()
    image.save(output)
    output.seek(0)
    return send_file(output, mimetype="image/svg+xml")

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
