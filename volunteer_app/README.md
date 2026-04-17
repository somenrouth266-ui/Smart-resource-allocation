# VolunteerIQ — Smart Resource Allocation

> Data-driven volunteer coordination for social impact  
> Built for **Hack2Skills × Google** Hackathon

---

## What It Does

VolunteerIQ uses a **4-factor smart matching algorithm** and **Claude AI suggestions** to connect coordinators with the best-fit volunteers for every task — automatically.

| Role | Can Do |
|---|---|
| **Coordinator** | Create tasks, view smart matches, assign volunteers, track impact |
| **Volunteer** | Browse tasks, apply, accept/decline assignments, track impact hours |

---

## Smart Matching Algorithm

Every volunteer is scored 0–100 against a task:

| Factor | Weight | Logic |
|---|---|---|
| Skill overlap | 50 pts | % of required skills the volunteer has |
| Availability | 20 pts | Keyword match: task time slot vs. volunteer schedule |
| Workload balance | 20 pts | Fewer active tasks = higher score (fair distribution) |
| Reliability | 10 pts | Historical completion vs. decline ratio |

---

## Local Setup (5 minutes)

```bash
# 1. Clone / unzip
cd volunteer_app

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY (optional — app works without it)

# 5. Seed demo data
python seed.py

# 6. Run
python run.py
# Open http://localhost:5000
```

### Demo Login Credentials

| Role | Email | Password |
|---|---|---|
| Coordinator | coordinator@demo.com | demo1234 |
| Volunteer | priya@demo.com | demo1234 |
| Volunteer | sneha@demo.com | demo1234 |

All 8 demo volunteers use password: `demo1234`

---

## Deploy to Render (Free Tier)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml`
5. Add environment variable: `ANTHROPIC_API_KEY` → your key
6. Click **Deploy**

Done. Live in ~3 minutes.

---

## Project Structure

```
volunteer_app/
├── app.py              ← Flask factory, db, login manager
├── models.py           ← User, Task, Assignment models
├── matching.py         ← 4-factor smart matching engine
├── seed.py             ← Demo data seeder
├── run.py              ← Entry point
├── requirements.txt
├── Procfile            ← For Render/Heroku
├── render.yaml         ← One-click Render deploy
├── .env.example
├── routes/
│   ├── auth.py         ← Register, login, logout
│   ├── coordinator.py  ← All coordinator routes
│   ├── volunteer.py    ← All volunteer routes
│   ├── ai_suggest.py   ← Claude API integration
│   └── main.py         ← Landing page
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── auth/
│   ├── coordinator/
│   └── volunteer/
└── static/
    └── css/main.css    ← Full design system
```

---

## AI Suggest Feature

On any task detail page, coordinators can click **✨ Get AI Suggestion**.

Claude reviews the top 5 matched candidates and returns a plain-English recommendation: who to pick, why, and a tip for the coordinator.

Works without an API key (returns algorithmic summary). Set `ANTHROPIC_API_KEY` in `.env` for full AI responses.

---

## Tech Stack

- **Backend**: Flask 3, SQLAlchemy, Flask-Login
- **Database**: SQLite (local) — swap `DATABASE_URL` for PostgreSQL on Render
- **AI**: Anthropic Claude API (`claude-sonnet-4-20250514`)
- **Frontend**: Vanilla HTML/CSS/JS — no frameworks, loads instantly
- **Charts**: Chart.js 4 (CDN)
- **Fonts**: Space Grotesk + DM Sans + JetBrains Mono (Google Fonts)
- **Deploy**: Render (free tier)
