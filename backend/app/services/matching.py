from app.services.embeddings import embed_texts, cosine_similarity
from app.services.analyzer import extract_skills

def build_job_text(job: dict) -> str:
    skills = ", ".join(job.get("required_skills", []))
    return (
        f"Job title: {job.get('title', '')}. Company: {job.get('company', '')}. "
        f"Experience: {job.get('experience_level', '')}. "
        f"Description: {job.get('description', '')}. Required skills: {skills}."
    )

def build_resume_text(resume: dict) -> str:
    return (
        f"Resume content: {resume.get('text', '')[:12000]}. "
        f"Detected skills: {', '.join(resume.get('skills', []))}."
    )

def match_resume_to_job(resume: dict, job: dict) -> dict:
    resume_skills = set(resume.get("skills") or extract_skills(resume.get("text", "")))
    required = {s.strip().lower() for s in job.get("required_skills", []) if s.strip()}
    matched = sorted(resume_skills & required)
    missing = sorted(required - resume_skills)
    coverage = len(matched) / len(required) if required else 0.0

    resume_vector, job_vector = embed_texts([
        build_resume_text(resume),
        build_job_text(job),
    ])
    semantic = max(0.0, min(1.0, cosine_similarity(resume_vector, job_vector)))

    # Weighted score is a ranking aid, not a probability of getting hired.
    final_score = round((0.65 * semantic + 0.35 * coverage) * 100)
    return {
        "match_score": final_score,
        "semantic_similarity": round(semantic * 100, 2),
        "skill_coverage": round(coverage * 100, 2),
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required_skills": len(required),
        "score_method": "65% sentence-embedding similarity + 35% required-skill coverage",
        "score_disclaimer": "This is an approximate relevance score, not a hiring probability or guarantee."
    }
