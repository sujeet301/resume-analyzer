# AI Resume Analyzer — Complete AI Backend

FastAPI + MongoDB backend with local semantic embeddings and Google Gemini generative AI.

## AI features
1. **Semantic job matching:** sentence-transformers `all-MiniLM-L6-v2` encodes resume and job text. Ranking combines 65% semantic similarity and 35% explicit required-skill coverage.
2. **AI resume review:** Gemini returns evidence-based strengths, weaknesses, improvement suggestions, unclear information, rewritten bullet suggestions, target-role fit, and skills to learn.
3. **AI mock interviews:** Gemini creates role/resume-specific interview questions and evaluates candidate answers with scores, feedback, answer structure, sample improved answers, and follow-up questions.
4. **Resume chat:** ask questions about a saved resume, optionally in the context of a job.

## Important limitations
- Gemini API key is required for generative endpoints. Semantic embeddings run locally but require model download and enough RAM/disk.
- The first semantic request downloads the embedding model; expect a delay.
- Job records are sample/manual entries. This backend does not scrape LinkedIn/Indeed or fetch live job vacancies.
- The match score is an approximate relevance ranking, not probability of selection.
- PDF text extraction does not perform OCR on scanned/image-only PDFs.
- This is a development backend. It does not yet include user authentication, per-user authorization, production rate limiting, or encrypted resume storage. Do not expose it publicly with real resumes until these controls are added.
- AI output can be wrong. Review all suggestions and never add unverified claims to a resume.

## Requirements
- Python 3.11+
- MongoDB local or Atlas
- Gemini API key for LLM endpoints

## Windows PowerShell setup
```powershell
py -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=resume_analyzer
GEMINI_API_KEY=YOUR_REAL_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
```
Get a Gemini API key from Google AI Studio. Keep it private and never put it in frontend code or commit `.env` to Git.

## Start server
```powershell
uvicorn app.main:app --reload
```
Swagger: http://127.0.0.1:8000/docs

## Test workflow
1. `GET /api/health`
2. `GET /api/ai/status` — confirm `gemini_configured: true`
3. `POST /api/jobs/seed` — add five demo jobs (run once).
4. `POST /api/resumes/upload` — upload a PDF or DOCX; copy `resume_id` from response.
5. `GET /api/recommendations/{resume_id}` — semantic ranked jobs; first run downloads the embedding model.
6. `POST /api/analysis` with JSON:
```json
{"resume_id":"YOUR_RESUME_ID","job_id":"A_JOB_ID"}
```
7. `POST /api/ai/resume-analysis`:
```json
{"resume_id":"YOUR_RESUME_ID","job_id":"A_JOB_ID"}
```
8. `POST /api/ai/interviews/start`:
```json
{"resume_id":"YOUR_RESUME_ID","job_id":"A_JOB_ID","count":8}
```
9. `POST /api/ai/interviews/answer`:
```json
{"interview_id":"INTERVIEW_ID","question_index":0,"answer":"Your answer here, with specific examples."}
```
10. `GET /api/ai/interviews/{interview_id}` — retrieve session and feedback.
11. `POST /api/ai/resume-chat`:
```json
{"resume_id":"YOUR_RESUME_ID","job_id":"A_JOB_ID","question":"What are the three biggest improvements I should make?"}
```

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health and AI status |
| GET | `/api/ai/status` | Provider configuration |
| POST | `/api/resumes/upload` | Upload PDF/DOCX |
| GET | `/api/resumes` | List resumes |
| GET | `/api/resumes/{id}` | Resume metadata |
| DELETE | `/api/resumes/{id}` | Delete resume and related records |
| POST | `/api/jobs` | Add job |
| GET | `/api/jobs` | List stored jobs |
| GET | `/api/jobs/search-live/{resume_id}` | Search Adzuna/Arbeitnow and rank live listings |
| POST | `/api/jobs/seed` | Add demo jobs |
| POST | `/api/analysis` | Semantic resume-job match |
| GET | `/api/recommendations/{resume_id}` | Ranked job recommendations |
| POST | `/api/ai/resume-analysis` | Gemini resume review |
| POST | `/api/ai/interviews/start` | Generate personalized questions |
| POST | `/api/ai/interviews/answer` | Evaluate one answer |
| GET | `/api/ai/interviews/{interview_id}` | Retrieve interview session |
| POST | `/api/ai/resume-chat` | Ask questions about a resume |

## Notes on the scoring formula
`match_score = 65% * semantic_similarity + 35% * skill_coverage`
The score is for sorting and comparison only. It is not a hiring probability.


## LinkedIn integration
Call `GET /api/jobs/linkedin-search/{resume_id}?location=Delhi%20NCR&remote=true` to generate personalized LinkedIn Jobs search links from detected resume skills and inferred job roles. These links open LinkedIn's own live search results; the backend does not retrieve or scrape LinkedIn listings. LinkedIn's Job Posting API is restricted to approved partners, not a public job-search API.

## Live job search providers

`GET /api/jobs/search-live/{resume_id}` fetches live listings from configured providers and ranks each result against the uploaded resume using the existing semantic matching model.

Example for India:
```http
GET /api/jobs/search-live/RESUME_ID?location=Delhi%20NCR&country=in&providers=adzuna&limit=20
```

To include remote/international listings from Arbeitnow:
```http
GET /api/jobs/search-live/RESUME_ID?query=python%20developer&providers=adzuna,arbeitnow&remote=true
```

### Adzuna setup
1. Register at https://developer.adzuna.com/ and create an API application.
2. Copy `app_id` and `app_key` into backend `.env` as `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
3. Restart the backend.
4. The default country is `in` (India). Set `country` to another supported two-letter Adzuna market code when needed.
5. Display the label **Jobs by Adzuna** on every Adzuna listing and link it to the relevant local Adzuna site. Review Adzuna's API terms before use beyond evaluation/academic testing. The free key is intended for evaluation; academic/organisational and commercial use has additional conditions.

### Arbeitnow setup
No API key is required for its public job-board API. Listings are predominantly Germany/Europe-focused. Keep the source label and link back to https://www.arbeitnow.com/ on displayed results. Review its current terms before deployment.

### Matching and limitations
- Job results are fetched from providers at request time and are not cached in MongoDB.
- Adzuna may return a description snippet rather than a full job description; semantic matching is based on the content supplied by the provider.
- Arbeitnow results are filtered locally by query/location and may be sparse for India.
- Provider errors are returned in `provider_errors`; one failed provider does not prevent results from another provider.
- Always show provider attribution and send users to the original job URL to apply.
- Do not scrape LinkedIn. LinkedIn remains an outbound search-link integration.
