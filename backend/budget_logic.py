import calendar
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
 
from segment_tree import SumSegmentTree, MaxSegmentTree
from recommendations import generate
 
CATEGORIES = ("needs", "wants", "savings")
RATIOS = {"needs": 50, "wants": 30, "savings": 20}
MAX_AMOUNT = Decimal("1000000000")
MAX_ITEMS = 5000
 
 
class BudgetError(ValueError):
    """Raised for invalid user input; its message is safe to show to the user."""
 
 
def to_centavos(value, field="amount"):
    if value is None or isinstance(value, bool):
        raise BudgetError(f"{field} must be a number.")
    try:
        d = Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        raise BudgetError(f"{field} must be a number.")
    if not d.is_finite():
        raise BudgetError(f"{field} must be a number.")
    if d < 0 or d > MAX_AMOUNT:
        raise BudgetError(f"{field} must be between 0 and 1,000,000,000.")
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
 
 
def P(centavos):
    """centavos -> pesos for JSON."""
    return round(centavos / 100, 2)
 
 
def _int(v, field, lo, hi):
    try:
        if isinstance(v, bool):
            raise ValueError
        n = int(v)
        if isinstance(v, float) and v != n:
            raise ValueError
    except (TypeError, ValueError):
        raise BudgetError(f"{field} must be a whole number.")
    if not lo <= n <= hi:
        raise BudgetError(f"{field} must be between {lo} and {hi}.")
    return n
 
 
def _pct(a, b):
    if b == 0:
        return 0.0 if a == 0 else 100.0
    return round(a * 100 / b, 1)
 
 
def calculate(payload):
    if not isinstance(payload, dict):
        raise BudgetError("Invalid request.")
    now = date.today()
    year = _int(payload.get("year", now.year), "year", 2000, 2100)
    month = _int(payload.get("month", now.month), "month", 1, 12)
    dim = calendar.monthrange(year, month)[1]
    today = _int(payload.get("today", min(now.day, dim)), "today", 1, dim)
    income = to_centavos(payload.get("income", 0), "income")
 
    raw = payload.get("items", [])
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        raise BudgetError("items must be a list of at most 5000 entries.")
 
    by_cat = {c: SumSegmentTree(dim) for c in CATEGORIES}
    spend = SumSegmentTree(dim)      # needs + wants per day
    peak = MaxSegmentTree(dim)       # biggest spending day
    day_spend = [0] * dim
    largest = None
    names = {c: {} for c in CATEGORIES}   # per-name totals, for smarter advice
 
    for it in raw:
        if not isinstance(it, dict):
            raise BudgetError("Each item must be an object.")
        cat = str(it.get("category", "")).strip().lower()
        if cat not in CATEGORIES:
            raise BudgetError("category must be needs, wants or savings.")
        amt = to_centavos(it.get("amount"), "amount")
        if amt == 0:
            raise BudgetError("amount must be greater than zero.")
        idx = _int(it.get("day", today), "day", 1, dim) - 1
        name = str(it.get("name", "")).strip()[:60] or cat.title()
 
        by_cat[cat].add(idx, amt)
        ent = names[cat].setdefault(name.lower(), [name, 0])
        ent[1] += amt
        if cat != "savings":
            spend.add(idx, amt)
            day_spend[idx] += amt
            peak.update(idx, day_spend[idx])
            if largest is None or amt > largest[1]:
                largest = (name, amt)
 
    needs_b = (income * RATIOS["needs"] + 50) // 100
    wants_b = (income * RATIOS["wants"] + 50) // 100
    budget = {"needs": needs_b, "wants": wants_b, "savings": income - needs_b - wants_b}
    actual = {c: by_cat[c].query(0, dim - 1) for c in CATEGORIES}
    total_actual = sum(actual.values())
 
    spent_total = spend.query(0, dim - 1)
    spent_to_date = spend.query(0, today - 1)
    daily_avg = (2 * spent_to_date + today) // (2 * today)
    projected = (spent_to_date * dim + today // 2) // today
    last7 = spend.query(max(0, today - 7), today - 1)
    peak_val = peak.query(0, dim - 1)
    peak_day = day_spend.index(peak_val) + 1 if peak_val else None
    spend_budget = needs_b + wants_b
    spend_left = spend_budget - spent_total
    days_left = dim - today
    if spend_left <= 0:
        allowance = 0
    else:
        allowance = spend_left // days_left if days_left > 0 else spend_left
 
    weekly = []
    for start in range(1, dim + 1, 7):
        end = min(start + 6, dim)
        weekly.append({"week": len(weekly) + 1, "from": start, "to": end,
                       "spent": P(spend.query(start - 1, end - 1))})
 
    result = {
        "ok": True,
        "period": {"year": year, "month": month, "days_in_month": dim,
                   "today": today, "days_left": days_left},
        "income": P(income),
        "categories": {
            c: {"ratio": RATIOS[c], "budget": P(budget[c]), "actual": P(actual[c]),
                "left": P(budget[c] - actual[c]), "percent_used": _pct(actual[c], budget[c])}
            for c in CATEGORIES
        },
        "totals": {"budget": P(income), "actual": P(total_actual),
                   "left": P(income - total_actual), "balance": P(income - total_actual)},
        "metrics": {
            "spent_total": P(spent_total), "spent_to_date": P(spent_to_date),
            "daily_average": P(daily_avg), "projected_spending": P(projected),
            "last_7_days": P(last7), "peak_day": peak_day, "peak_amount": P(peak_val),
            "spending_budget": P(spend_budget), "spending_left": P(spend_left),
            "daily_allowance": P(allowance),
        },
        "weekly": weekly,
        "items_count": len(raw),
        "largest_expense": {"name": largest[0], "amount": P(largest[1])} if largest else None,
    }
    result["breakdown"] = {c: [{"name": v[0], "amount": P(v[1])}
                               for v in sorted(names[c].values(), key=lambda x: -x[1])] for c in CATEGORIES}
    result["recommendations"] = generate(result)
    return result