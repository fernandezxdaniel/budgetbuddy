# BudgetBuddy (Flask + Segment Tree)

## Run locally in VS Code
1. Open this folder in VS Code, then open a terminal (Terminal > New Terminal).
2. pip install -r requirements.txt
3. python app.py  (then open http://localhost:5000)
4. Tests: python test_budget.py  and  python test_app.py

## Deploy free on Render
1. Put this folder in a GitHub repo and push it.
2. On render.com: New > Blueprint (or Web Service) and select the repo.
   - Build command: pip install -r requirements.txt
   - Start command: gunicorn app:app
   - Environment variable SECRET_KEY = any long random text (the blueprint generates it).
3. Open the URL Render gives you.

Note: Render's free tier has a temporary disk, so the SQLite file is erased when the service
redeploys or restarts. For permanent data, move to a free Render Postgres database.

Optional env vars: CURRENCY_SYMBOL (default $, for example the peso sign), DB_PATH.
