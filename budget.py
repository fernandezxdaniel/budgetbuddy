"""BudgetBuddy core logic: a Segment Tree ADT plus the 50/30/20 budget analysis.

Segment Tree (special tree) ADT operations
    build(values)   O(n)      construct the tree from the expense amounts
    update(i, v)    O(log n)  change one category's amount
    query(l, r)    O(log n)  total, highest and lowest over any category range
All money is handled as integer cents to avoid floating point errors.
"""
import math

INF = math.inf

NEEDS = (("food", "Food"), ("water", "Water"), ("rent", "Rent"),
         ("clothes", "Clothes"), ("school_fees", "School fees"))
WANTS = (("gaming", "Gaming expenses"), ("gala", "Gala (going out)"),
         ("online_shopping", "Online shopping"))
SAVINGS = (("emergency_fund", "Emergency fund"), ("savings", "Savings"))

EXPENSES = NEEDS + WANTS                       # the categories stored in the tree
ALL_KEYS = {k for k, _ in EXPENSES + SAVINGS}
SAVINGS_KEYS = [k for k, _ in SAVINGS]
LABELS = dict(NEEDS + WANTS + SAVINGS)
NEEDS_RANGE = (0, len(NEEDS) - 1)
WANTS_RANGE = (len(NEEDS), len(EXPENSES) - 1)
TARGETS = {"needs": 50, "wants": 30, "savings": 20}   # the standard 50/30/20 ratio
GROUPS = [
    {"id": "needs", "title": "Basic needs", "entries": NEEDS},
    {"id": "wants", "title": "Wants", "entries": WANTS},
    {"id": "savings", "title": "Savings", "entries": SAVINGS},
]
TIPS = {
    "food": "Plan weekly meals and cook in batches to cut food costs.",
    "water": "Fix leaks and cut waste to keep the water bill low.",
    "rent": "Rent is a fixed cost: consider sharing the space or negotiating.",
    "clothes": "Buy only what you need and wait for sales.",
    "school_fees": "Look for scholarships, instalment plans or second-hand books.",
    "gaming": "Set a monthly gaming cap and skip in-game purchases.",
    "gala": "Limit going out to once a week or pick free activities.",
    "online_shopping": "Wait 48 hours before buying and unsubscribe from shop promotions.",
}


class SegmentTree:
    """Each node stores (total, (max_value, max_index), (min_value, min_index)).
    Zero amounts are ignored for the minimum, so 'lowest' means the lowest
    category you actually spent on."""

    def __init__(self, values):
        self.n = len(values)
        if self.n == 0:
            raise ValueError("SegmentTree needs at least one value")
        self.t = [None] * (4 * self.n)
        self._build(1, 0, self.n - 1, values)

    @staticmethod
    def _leaf(i, v):
        return (v, (v, i), (v if v > 0 else INF, i))

    @staticmethod
    def _merge(a, b):
        mx = a[1] if a[1][0] >= b[1][0] else b[1]   # ties keep the left-most index
        mn = a[2] if a[2][0] <= b[2][0] else b[2]
        return (a[0] + b[0], mx, mn)

    def _build(self, node, lo, hi, values):
        if lo == hi:
            self.t[node] = self._leaf(lo, values[lo])
            return
        mid = (lo + hi) // 2
        self._build(2 * node, lo, mid, values)
        self._build(2 * node + 1, mid + 1, hi, values)
        self.t[node] = self._merge(self.t[2 * node], self.t[2 * node + 1])

    def update(self, i, value):
        if not 0 <= i < self.n:
            raise IndexError("index out of range")
        self._update(1, 0, self.n - 1, i, value)

    def _update(self, node, lo, hi, i, value):
        if lo == hi:
            self.t[node] = self._leaf(lo, value)
            return
        mid = (lo + hi) // 2
        if i <= mid:
            self._update(2 * node, lo, mid, i, value)
        else:
            self._update(2 * node + 1, mid + 1, hi, i, value)
        self.t[node] = self._merge(self.t[2 * node], self.t[2 * node + 1])

    def query(self, l, r):
        if not 0 <= l <= r < self.n:
            raise IndexError("bad query range")
        return self._query(1, 0, self.n - 1, l, r)

    def _query(self, node, lo, hi, l, r):
        if l <= lo and hi <= r:
            return self.t[node]
        mid = (lo + hi) // 2
        if r <= mid:
            return self._query(2 * node, lo, mid, l, r)
        if l > mid:
            return self._query(2 * node + 1, mid + 1, hi, l, r)
        return self._merge(self._query(2 * node, lo, mid, l, r),
                           self._query(2 * node + 1, mid + 1, hi, l, r))


