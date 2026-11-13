# ResumeAI Backend

FastAPI backend for the AI Resume Analyzer & Job Recommendation System.

## Setup
```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Configure MongoDB and Gemini in `.env`. Set `JWT_SECRET` to a long random value before deployment. The API exposes registration, login and current-user endpoints under `/api/auth`.

## Authentication and data isolation
- `POST /api/auth/register` creates an account.
- `POST /api/auth/login` returns a signed bearer token.
- `GET /api/auth/me` returns the authenticated user.
- All resume, analysis, recommendation, chat and interview routes require the bearer token.
- Resume and interview records are scoped to the authenticated account. Demo jobs are shared; user-created jobs are private.
- Passwords are stored as salted scrypt hashes, not plaintext.

## AI and job search
- Sentence Transformers (`all-MiniLM-L6-v2`) powers semantic matching.
- Gemini powers resume review, resume chat and mock interviews when `GEMINI_API_KEY` is configured.
- Live job search uses Arbeitnow only. Adzuna integration and credentials are removed.
- LinkedIn integration generates outbound search URLs; it does not scrape or fetch LinkedIn job listings.

## Deployment
Set `MONGODB_URI`, `MONGODB_DATABASE`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `JWT_SECRET` and `CORS_ORIGINS` on the backend host. `CORS_ORIGINS` must be a JSON array, for example:
`["https://your-frontend.vercel.app"]`.

Render start command:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
