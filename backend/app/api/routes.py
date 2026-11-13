from datetime import datetime, timezone
from urllib.parse import urlencode
from bson import ObjectId
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.core.config import settings
from app.db.mongo import get_database
from app.models.schemas import (
    JobCreate, AnalyzeRequest, ResumeAIRequest,
    InterviewStartRequest, InterviewAnswerRequest
)
from app.services.resume_parser import extract_text
from app.services.analyzer import extract_skills, extract_sections, improvement_suggestions
from app.services.matching import match_resume_to_job
from app.services.ai_client import gemini_configured
from app.services.job_providers import search_arbeitnow
from app.core.auth import current_user_id, require_user
from app.services.ai_features import (
    analyze_resume_with_ai, create_interview_questions,
    evaluate_interview_answer, generate_resume_chat_reply
)

router = APIRouter(dependencies=[Depends(require_user)])

def oid(value: str, label: str):
    if not ObjectId.is_valid(value):
        raise HTTPException(400, f"Invalid {label} ID")
    return ObjectId(value)

def serialize(doc):
    if not doc:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc



def linkedin_jobs_url(keywords: str, location: str = "", remote: bool = False) -> str:
    params = {"keywords": keywords}
    if location.strip():
        params["location"] = location.strip()
    if remote:
        params["f_WT"] = "2"
    return "https://www.linkedin.com/jobs/search/?" + urlencode(params)

async def get_resume_or_404(resume_id: str, include_text: bool = True):
    projection = None if include_text else {"text": 0}
    doc = await get_database().resumes.find_one({"_id": oid(resume_id, "resume"), "user_id": current_user_id()}, projection)
    if not doc:
        raise HTTPException(404, "Resume not found")
    return doc

async def get_job_or_404(job_id: str):
    doc = await get_database().jobs.find_one({"_id": oid(job_id, "job"), "$or": [{"user_id": current_user_id()}, {"is_global": True}]})
    if not doc:
        raise HTTPException(404, "Job not found")
    return doc

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-resume-analyzer-api",
        "gemini_configured": gemini_configured(),
        "semantic_matching": True
    }

@router.get("/ai/status")
async def ai_status():
    return {
        "semantic_embeddings": "enabled (sentence-transformers; model loads on first semantic request)",
        "llm_provider": "Google Gemini",
        "gemini_configured": gemini_configured(),
        "gemini_model": settings.gemini_model,
        "note": "Gemini endpoints return 503 until GEMINI_API_KEY is configured."
    }

