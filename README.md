# AI Pulse

AI Pulse helps a company understand how well its people use AI at work, team by team.

- **Employees** sign in, pick their organization, and take a short diagnostic. Questions adapt to their job role and seniority. Open-ended answers are scored by an LLM.
- **Each employee** gets a personal report: maturity level, risks, and next steps for their role.
- **Company admins** see a dashboard of AI maturity by department and the top risks across the company.
- Some users (consultants, group-company HR) belong to **more than one organization** and choose one after login.

---

## What I found and fixed

- **Organization isolation (`backend/app/routes/dashboard.py`):** Added a check ensuring an admin only accesses dashboards for their own organization (`403 Forbidden`).
- **Seniority question filtering (`backend/app/services/questions.py`):** Replaced alphabetical string comparison (`"lead" < "senior"`) with integer ranks so lead employees receive senior questions.
- **Department privacy threshold (`backend/app/routes/dashboard.py`):** Hidden scores (`None`) and levels (`"Not assessed"`) for departments with fewer than 5 completed respondents, and kept their risk flags out of `top_risks`.
- **Resilient AI scoring (`backend/app/services/scoring.py`):** Cleaned markdown fences and caught scoring exceptions so failed evaluations save with `score=None` instead of aborting the submission.
- **Secret key exposure (`backend/.env`):** Removed `backend/.env` from Git tracking, added `.env` to `.gitignore`, provided `backend/.env.example`, and rotated the local secret.

## Client requirements (Northwind HR)

- **Minimum 5 respondents:** If fewer than 5 employees in a department complete the diagnostic, department scores and levels are withheld, and their risks are excluded from company top risks.
- **Right to delete:** Added `DELETE /reports/me` and a "Delete my data" button on the Report page so employees can delete their diagnostic responses, which are excluded from dashboard calculations on the next data fetch or refresh.

## Feature: Sambhal (Privacy-aware answer recovery)

Sambhal redacts email addresses and phone numbers with regex before sending text to the LLM or saving it to SQLite. If scoring fails, the sanitized answer is safely stored with `score=None`, letting the employee retry scoring on demand via `POST /diagnostic/retry` from their report page. *Limitation:* Simple regex pattern matching only catches standard emails and phone numbers; it is not complete anonymization and will not catch names or custom confidential terms.

## Known limitations

- **No attempt history:** Each submission overwrites the member's previous answers rather than storing versioned historical attempts.
- **Suppression over pooling:** Ineligible departments have their scores suppressed instead of grouped into an artificial "Other teams" bucket.
- **No draft state:** Diagnostic questions must be completed in one sitting; partial answers are not saved.

## AI-assisted review

AI tools helped explore implementation options, but I reviewed suggestions against the code and requirements. One suggestion introduced a simulated timeout based on answer text, which highlighted why generated changes need careful review.

## Open questions for the client

Before rollout, we should confirm whether employee data deletion must also cover external AI-provider logs and backups, and whether departments with fewer than five respondents should stay hidden or be grouped under an "Other teams" row.

---

## Stack

- Backend: Python, FastAPI, SQLAlchemy (SQLite by default)
- Frontend: React (Vite)
- AI: any OpenAI-compatible chat completions endpoint, or mock mode with canned responses

## Run it locally

Backend:

```bash
cd backend
pip install -r requirements.txt
python -m app.seed          # creates demo data, password for all users: pulse123
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

Tests:

```bash
cd backend
python -m pytest
```

## Demo accounts (password `pulse123`)

| Email | Organization(s) | Role |
|---|---|---|
| asha@northwind.test | Northwind Logistics | Admin |
| meera@bluepeak.test | Bluepeak Retail | Admin |
| ravi@consult.test | Both | Employee at Northwind, admin at Bluepeak |
| priya@northwind.test | Northwind Logistics | Employee (Support) |
| dev@northwind.test | Northwind Logistics | Employee (Engineering, lead) |

## AI mode

`AI_MODE=mock` (default) returns canned model responses from `backend/data/mock_ai_responses.json`. Like a real model, they are not always well-formed.

`AI_MODE=live` calls `LLM_API_URL` with `LLM_API_KEY` and `LLM_MODEL`.