def analyze(income, by_key, symbol="$"):
    """income and by_key values are integer cents for ONE month."""
    m = lambda c: f"{symbol}{c / 100:,.2f}"
    tree = SegmentTree([int(by_key.get(k, 0)) for k, _ in EXPENSES])
    needs = tree.query(*NEEDS_RANGE)[0]
    wants = tree.query(*WANTS_RANGE)[0]
    spent, hi, lo = tree.query(0, len(EXPENSES) - 1)
    saved = sum(int(by_key.get(k, 0)) for k in SAVINGS_KEYS)
    left = income - spent - saved

    def top_in(rng):
        _, (v, i), _ = tree.query(*rng)
        return (EXPENSES[i][0], EXPENSES[i][1], v) if v > 0 else None

    pct = lambda c: round(c * 100 / income, 1) if income > 0 else 0.0
    # savings rate = everything not spent on needs or wants
    keep = income - needs - wants
    ok_needs = needs * 100 <= TARGETS["needs"] * income
    ok_wants = wants * 100 <= TARGETS["wants"] * income
    ok_save = keep * 100 >= TARGETS["savings"] * income

    tips = []
    if income == 0 and spent + saved == 0:
        status, headline = "empty", "No data yet"
        message = "Add your income, then your expenses for this month to see your analysis."
    elif income == 0:
        status, headline = "no_income", "Income is missing"
        message = "You have entries this month but no income. Add your income to check your ratio."
    elif left < 0:
        status, headline = "overspending", "You are overspending"
        message = f"You used {m(-left)} more than your income this month."
        w = top_in(WANTS_RANGE)
        if w:
            tips.append(f"Cut wants first. Your biggest want is {w[1]} ({m(w[2])}). {TIPS[w[0]]}")
        n = top_in(NEEDS_RANGE)
        if n and not ok_needs:
            tips.append(f"Needs take {pct(needs)}% of your income (target {TARGETS['needs']}%). "
                        f"Biggest need: {n[1]} ({m(n[2])}). {TIPS[n[0]]}")
        if spent <= income:
            tips.append("Your spending fits your income, but your savings entries push you over. "
                        "Lower this month's savings amount.")
    elif ok_needs and ok_wants and ok_save:
        status, headline = "balanced", "Perfectly balanced"
        message = ("You are like an ant \U0001F41C: you plan ahead, spend with purpose "
                   "and store up for the future. Keep it up!")
        tips.append("Keep growing your emergency fund toward 3 to 6 months of basic needs.")
    else:
        status, headline = "attention", "Close, but off the 50/30/20 ratio"
        message = "You are within your income, but some areas are off the ideal ratio."
        if not ok_needs:
            n = top_in(NEEDS_RANGE)
            tips.append(f"Needs are {pct(needs)}% of income (target {TARGETS['needs']}% or less), "
                        f"about {m(needs - income * TARGETS['needs'] / 100)} too high. "
                        f"Biggest need: {n[1]} ({m(n[2])}). {TIPS[n[0]]}")
        if not ok_wants:
            w = top_in(WANTS_RANGE)
            tips.append(f"Wants are {pct(wants)}% of income (target {TARGETS['wants']}% or less), "
                        f"about {m(wants - income * TARGETS['wants'] / 100)} too high. "
                        f"Biggest want: {w[1]} ({m(w[2])}). {TIPS[w[0]]}")
        if not ok_save:
            tips.append(f"Set aside about {m(income * TARGETS['savings'] / 100 - keep)} more to reach "
                        f"the {TARGETS['savings']}% savings target. Pay yourself first when income arrives.")
    if status in ("overspending", "attention"):
        tips.append("Follow the 50/30/20 rule: 50% needs, 30% wants, 20% savings.")
        tips.append("Review your spending weekly so small leaks don't grow.")

    group_of = {k: g["title"] for g in GROUPS for k, _ in g["entries"]}
    return {
        "status": status, "headline": headline, "message": message, "suggestions": tips,
        "income": income / 100, "needs": needs / 100, "wants": wants / 100,
        "spent": spent / 100, "saved": saved / 100, "left": left / 100,
        "pct": {"needs": pct(needs), "wants": pct(wants), "savings": pct(keep)},
        "targets": TARGETS,
        "highest": {"label": EXPENSES[hi[1]][1], "amount": hi[0] / 100} if hi[0] > 0 else None,
        "lowest": {"label": EXPENSES[lo[1]][1], "amount": lo[0] / 100} if lo[0] != INF else None,
        "by_category": [{"key": k, "label": LABELS[k], "group": group_of[k],
                         "amount": int(by_key.get(k, 0)) / 100}
                        for k in [x for x, _ in EXPENSES + SAVINGS]],
    }
