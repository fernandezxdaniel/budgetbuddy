import os
import re
import sqlite3
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import budget

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE, "budgetbuddy.db"))
SYMBOL = os.environ.get("CURRENCY_SYMBOL", "$")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),   # Render sets RENDER=true (HTTPS)
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    MAX_CONTENT_LENGTH=64 * 1024,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS incomes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
  month TEXT NOT NULL, cents INTEGER NOT NULL CHECK(cents > 0));
CREATE TABLE IF NOT EXISTS expenses(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
  month TEXT NOT NULL, category TEXT NOT NULL, cents INTEGER NOT NULL CHECK(cents > 0));
CREATE INDEX IF NOT EXISTS ix_inc ON incomes(user_id, month);
CREATE INDEX IF NOT EXISTS ix_exp ON expenses(user_id, month);
"""


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.close()


init_db()


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    if request.path.startswith("/api/") or request.path == "/dashboard":
        resp.headers["Cache-Control"] = "no-store"
    return resp


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "uid" not in session:
            if request.path.startswith("/api/"):
                return jsonify(error="Please log in again."), 401
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)
    return wrapper


# ---------- validation helpers ----------
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def to_cents(value):
    """Return a positive integer number of cents, or None if the amount is invalid."""
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not d.is_finite() or d <= 0 or d > Decimal("1000000000"):
        return None
    cents = int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return cents if cents > 0 else None


def get_month(data=None):
    month = (data or {}).get("month") or request.args.get("month") or date.today().strftime("%Y-%m")
    month = str(month)
    return month if MONTH_RE.match(month) else None


def password_ok(pw):
    return (8 <= len(pw) <= 128 and re.search(r"[A-Z]", pw) and re.search(r"\d", pw)
            and re.search(r"[@$!%*?&]", pw))


# ---------- pages ----------
@app.get("/")
def login_page():
    return redirect(url_for("dashboard")) if "uid" in session else render_template("login.html")


@app.get("/create-account")
def signup_page():
    return redirect(url_for("dashboard")) if "uid" in session else render_template("signup.html")


@app.get("/forgot-password")
def forgot_page():
    return render_template("forgot.html")


@app.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", name=session.get("name", ""),
                           groups=budget.GROUPS, symbol=SYMBOL)


# ---------- auth API ----------
@app.post("/api/signup")
def api_signup():
    d = body()
    name = str(d.get("name", "")).strip()[:60]
    email = str(d.get("email", "")).strip().lower()[:254]
    pw = str(d.get("password", ""))
    if not name:
        return jsonify(error="Enter your name."), 400
    if not EMAIL_RE.match(email):
        return jsonify(error="Enter a valid email address."), 400
    if not password_ok(pw):
        return jsonify(error="Password needs 8+ characters, an uppercase letter, a number and one of @$!%*?&"), 400
    try:
        cur = db().execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                           (name, email, generate_password_hash(pw)))
        db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="An account with this email already exists."), 409
    session.clear()
    session["uid"], session["name"] = cur.lastrowid, name
    return jsonify(redirect=url_for("dashboard"))


@app.post("/api/login")
def api_login():
    d = body()
    email = str(d.get("email", "")).strip().lower()
    pw = str(d.get("password", ""))
    row = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], pw):
        return jsonify(error="Incorrect email or password."), 401
    session.clear()
    session["uid"], session["name"] = row["id"], row["name"]
    session.permanent = bool(d.get("remember"))
    return jsonify(redirect=url_for("dashboard"))


@app.post("/api/forgot")
def api_forgot():
    return jsonify(error="Password reset by email isn't set up in this version yet."), 501


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify(redirect=url_for("login_page"))


# ---------- budget API ----------
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def history(uid, month):
    """Income vs spending (needs + wants) for the 6 months ending at `month`."""
    y, m = int(month[:4]), int(month[5:])
    months = []
    for _ in range(6):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    marks = ",".join("?" * 6)
    smarks = ",".join("?" * len(budget.SAVINGS_KEYS))
    inc = {r[0]: r[1] for r in db().execute(
        f"SELECT month, SUM(cents) FROM incomes WHERE user_id=? AND month IN ({marks}) GROUP BY month",
        (uid, *months))}
    exp = {r[0]: r[1] for r in db().execute(
        f"SELECT month, SUM(cents) FROM expenses WHERE user_id=? AND month IN ({marks}) "
        f"AND category NOT IN ({smarks}) GROUP BY month", (uid, *months, *budget.SAVINGS_KEYS))}
    return [{"month": mo, "label": MONTH_NAMES[int(mo[5:]) - 1],
             "income": inc.get(mo, 0) / 100, "expense": exp.get(mo, 0) / 100} for mo in months]


def summary(uid, month):
    conn = db()
    income = conn.execute("SELECT COALESCE(SUM(cents),0) FROM incomes WHERE user_id=? AND month=?",
                          (uid, month)).fetchone()[0]
    by_key = {r[0]: r[1] for r in conn.execute(
        "SELECT category, SUM(cents) FROM expenses WHERE user_id=? AND month=? GROUP BY category",
        (uid, month))}
    all_in = conn.execute("SELECT COALESCE(SUM(cents),0) FROM incomes WHERE user_id=?", (uid,)).fetchone()[0]
    all_out = conn.execute("SELECT COALESCE(SUM(cents),0) FROM expenses WHERE user_id=?", (uid,)).fetchone()[0]
    marks = ",".join("?" * len(budget.SAVINGS_KEYS))
    all_saved = conn.execute(f"SELECT COALESCE(SUM(cents),0) FROM expenses WHERE user_id=? AND category IN ({marks})",
                             (uid, *budget.SAVINGS_KEYS)).fetchone()[0]
    out = budget.analyze(income, by_key, SYMBOL)
    out.update(month=month, total_balance=(all_in - all_out) / 100,
               total_income=all_in / 100, total_saved=all_saved / 100,
               history=history(uid, month))
    return out


@app.get("/api/summary")
@login_required
def api_summary():
    month = get_month()
    if not month:
        return jsonify(error="Invalid month."), 400
    return jsonify(summary(session["uid"], month))


@app.post("/api/income")
@login_required
def api_income():
    d = body()
    month, cents = get_month(d), to_cents(d.get("amount"))
    if not month:
        return jsonify(error="Invalid month."), 400
    if cents is None:
        return jsonify(error="Enter a valid income amount greater than zero."), 400
    db().execute("INSERT INTO incomes(user_id,month,cents) VALUES(?,?,?)", (session["uid"], month, cents))
    db().commit()
    return jsonify(summary(session["uid"], month))


@app.post("/api/expenses")
@login_required
def api_expenses():
    d = body()
    month, items = get_month(d), d.get("items")
    if not month:
        return jsonify(error="Invalid month."), 400
    if not isinstance(items, dict):
        return jsonify(error="Enter at least one amount."), 400
    rows = []
    for key, value in items.items():
        if key not in budget.ALL_KEYS:
            return jsonify(error="Unknown category."), 400
        if value is None or str(value).strip() == "":
            continue
        cents = to_cents(value)
        if cents is None:
            return jsonify(error=f"Enter a valid amount for {budget.LABELS[key]}."), 400
        rows.append((session["uid"], month, key, cents))
    if not rows:
        return jsonify(error="Enter at least one amount."), 400
    db().executemany("INSERT INTO expenses(user_id,month,category,cents) VALUES(?,?,?,?)", rows)
    db().commit()
    return jsonify(summary(session["uid"], month))


@app.post("/api/reset")
@login_required
def api_reset():
    month = get_month(body())
    if not month:
        return jsonify(error="Invalid month."), 400
    for table in ("incomes", "expenses"):
        db().execute(f"DELETE FROM {table} WHERE user_id=? AND month=?", (session["uid"], month))
    db().commit()
    return jsonify(summary(session["uid"], month))


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
