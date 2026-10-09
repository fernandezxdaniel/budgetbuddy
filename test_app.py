import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
from app import app

c = app.test_client()
J = lambda r: r.get_json()

# pages
for path in ["/", "/create-account", "/forgot-password"]:
    r = c.get(path); assert r.status_code == 200, path
    assert b"logo.png" in r.data and b"BudgetBuddy" in r.data
assert b"Log in" in c.get("/").data and b"Welcome back" not in c.get("/").data
assert c.get("/dashboard").status_code == 302                        # protected
assert c.get("/api/summary").status_code == 401
assert c.post("/api/income", json={"amount": 5}).status_code == 401
assert c.get("/static/dashboard.js").status_code == 200 and c.get("/static/logo.png").status_code == 200

# signup validation
bad = [{"name": "", "email": "a@b.co", "password": "Abcdef1!"}, {"name": "A", "email": "nope", "password": "Abcdef1!"},
       {"name": "A", "email": "a@b.co", "password": "abcdef1!"}, {"name": "A", "email": "a@b.co", "password": "Abc1!"}]
for d in bad: assert c.post("/api/signup", json=d).status_code == 400, d
r = c.post("/api/signup", json={"name": "Ana", "email": "Ana@Mail.com", "password": "Secret12!"})
assert r.status_code == 200 and J(r)["redirect"] == "/dashboard"
assert b"Hi, Ana" in c.get("/dashboard").data
for needle in [b"Gala (going out)", b"School fees", b"Online shopping", b"Emergency fund", b"flowChart", b"pieChart"]:
    assert needle in c.get("/dashboard").data, needle
c.post("/api/logout")
assert c.get("/dashboard").status_code == 302
assert c.post("/api/signup", json={"name": "X", "email": "ana@mail.com", "password": "Secret12!"}).status_code == 409
assert c.post("/api/login", json={"email": "ana@mail.com", "password": "wrong"}).status_code == 401
assert c.post("/api/login", json={"email": "ana@mail.com", "password": "Secret12!"}).status_code == 200

# budget flow, month 1: 1000 income, balanced
r = J(c.post("/api/income", json={"month": "2026-10", "amount": "1000"}))
assert r["total_balance"] == 1000 and r["income"] == 1000
r = J(c.post("/api/expenses", json={"month": "2026-10", "items": {
    "food": "300", "rent": "200", "gaming": "200", "gala": "100", "savings": "200", "water": ""}}))
assert r["spent"] == 800 and r["saved"] == 200 and r["left"] == 0 and r["total_balance"] == 0, r
assert r["status"] == "balanced" and "ant" in r["message"]
assert r["highest"] == {"label": "Food", "amount": 300.0} and r["lowest"]["label"] == "Gala (going out)"
assert r["pct"] == {"needs": 50.0, "wants": 30.0, "savings": 20.0}

# month 2: income again, then overspend; balance carries over across months
J(c.post("/api/income", json={"month": "2026-11", "amount": 500.50}))
r = J(c.post("/api/expenses", json={"month": "2026-11", "items": {"rent": "400", "online_shopping": "250.75"}}))
assert r["status"] == "overspending" and r["left"] == -150.25 and r["suggestions"], r
assert r["total_balance"] == -150.25 and r["total_income"] == 1500.5 and r["total_saved"] == 200
r = J(c.get("/api/summary?month=2026-10")); assert r["status"] == "balanced"      # months are independent

# bad input
for amt in ["", "-5", "0", "abc", "NaN", "Infinity", "1e12", None, [1], True, "0.001"]:
    assert c.post("/api/income", json={"month": "2026-10", "amount": amt}).status_code == 400, amt
assert c.post("/api/income", json={"month": "2026-13", "amount": 5}).status_code == 400
assert c.get("/api/summary?month=bad").status_code == 400
assert c.post("/api/expenses", json={"month": "2026-10", "items": {}}).status_code == 400
assert c.post("/api/expenses", json={"month": "2026-10", "items": {"hacker": "5"}}).status_code == 400
assert c.post("/api/expenses", json={"month": "2026-10", "items": {"food": "-1"}}).status_code == 400
assert c.post("/api/expenses", data="notjson").status_code == 400
assert J(c.get("/api/summary?month=2026-10"))["spent"] == 800                       # nothing leaked in

# reset one month only
r = J(c.post("/api/reset", json={"month": "2026-11"}))
assert r["income"] == 0 and r["status"] == "empty" and r["total_balance"] == 0
assert c.post("/api/forgot", json={"email": "a@b.co"}).status_code == 501

# a second user can't see the first user's data
c2 = app.test_client()
c2.post("/api/signup", json={"name": "Ben", "email": "ben@mail.com", "password": "Secret12!"})
assert J(c2.get("/api/summary?month=2026-10"))["income"] == 0
h = J(c.get("/api/summary?month=2026-02"))["history"]
assert [x["month"] for x in h] == ["2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02"], h
h = J(c.get("/api/summary?month=2026-10"))["history"]
assert len(h) == 6 and h[-1] == {"month": "2026-10", "label": "Oct", "income": 1000.0, "expense": 800.0}, h
assert h[-2]["income"] == 0 and h[-2]["expense"] == 0
assert b"flowChart" in c.get("/dashboard").data and b"logo-chip" in c.get("/dashboard").data
print("app tests passed")