@router.post("/resumes/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "Filename is required")
    raw = await file.read()
    if len(raw) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_size_mb} MB limit")
    try:
        text = extract_text(file.filename, raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(400, f"Could not parse resume: {exc}")
    skills = extract_skills(text)
    sections = extract_sections(text)
    doc = {
        "user_id": current_user_id(),
        "filename": file.filename,
        "content_type": file.content_type,
        "text": text,
        "skills": skills,
        "sections": sections,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_database().resumes.insert_one(doc)
    return {
        "resume_id": str(result.inserted_id),
        "filename": file.filename,
        "skills": skills,
        "sections": sections,
        "word_count": len(text.split()),
        "message": "Resume uploaded and parsed successfully"
    }

@router.get("/resumes")
async def list_resumes():
    docs = await get_database().resumes.find({"user_id": current_user_id()}, {"text": 0}).sort("created_at", -1).to_list(100)
    return [serialize(d) for d in docs]

@router.get("/resumes/{resume_id}")
async def get_resume(resume_id: str):
    return serialize(await get_resume_or_404(resume_id, include_text=False))

@router.delete("/resumes/{resume_id}")
async def delete_resume(resume_id: str):
    db = get_database()
    rid = oid(resume_id, "resume")
    result = await db.resumes.delete_one({"_id": rid, "user_id": current_user_id()})
    if not result.deleted_count:
        raise HTTPException(404, "Resume not found")
    await db.analyses.delete_many({"resume_id": resume_id, "user_id": current_user_id()})
    await db.ai_analyses.delete_many({"resume_id": resume_id, "user_id": current_user_id()})
    await db.interviews.delete_many({"resume_id": resume_id, "user_id": current_user_id()})
    return {"message": "Resume and related analysis/interview records deleted"}

@router.post("/jobs")
async def create_job(payload: JobCreate):
    doc = payload.model_dump()
    doc["user_id"] = current_user_id()
    doc["created_at"] = datetime.now(timezone.utc)
    result = await get_database().jobs.insert_one(doc)
    return {"job_id": str(result.inserted_id), **payload.model_dump()}

@router.get("/jobs")
async def list_jobs():
    docs = await get_database().jobs.find({"$or": [{"user_id": current_user_id()}, {"is_global": True}]}).sort("created_at", -1).to_list(200)
    return [serialize(d) for d in docs]

@router.post("/jobs/seed")
async def seed_jobs():
    db = get_database()
    samples = [
        {"title": "Junior Python Developer", "company": "Demo Tech", "location": "Remote", "experience_level": "Entry level", "description": "Build APIs and backend services using Python, FastAPI, SQL, testing and REST APIs.", "required_skills": ["python", "fastapi", "sql", "git", "rest api"]},
        {"title": "Frontend Developer", "company": "Demo Studio", "location": "Delhi NCR", "experience_level": "Entry level", "description": "Build responsive interfaces using React, JavaScript, HTML, CSS and modern frontend tooling.", "required_skills": ["react", "javascript", "html", "css", "git"]},
        {"title": "MERN Stack Developer", "company": "Demo Systems", "location": "Hybrid", "experience_level": "Junior", "description": "Develop full-stack apps with MongoDB, Express, React, Node.js and REST APIs.", "required_skills": ["mongodb", "express", "react", "node.js", "javascript", "rest api"]},
        {"title": "Junior Data Analyst", "company": "Demo Analytics", "location": "Remote", "experience_level": "Entry level", "description": "Analyze datasets and create reports with Python, SQL, Pandas, Excel and communication.", "required_skills": ["python", "sql", "pandas", "excel", "communication"]},
        {"title": "AI/ML Intern", "company": "Demo AI Lab", "location": "Delhi NCR", "experience_level": "Internship", "description": "Explore NLP and machine learning workflows using Python, scikit-learn, NumPy and machine learning.", "required_skills": ["python", "machine learning", "nlp", "scikit-learn", "numpy"]}
    ]
    inserted = 0
    for job in samples:
        if not await db.jobs.find_one({"title": job["title"], "company": job["company"], "is_global": True}):
            await db.jobs.insert_one({**job, "is_global": True, "created_at": datetime.now(timezone.utc)})
            inserted += 1
    return {"message": f"Seeded {inserted} demo jobs", "inserted": inserted}

@router.post("/analysis")
async def analyze_resume(payload: AnalyzeRequest):
    db = get_database()
    resume = await get_resume_or_404(payload.resume_id)
    job = await get_job_or_404(payload.job_id)
    result = match_resume_to_job(resume, job)
    result.update({
        "resume_id": payload.resume_id,
        "user_id": current_user_id(),
        "job_id": payload.job_id,
        "job_title": job["title"],
        "company": job["company"],
        "suggestions": improvement_suggestions(resume["text"], resume.get("skills", [])),
        "created_at": datetime.now(timezone.utc)
    })
    saved = await db.analyses.insert_one(result)
    result["analysis_id"] = str(saved.inserted_id)
    return result

@router.get("/recommendations/{resume_id}")
async def recommendations(resume_id: str):
    resume = await get_resume_or_404(resume_id)
    jobs = await get_database().jobs.find({"$or": [{"user_id": current_user_id()}, {"is_global": True}]}).to_list(200)
    results = []
    for job in jobs:
        match = match_resume_to_job(resume, job)
        results.append({
            "job": serialize(job),
            "match_score": match["match_score"],
            "semantic_similarity": match["semantic_similarity"],
            "skill_coverage": match["skill_coverage"],
            "matched_skills": match["matched_skills"],
            "missing_skills": match["missing_skills"],
            "score_method": match["score_method"],
            "score_disclaimer": match["score_disclaimer"],
            "linkedin_search_url": linkedin_jobs_url(
                job.get("title", ""), job.get("location", "")
            )
        })
    return sorted(results, key=lambda x: x["match_score"], reverse=True)





@router.get("/jobs/search-live/{resume_id}")
async def search_live_jobs(
    resume_id: str,
    location: str = "",
    country: str = "in",
    query: str = "",
    providers: str = "arbeitnow",
    remote: bool = False,
    page: int = 1,
    limit: int = 20,
):
    """Fetch current third-party listings and rank them against the saved resume."""
    if country not in {"in", "gb", "us", "au", "ca", "de", "fr", "nl", "be", "at", "ch", "it", "es", "pl", "nz", "za", "br", "mx", "sg"}:
        raise HTTPException(400, "Unsupported country code for this integration")
    if page < 1 or not 1 <= limit <= 50:
        raise HTTPException(400, "page must be >= 1 and limit must be between 1 and 50")
    resume = await get_resume_or_404(resume_id)
    skills = resume.get("skills", [])
    search_query = query.strip() or " ".join(skills[:4]) or "software developer"
    selected = {p.strip().lower() for p in providers.split(",") if p.strip()}
    unknown = selected - {"arbeitnow"}
    if unknown:
        raise HTTPException(400, f"Unknown providers: {', '.join(sorted(unknown))}")

    jobs, provider_errors = [], []
    if "arbeitnow" in selected:
        try:
            jobs.extend(await search_arbeitnow(search_query, location, remote, page))
        except Exception as exc:
            provider_errors.append({"provider": "Arbeitnow", "error": str(exc)})

    ranked = []
    seen = set()
    for job in jobs:
        dedupe_key = (job.get("source", ""), job.get("external_id", ""))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        matchable = {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "description": job.get("description", ""),
            "required_skills": job.get("required_skills", []),
            "experience_level": "",
        }
        try:
            match = match_resume_to_job(resume, matchable)
            job.update({
                "match_score": match["match_score"],
                "semantic_similarity": match["semantic_similarity"],
                "skill_coverage": match["skill_coverage"],
                "matched_skills": match["matched_skills"],
                "missing_skills": match["missing_skills"],
                "score_method": match["score_method"],
                "score_disclaimer": match["score_disclaimer"],
            })
        except Exception as exc:
            job.update({"match_score": None, "matching_error": str(exc)})
        ranked.append(job)

    ranked.sort(key=lambda item: item.get("match_score") if item.get("match_score") is not None else -1, reverse=True)
    return {
        "resume_id": resume_id,
        "query": search_query,
        "location": location or None,
        "country": country,
        "remote_only": remote,
        "total": len(ranked),
        "results": ranked,
        "provider_errors": provider_errors,
        "attribution": [
            {"provider": "Arbeitnow", "label": "Jobs from Arbeitnow", "url": "https://www.arbeitnow.com/"},
        ],
        "notice": "Listings and apply links are supplied by the job sources. Verify availability and details on the source site. Match scores are relevance estimates, not hiring probabilities."
    }

@router.get("/jobs/linkedin-search/{resume_id}")
async def linkedin_job_search_links(resume_id: str, location: str = "", remote: bool = False):
    """Build personalized LinkedIn Jobs search links; does not scrape listings."""
    resume = await get_resume_or_404(resume_id)
    skills = resume.get("skills", [])
    searches = []
    if skills:
        top_skills = skills[:5]
        combined = " ".join(top_skills[:3])
        searches.append({"label": "Jobs matching your detected skills", "keywords": combined, "url": linkedin_jobs_url(combined, location, remote)})
        for skill in top_skills[:3]:
            searches.append({"label": f"Roles requiring {skill}", "keywords": skill, "url": linkedin_jobs_url(skill, location, remote)})
    skill_set = {s.lower() for s in skills}
    role_queries = []
    if {"react", "javascript"} & skill_set: role_queries.append("Frontend Developer")
    if {"node.js", "express", "mongodb"} & skill_set: role_queries.append("MERN Stack Developer")
    if {"python", "fastapi", "django"} & skill_set: role_queries.append("Python Developer")
    if {"machine learning", "nlp", "scikit-learn", "pytorch", "tensorflow"} & skill_set: role_queries.append("Machine Learning Engineer")
    for role in role_queries:
        searches.append({"label": f"Suggested role: {role}", "keywords": role, "url": linkedin_jobs_url(role, location, remote)})
    unique, seen = [], set()
    for item in searches:
        if item["url"] not in seen:
            unique.append(item); seen.add(item["url"])
    return {"resume_id": resume_id, "detected_skills": skills, "location": location or None, "remote_only": remote, "searches": unique, "source": "LinkedIn Jobs search page", "integration_type": "outbound_search_link", "notice": "Links open LinkedIn's live search results in the user's browser. This API does not retrieve, scrape, cache, or verify individual LinkedIn job listings."}

@router.post("/ai/resume-analysis")
async def ai_resume_analysis(payload: ResumeAIRequest):
    if not gemini_configured():
        raise HTTPException(503, "Gemini is not configured. Add GEMINI_API_KEY to .env and restart the API.")
    resume = await get_resume_or_404(payload.resume_id)
    job = await get_job_or_404(payload.job_id) if payload.job_id else None
    try:
        result = analyze_resume_with_ai(resume["text"], resume.get("skills", []), job)
    except Exception as exc:
        raise HTTPException(502, f"AI analysis failed: {exc}")
    result["resume_id"] = payload.resume_id
    result["user_id"] = current_user_id()
    result["job_id"] = payload.job_id
    result["created_at"] = datetime.now(timezone.utc)
    saved = await get_database().ai_analyses.insert_one(result)
    result["analysis_id"] = str(saved.inserted_id)
    return result

@router.post("/ai/interviews/start")
async def start_interview(payload: InterviewStartRequest):
    if not gemini_configured():
        raise HTTPException(503, "Gemini is not configured. Add GEMINI_API_KEY to .env and restart the API.")
    resume = await get_resume_or_404(payload.resume_id)
    job = await get_job_or_404(payload.job_id)
    try:
        questions = create_interview_questions(
            resume["text"], resume.get("skills", []), job, payload.count
        )
    except Exception as exc:
        raise HTTPException(502, f"Could not generate interview questions: {exc}")
    if not questions:
        raise HTTPException(502, "AI returned no interview questions")
    doc = {
        "resume_id": payload.resume_id,
        "user_id": current_user_id(),
        "job_id": payload.job_id,
        "job_title": job["title"],
        "questions": questions,
        "answers": [],
        "created_at": datetime.now(timezone.utc)
    }
    saved = await get_database().interviews.insert_one(doc)
    return {
        "interview_id": str(saved.inserted_id),
        "job_title": job["title"],
        "questions": questions
    }

@router.post("/ai/interviews/answer")
async def submit_interview_answer(payload: InterviewAnswerRequest):
    if not gemini_configured():
        raise HTTPException(503, "Gemini is not configured. Add GEMINI_API_KEY to .env and restart the API.")
    db = get_database()
    iid = oid(payload.interview_id, "interview")
    interview = await db.interviews.find_one({"_id": iid, "user_id": current_user_id()})
    if not interview:
        raise HTTPException(404, "Interview session not found")
    questions = interview.get("questions", [])
    if payload.question_index >= len(questions):
        raise HTTPException(400, "Question index is out of range")
    question = questions[payload.question_index].get("question", "")
    try:
        feedback = evaluate_interview_answer(question, payload.answer, interview.get("job_title", ""))
    except Exception as exc:
        raise HTTPException(502, f"Could not evaluate answer: {exc}")
    answer_record = {
        "question_index": payload.question_index,
        "question": question,
        "answer": payload.answer,
        "feedback": feedback,
        "created_at": datetime.now(timezone.utc)
    }
    await db.interviews.update_one({"_id": iid, "user_id": current_user_id()}, {"$push": {"answers": answer_record}})
    return answer_record

@router.get("/ai/interviews/{interview_id}")
async def get_interview(interview_id: str):
    doc = await get_database().interviews.find_one({"_id": oid(interview_id, "interview"), "user_id": current_user_id()})
    if not doc:
        raise HTTPException(404, "Interview session not found")
    return serialize(doc)

@router.post("/ai/resume-chat")
async def resume_chat(payload: dict):
    if not gemini_configured():
        raise HTTPException(503, "Gemini is not configured. Add GEMINI_API_KEY to .env and restart the API.")
    resume_id = str(payload.get("resume_id", ""))
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(400, "question is required")
    resume = await get_resume_or_404(resume_id)
    job_id = payload.get("job_id")
    job = await get_job_or_404(job_id) if job_id else None
    try:
        answer = generate_resume_chat_reply(question, resume["text"], job)
    except Exception as exc:
        raise HTTPException(502, f"AI assistant failed: {exc}")
    return {"answer": answer}
