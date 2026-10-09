import random
import budget as b

# Segment tree vs brute force on many random arrays, ranges and updates
random.seed(7)
for _ in range(300):
    n = random.randint(1, 12)
    vals = [random.choice([0, 0, random.randint(1, 500)]) for _ in range(n)]
    t = b.SegmentTree(vals)
    for _ in range(20):
        if random.random() < .4:
            i, v = random.randrange(n), random.choice([0, random.randint(1, 500)])
            vals[i] = v; t.update(i, v)
        l = random.randrange(n); r = random.randint(l, n - 1)
        total, (mxv, mxi), (mnv, mni) = t.query(l, r)
        seg = vals[l:r + 1]
        assert total == sum(seg)
        assert mxv == max(seg) and vals[mxi] == mxv and l <= mxi <= r
        pos = [x for x in seg if x > 0]
        if pos:
            assert mnv == min(pos) and vals[mni] == mnv and l <= mni <= r
        else:
            assert mnv == b.INF
for bad in [(-1, 2), (3, 2), (0, 99)]:
    try: b.SegmentTree([1, 2, 3]).query(*bad); raise SystemExit("should fail")
    except IndexError: pass

# Budget scenarios (cents)
a = b.analyze(0, {});                                        assert a["status"] == "empty"
a = b.analyze(0, {"food": 100});                             assert a["status"] == "no_income"
a = b.analyze(100000, {"food": 30000, "rent": 20000, "gaming": 20000, "gala": 10000, "savings": 20000})
assert a["status"] == "balanced" and "ant" in a["message"] and a["left"] == 0, a
assert a["highest"]["label"] == "Food" and a["lowest"]["label"] == "Gala (going out)"
a = b.analyze(100000, {"rent": 60000, "online_shopping": 50000})
assert a["status"] == "overspending" and a["left"] == -100 and a["suggestions"], a
a = b.analyze(100000, {"rent": 60000, "gaming": 10000})   # needs 60%, savings rate 30%
assert a["status"] == "attention" and any("Needs are 60.0%" in s for s in a["suggestions"]), a
a = b.analyze(100000, {"food": 10000, "gaming": 50000})   # wants 50%
assert a["status"] == "attention" and any("Wants are 50.0%" in s for s in a["suggestions"]), a
a = b.analyze(100000, {"food": 10000, "emergency_fund": 95000})  # savings pushes over income
assert a["status"] == "overspending" and any("savings entries" in s for s in a["suggestions"]), a
print("budget tests passed")
