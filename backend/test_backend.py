"""Run: python test_backend.py   (checks the segment tree against brute force + a sample budget)"""
import random
from segment_tree import SegmentTree, SumSegmentTree, MaxSegmentTree
from budget_logic import calculate, BudgetError
 
random.seed(1)
for _ in range(300):
    n = random.randint(1, 31)
    vals = [random.randint(0, 5000) for _ in range(n)]
    s, m = SumSegmentTree(n), MaxSegmentTree(n)
    for i, v in enumerate(vals):
        s.update(i, v); m.update(i, v)
    for _ in range(30):
        i = random.randrange(n); vals[i] = random.randint(0, 5000)
        s.update(i, vals[i]); m.update(i, vals[i])
        a = random.randrange(n); b = random.randrange(a, n)
        assert s.query(a, b) == sum(vals[a:b + 1])
        assert m.query(a, b) == max(vals[a:b + 1])
assert SegmentTree.from_list([1, 2, 3, 4]).query(1, 3) == 9
 
r = calculate({"year": 2026, "month": 10, "today": 9, "income": 10000, "items": [
    {"category": "needs", "name": "Rent", "amount": 5500, "day": 1},
    {"category": "needs", "name": "Food", "amount": "1,200.50", "day": 5},
    {"category": "wants", "name": "Movies", "amount": 3100, "day": 8},
    {"category": "savings", "name": "Piggy", "amount": 500, "day": 2}]})
c = r["categories"]
assert c["needs"]["budget"] == 5000 and c["needs"]["actual"] == 6700.5 and c["needs"]["left"] == -1700.5
assert c["wants"]["left"] == -100 and c["savings"]["left"] == 1500
assert r["totals"]["balance"] == 10000 - 6700.5 - 3100 - 500
assert r["metrics"]["peak_day"] == 1 and r["weekly"][0]["spent"] == 6700.5
assert r["recommendations"][0]["level"] in ("danger", "warning")
for bad in ({"income": -5}, {"items": [{"category": "x", "amount": 1}]},
            {"items": [{"category": "needs", "amount": "abc"}]},
            {"month": 2, "year": 2026, "items": [{"category": "needs", "amount": 5, "day": 30}]}):
    try: calculate(bad); raise SystemExit("should have failed: %r" % bad)
    except BudgetError: pass
r2 = calculate({"year": 2026, "month": 10, "today": 9, "income": 10000, "items": [
    {"category": "needs", "name": "Rent", "amount": 4000, "day": 1},
    {"category": "needs", "name": "rent", "amount": 500, "day": 2},
    {"category": "wants", "name": "Online Shopping", "amount": 1500, "day": 3},
    {"category": "savings", "name": "Education Fund", "amount": 500, "day": 4}]})
assert r2["breakdown"]["needs"][0] == {"name": "Rent", "amount": 4500.0}
titles = [x["title"] for x in r2["recommendations"]]
assert any("Rent takes 45%" in x for x in titles) and any("Online shopping is 15%" in x for x in titles)
assert any("emergency fund" in x for x in titles), titles
print("ALL TESTS PASSED")
for x in r["recommendations"]: print("-", x["level"], "|", x["title"])
