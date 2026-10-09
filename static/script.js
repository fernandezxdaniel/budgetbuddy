(() => {
  const $ = (id) => document.getElementById(id);

  document.querySelectorAll(".toggle-pw").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = $(btn.dataset.toggle);
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "Hide" : "Show";
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  const msg = $("form-msg");
  const say = (text, ok = false) => { msg.textContent = text; msg.classList.toggle("success", ok); };
  const emailOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());

  const pw = $("password");
  const confirmPw = $("confirm-password");
  const matchMsg = $("match-msg");
  const rules = {
    length: (v) => v.length >= 8,
    uppercase: (v) => /[A-Z]/.test(v),
    number: (v) => /\d/.test(v),
    special: (v) => /[@$!%*?&]/.test(v),
  };
  function checkPassword() {
    let score = 0;
    for (const [id, test] of Object.entries(rules)) {
      const pass = test(pw.value);
      $(id).classList.toggle("valid", pass);
      if (pass) score++;
    }
    $("strength").dataset.level = pw.value ? score : 0;
    return score === 4;
  }
  function checkMatch() {
    const bad = confirmPw.value !== "" && confirmPw.value !== pw.value;
    matchMsg.style.display = bad ? "block" : "none";
    confirmPw.classList.toggle("invalid", bad);
    return confirmPw.value !== "" && !bad;
  }
  if (confirmPw) {
    pw.addEventListener("input", () => { checkPassword(); checkMatch(); });
    confirmPw.addEventListener("input", checkMatch);
  }

  function handle(form, url, validate, payload, okText) {
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      form.querySelectorAll("input").forEach((i) => i.classList.remove("invalid"));
      const problem = validate();
      if (problem) { say(problem.text); problem.field.classList.add("invalid"); problem.field.focus(); return; }
      say("");
      const btn = form.querySelector(".login-btn");
      btn.classList.add("loading");
      try {
        const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload()) });
        let data = {};
        try { data = await res.json(); } catch (_) {}
        if (!res.ok) { say(data.error || "Something went wrong. Please try again."); return; }
        if (data.redirect) { say(okText, true); window.location.href = data.redirect; return; }
        say(data.message || okText, true);
      } catch (_) {
        say("Can't reach the server. Check your connection and try again.");
      } finally {
        btn.classList.remove("loading");
      }
    });
  }

  const remember = () => { const c = document.querySelector('input[name="remember"]'); return !!(c && c.checked); };

  handle($("login-form"), "/api/login", () => {
    if (!emailOk($("email").value)) return { field: $("email"), text: "Enter a valid email address." };
    if (!pw.value) return { field: pw, text: "Enter your password." };
  }, () => ({ email: $("email").value, password: pw.value, remember: remember() }), "Logged in. Opening your dashboard…");

  handle($("signup-form"), "/api/signup", () => {
    if (!$("username").value.trim()) return { field: $("username"), text: "Enter your name." };
    if (!emailOk($("email").value)) return { field: $("email"), text: "Enter a valid email address." };
    if (!checkPassword()) return { field: pw, text: "Your password doesn't meet all the requirements yet." };
    if (!checkMatch()) return { field: confirmPw, text: "Passwords don't match." };
  }, () => ({ name: $("username").value, email: $("email").value, password: pw.value }), "Account created. Opening your dashboard…");

  handle($("forgot-form"), "/api/forgot", () => {
    if (!emailOk($("email").value)) return { field: $("email"), text: "Enter a valid email address." };
  }, () => ({ email: $("email").value }), "Request sent.");
})();
