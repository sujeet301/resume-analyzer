import re
from html import unescape
import httpx
from app.services.analyzer import extract_skills


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def normalize_arbeitnow(item: dict) -> dict:
    description = clean_html(item.get("description", ""))
    tags = item.get("tags") or []
    skills = sorted(set(extract_skills(f"{item.get('title', '')} {description} {' '.join(tags)}")))
    return {
        "external_id": str(item.get("slug", "")),
        "title": item.get("title", "Untitled role"),
        "company": item.get("company_name", "Unknown company"),
        "location": item.get("location", ""),
        "description": description,
        "url": item.get("url", ""),
        "created_at": item.get("created_at"),
        "remote": bool(item.get("remote", False)),
        "job_types": item.get("job_types") or [],
        "tags": tags,
        "required_skills": skills,
        "source": "Arbeitnow",
        "source_url": "https://www.arbeitnow.com/",
        "description_is_snippet": False,
    }


async def search_arbeitnow(query: str, location: str, remote: bool, page: int = 1) -> list[dict]:
    # Public API; attribution and link-back are required by Arbeitnow's terms.
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"page": page},
        )
        response.raise_for_status()
        payload = response.json()
    jobs = [normalize_arbeitnow(item) for item in payload.get("data", [])]
    terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9+#.]+", query) if len(term) > 1]
    if terms:
        jobs = [job for job in jobs if any(
            term in (job["title"] + " " + job["description"] + " " + " ".join(job["tags"])).lower()
            for term in terms
        )]
    if location:
        # This board is predominantly Germany/Europe; apply a conservative text filter.
        loc = location.lower()
        jobs = [job for job in jobs if loc in job["location"].lower() or (remote and job["remote"])]
    if remote:
        jobs = [job for job in jobs if job["remote"]]
    return jobs
