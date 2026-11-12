import re

SKILL_VOCABULARY = [
    "python", "java", "javascript", "typescript", "c++", "c#", "php", "react",
    "node.js", "express", "fastapi", "django", "flask", "html", "css", "tailwind",
    "bootstrap", "mongodb", "mysql", "postgresql", "sql", "redis", "git", "github",
    "docker", "kubernetes", "aws", "azure", "gcp", "machine learning", "deep learning",
    "natural language processing", "nlp", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "power bi", "excel", "rest api", "graphql",
    "communication", "leadership", "problem solving", "data structures", "algorithms",
    "llm", "generative ai", "langchain", "chromadb", "faiss", "opencv", "computer vision"
]

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())

def extract_skills(text: str) -> list[str]:
    normalized = normalize(text)
    found = []
    for skill in SKILL_VOCABULARY:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, normalized):
            found.append(skill)
    return sorted(set(found))

def extract_sections(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections = {"education": [], "experience": [], "projects": [], "certifications": []}
    headings = {
        "education": ("education", "academic", "qualification"),
        "experience": ("experience", "employment", "work history", "internship"),
        "projects": ("projects", "personal projects"),
        "certifications": ("certifications", "certificates", "courses"),
    }
    active = None
    for line in lines:
        low = line.lower().strip(" :")
        matched = next((name for name, keys in headings.items()
                        if any(low == key or low.startswith(key + " ") for key in keys)), None)
        if matched:
            active = matched
        elif active:
            sections[active].append(line)
    return {key: value[:40] for key, value in sections.items()}

def improvement_suggestions(resume_text: str, skills: list[str]) -> list[str]:
    low = resume_text.lower()
    suggestions = []
    if len(resume_text.split()) < 120:
        suggestions.append("Add more detail about projects, responsibilities, and measurable outcomes.")
    if not re.search(r"\b\d+%|\b\d+\+?\s*(users|clients|projects|months|years)\b", low):
        suggestions.append("Add measurable impact where truthful, such as users served, load time reduced, or project scale.")
    if "project" not in low:
        suggestions.append("Include a Projects section with your role, technology stack, and outcome.")
    if not any(x in low for x in ("linkedin", "github", "portfolio")):
        suggestions.append("Add relevant professional links such as LinkedIn, GitHub, or a portfolio.")
    if not skills:
        suggestions.append("Use a clearly labelled Skills section so relevant technologies are easier to identify.")
    return suggestions or ["Keep each experience bullet specific, concise, and focused on your contribution."]
