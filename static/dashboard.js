(() => {
  const SYM = document.body.dataset.symbol || "$";
  const $ = (id) => document.getElementById(id);
  const money = (n) => {
    const v = Number(n) || 0;
    return (v < 0 ? "-" : "") + SYM + Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
  const now = new Date();
  const monthInput = $("month");
  monthInput.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  async function api(url, data) {
    const opts = data === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
    const res = await fetch(url, opts);
    if (res.status === 401) { window.location.href = "/"; throw new Error("Please log in again."); }
    let body = {};
    try { body = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(body.error || "Something went wrong. Please try again.");
    return body;
  }
  const flash = (node, text, ok) => { node.textContent = text; node.classList.toggle("ok", !!ok); };

  const ICONS = { food: "🍚", water: "💧", rent: "🏠", clothes: "👕", school_fees: "🎓", gaming: "🎮", gala: "🎉", online_shopping: "🛍️", emergency_fund: "🛟", savings: "🐷" };
  const COLORS = ["#1239b8", "#2f7df0", "#38bdf8", "#7dd3fc", "#93c5fd", "#1d4ed8", "#0ea5e9", "#60a5fa", "#6366f1", "#a5b4fc"];

  let flow = null, pie = null;
  if (window.Chart) {
    Chart.defaults.font.family = '"Plus Jakarta Sans", system-ui, sans-serif';
    flow = new Chart($("flowChart"), {
      type: "bar",
      data: { labels: [], datasets: [
        { label: "Income", data: [], backgroundColor: "#9cc8ff", borderRadius: 8 },
        { label: "Expenses", data: [], backgroundColor: "#1d4ed8", borderRadius: 8 }] },
      options: { maintainAspectRatio: false,
        plugins: { legend: { position: "top", align: "end", labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${money(c.parsed.y)}` } } },
        scales: { y: { beginAtZero: true, grid: { color: "#e8f0fb" }, ticks: { callback: (v) => SYM + v } }, x: { grid: { display: false } } } },
    });
    pie = new Chart($("pieChart"), {
      type: "doughnut",
      data: { labels: [], datasets: [{ data: [], backgroundColor: COLORS, borderWidth: 3, borderColor: "#fff" }] },
      options: { maintainAspectRatio: false, cutout: "72%", plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.label}: ${money(c.parsed)}` } } } },
    });
  } else {
    $("pieNote").textContent = "Charts couldn't load. Check your internet connection.";
  }

  function render(s) {
    $("totalBalance").textContent = money(s.total_balance);
    $("totalBalance").classList.toggle("neg", s.total_balance < 0);
    $("mIncome").textContent = money(s.income);
    $("mSpent").textContent = money(s.spent);
    $("mSaved").textContent = money(s.saved);
    $("mLeft").textContent = money(s.left);
    $("mLeft").classList.toggle("neg", s.left < 0);

    $("statusCard").className = "card st-" + s.status;
    $("statusBadge").textContent = { balanced: "Balanced", overspending: "Overspending", attention: "Needs attention" }[s.status] || "Analysis";
    $("statusTitle").textContent = s.headline;
    $("statusMsg").textContent = s.message;
    $("tips").replaceChildren(...s.suggestions.map((t) => el("li", "", t)));

    const limits = { needs: ["max", 50], wants: ["max", 30], savings: ["min", 20] };
    for (const key of Object.keys(limits)) {
      const p = s.pct[key], [kind, target] = limits[key];
      const good = s.income > 0 && (kind === "max" ? p <= target : p >= target);
      const row = $("r-" + key);
      row.classList.toggle("good", good);
      row.classList.toggle("bad", s.income > 0 && !good);
      row.querySelector("i").style.width = Math.max(0, Math.min(100, p)) + "%";
      $("p-" + key).textContent = (s.income > 0 ? p : 0) + "%";
    }
    $("highest").textContent = s.highest ? `${s.highest.label} · ${money(s.highest.amount)}` : "-";
    $("lowest").textContent = s.lowest ? `${s.lowest.label} · ${money(s.lowest.amount)}` : "-";

    // Money flow (last 6 months)
    if (flow) {
      flow.data.labels = s.history.map((h) => h.label);
      flow.data.datasets[0].data = s.history.map((h) => h.income);
      flow.data.datasets[1].data = s.history.map((h) => h.expense);
      flow.update();
    }
    // Donut + legend
    const used = s.by_category.filter((c) => c.amount > 0);
    $("dUsed").textContent = money(s.spent + s.saved);
    $("dIncome").textContent = money(s.income);
    $("dLeft").textContent = money(s.left);
    $("dLeft").classList.toggle("neg", s.left < 0);
    $("legend").replaceChildren(...used.map((c) => {
      const li = el("li"); const dot = el("i"); dot.style.background = COLORS[s.by_category.indexOf(c)];
      li.append(dot, el("em", "", c.label), el("span", "", money(c.amount))); return li;
    }));
    $("pieNote").style.display = used.length ? "none" : "block";
    if (pie) {
      pie.data.labels = used.map((c) => c.label);
      pie.data.datasets[0].data = used.map((c) => c.amount);
      pie.data.datasets[0].backgroundColor = used.map((c) => COLORS[s.by_category.indexOf(c)]);
      pie.update();
    }
    // Biggest expense tiles
    const top = s.by_category.filter((c) => c.group !== "Savings" && c.amount > 0).sort((a, b) => b.amount - a.amount).slice(0, 6);
    $("tiles").replaceChildren(...(top.length ? top.map((c) => {
      const t = el("div", "tile");
      t.append(el("span", "ico", ICONS[c.key] || "💰"), el("small", "", c.label), el("b", "", money(c.amount))); return t;
    }) : [el("p", "tiles-empty", "No expenses yet for this month.")]));
  }

  async function load() {
    if (!monthInput.value) return;
    try { render(await api("/api/summary?month=" + encodeURIComponent(monthInput.value))); }
    catch (e) { flash($("incomeMsg"), e.message, false); }
  }
  monthInput.addEventListener("change", load);

  async function submit(form, msgEl, url, payload, okText, clear) {
    const btn = form.querySelector(".btn");
    btn.disabled = true;
    try { render(await api(url, payload)); clear(); flash(msgEl, okText, true); }
    catch (e) { flash(msgEl, e.message, false); }
    finally { btn.disabled = false; }
  }

  $("incomeForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const amount = $("incomeAmount").value.trim();
    if (!monthInput.value) return flash($("incomeMsg"), "Pick a month first.", false);
    if (!amount) return flash($("incomeMsg"), "Enter your income amount.", false);
    submit(e.target, $("incomeMsg"), "/api/income", { month: monthInput.value, amount },
      "Income added to your total balance.", () => { $("incomeAmount").value = ""; });
  });

  $("expenseForm").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!monthInput.value) return flash($("expenseMsg"), "Pick a month first.", false);
    const inputs = [...document.querySelectorAll("[data-key]")];
    const items = {};
    inputs.forEach((i) => { if (i.value.trim() !== "") items[i.dataset.key] = i.value.trim(); });
    if (!Object.keys(items).length) return flash($("expenseMsg"), "Enter at least one amount.", false);
    submit(e.target, $("expenseMsg"), "/api/expenses", { month: monthInput.value, items },
      "Expenses saved and your balance is updated.", () => inputs.forEach((i) => { i.value = ""; }));
  });

  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => { t.classList.toggle("active", t === tab); t.setAttribute("aria-selected", t === tab); });
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== tab.dataset.tab));
  }));
  document.querySelectorAll(".side nav a").forEach((a) => a.addEventListener("click", () => {
    document.querySelectorAll(".side nav a").forEach((x) => x.classList.toggle("active", x === a));
  }));

  $("resetMonth").addEventListener("click", async () => {
    if (!monthInput.value || !confirm("Delete all income and expense entries for this month?")) return;
    try { render(await api("/api/reset", { month: monthInput.value })); flash($("expenseMsg"), "This month was cleared.", true); }
    catch (e) { flash($("expenseMsg"), e.message, false); }
  });
  $("logout").addEventListener("click", async () => {
    try { const r = await api("/api/logout", {}); window.location.href = r.redirect; } catch (_) { window.location.href = "/"; }
  });

  load();
})();
