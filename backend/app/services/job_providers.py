import re
from html import unescape
import httpx
from app.core.config import settings
from app.services.analyzer import extract_skills


def clean_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()


def normalize_adzuna(item: dict) -> dict:
    description = clean_html(item.get("description", ""))
    location = (item.get("location") or {}).get("display_name", "")
    company = (item.get("company") or {}).get("display_name", "Unknown company")
    skills = extract_skills(f"{item.get('title', '')} {description}")
    return {
        "external_id": str(item.get("id", "")),
        "title": item.get("title", "Untitled role"),
        "company": company,
        "location": location,
        "description": description,
        "url": item.get("redirect_url", ""),
        "created_at": item.get("created", ""),
        "salary_min": item.get("salary_min"),
        "salary_max": item.get("salary_max"),
        "salary_is_predicted": bool(item.get("salary_is_predicted", 0)),
        "contract_type": item.get("contract_type", ""),
        "contract_time": item.get("contract_time", ""),
        "required_skills": skills,
        "source": "Adzuna",
        "source_url": "https://www.adzuna.in/",
        "description_is_snippet": True,
    }


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


async def search_adzuna(query: str, location: str, country: str, page: int, limit: int) -> list[dict]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        raise RuntimeError("Adzuna is not configured. Add ADZUNA_APP_ID and ADZUNA_APP_KEY to .env.")
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": limit,
        "what": query,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    return [normalize_adzuna(item) for item in payload.get("results", [])]


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
