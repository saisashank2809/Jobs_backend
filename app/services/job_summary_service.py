"""
Utilities for building a consistent role overview and cleaned skill list.
"""

from __future__ import annotations

import html
import re
from typing import Any


HTML_TAG_REGEX = re.compile(r"<[^>]+>")
WHITESPACE_REGEX = re.compile(r"\s+")
SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+")

GENERIC_SENTENCE_PATTERNS = [
    re.compile(r"^(about us|job description|overview|responsibilities|requirements|preferred|qualifications?)[:\s-]*$", re.I),
    re.compile(r"^(posted|apply|click|equal opportunity|privacy|benefits)[:\s-]", re.I),
    re.compile(r"cookies|accessibility|terms of use|legal|policy", re.I),
]

GENERIC_SKILL_PATTERNS = [
    re.compile(r"^communication skills?$", re.I),
    re.compile(r"^team player$", re.I),
    re.compile(r"^problem solving$", re.I),
    re.compile(r"^detail oriented$", re.I),
]

SKILL_CANDIDATES = [
    "JavaScript",
    "TypeScript",
    "React",
    "Node.js",
    "Python",
    "Java",
    "C++",
    "C#",
    "SQL",
    "Excel",
    "Power BI",
    "Tableau",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Git",
    "REST API",
    "GraphQL",
    "Machine Learning",
    "Data Analysis",
    "Data Modeling",
    "ETL",
    "Snowflake",
    "DBT",
    "Airflow",
    "SAP",
    "ServiceNow",
    "Jira",
    "Linux",
    "Testing",
    "Automation",
    "Networking",
    "Troubleshooting",
    "Customer Support",
    "Financial Modeling",
    "SEO",
    "SEM",
    "Marketing",
    "Sales",
]


def strip_html(value: str = "") -> str:
    value = re.sub(r"<br\s*/?>", ". ", value, flags=re.I)
    value = re.sub(r"</(p|div|li|h\d|section|article)>", ". ", value, flags=re.I)
    value = html.unescape(value)
    value = HTML_TAG_REGEX.sub(" ", value)
    return WHITESPACE_REGEX.sub(" ", value).strip()


def clean_sentence(sentence: str = "") -> str:
    sentence = re.sub(r"\s*\|\s*", " ", sentence)
    sentence = re.sub(r"\s*[-â€“]\s*", " ", sentence)
    sentence = WHITESPACE_REGEX.sub(" ", sentence).strip()
    if sentence and not sentence.endswith((".", "!", "?")):
        sentence += "."
    return sentence


def is_useful_sentence(sentence: str) -> bool:
    if not sentence or len(sentence) < 35 or len(sentence) > 220:
        return False
    return not any(pattern.search(sentence) for pattern in GENERIC_SENTENCE_PATTERNS)


def normalize_skills(job: dict[str, Any], max_items: int = 8) -> list[str]:
    explicit = job.get("key_skills") or job.get("skills_required") or []
    normalized: list[str] = []
    seen: set[str] = set()

    for skill in explicit:
        cleaned = WHITESPACE_REGEX.sub(" ", str(skill or "")).strip()
        if not cleaned or len(cleaned) > 60:
            continue
        if any(pattern.search(cleaned) for pattern in GENERIC_SKILL_PATTERNS):
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
        if len(normalized) >= max_items:
            return normalized

    haystack = f"{job.get('title', '')} {strip_html(job.get('description_raw', ''))}".lower()
    for candidate in SKILL_CANDIDATES:
        if len(normalized) >= max_items:
            break
        key = candidate.lower()
        if key in seen:
            continue
        if key in haystack:
            seen.add(key)
            normalized.append(candidate)

    return normalized


def build_role_overview(job: dict[str, Any], min_items: int = 6, max_items: int = 8) -> list[str]:
    existing = job.get("role_overview")
    if isinstance(existing, list) and existing:
        return [clean_sentence(str(sentence)) for sentence in existing if str(sentence).strip()][:max_items]

    title = str(job.get("cleanTitle") or job.get("title") or "This role").strip()
    company = str(job.get("company_name") or "the company").strip()
    location = str(job.get("cleanLocation") or job.get("location") or "").strip()
    skills = normalize_skills(job, max_items=8)

    description = strip_html(job.get("description_raw", ""))
    candidate_sentences = [
        clean_sentence(sentence) for sentence in SENTENCE_SPLIT_REGEX.split(description) if is_useful_sentence(clean_sentence(sentence))
    ]

    overview: list[str] = []
    seen: set[str] = set()

    def push(sentence: str) -> None:
        cleaned = clean_sentence(sentence)
        key = cleaned.lower()
        if not cleaned or key in seen:
            return
        seen.add(key)
        overview.append(cleaned)

    push(f"{title} is a role at {company} where you will contribute to the team's main work and day-to-day priorities")
    for sentence in candidate_sentences[:6]:
        push(sentence)

    if len(overview) < min_items:
        if skills:
            push(f"The role highlights skills such as {', '.join(skills[:4])}, so candidates should be comfortable using them in real work situations")
        else:
            push("The role expects practical problem solving, clear communication, and the ability to learn the tools used by the team")

    if len(overview) < min_items:
        if location:
            push(f"The role is based in {location}, so you should be ready to work in that setup and collaborate with the local or distributed team")
        else:
            push("The work setup is not fully specified, so candidates should confirm location and team expectations during the process")

    if len(overview) < max_items:
        push(f"{title} suits candidates who can learn quickly, stay organized, and work well with the team on regular business goals")

    if len(overview) < max_items:
        push("Freshers can use this role to build hands-on experience, while experienced candidates can use it to deepen their domain knowledge and delivery impact")

    return overview[:max_items]


def build_short_description(job: dict[str, Any], max_sentences: int = 3) -> str:
    """Build a 2-3 sentence plain-text summary from role_overview or description_raw."""
    overview = job.get("role_overview")
    if isinstance(overview, list) and overview:
        sentences = [clean_sentence(str(s)) for s in overview if str(s).strip()][:max_sentences]
        if sentences:
            return " ".join(sentences)

    # Fallback: extract from description_raw
    description = strip_html(job.get("description_raw", ""))
    candidate_sentences = [
        clean_sentence(s)
        for s in SENTENCE_SPLIT_REGEX.split(description)
        if is_useful_sentence(clean_sentence(s))
    ][:max_sentences]

    if candidate_sentences:
        return " ".join(candidate_sentences)

    title = str(job.get("title") or "This role").strip()
    company = str(job.get("company_name") or "the company").strip()
    return f"{title} is a role at {company}. Visit the website for full details."


_EXPERIENCE_MAP = [
    (re.compile(r"fresher|intern|entry.?level|0\s*[-–]\s*0|graduate|trainee", re.I), "Freshers"),
    (re.compile(r"0\s*[-–]\s*1|0\s*to\s*1|less\s*than\s*1", re.I), "0-1 years"),
    (re.compile(r"0\s*[-–]\s*2|0\s*to\s*2|1\s*[-–]\s*2|1\s*to\s*2|1\s*\+", re.I), "0-2 years"),
    (re.compile(r"1\s*[-–]\s*3|1\s*to\s*3|2\s*[-–]\s*3|2\s*to\s*3|2\s*\+", re.I), "1-3 years"),
    (re.compile(r"2\s*[-–]\s*5|2\s*to\s*5|3\s*[-–]\s*5|3\s*to\s*5|4\s*[-–]\s*5|3\s*\+|4\s*\+", re.I), "3-5 years"),
    (re.compile(r"5\s*[-–]\s*\d|5\s*to\s*\d|5\s*\+|senior|lead|principal|staff|manager", re.I), "5+ years"),
]


def normalize_experience_range(job: dict[str, Any]) -> str:
    """Normalize the free-text experience field into a standard label."""
    exp_raw = str(job.get("experience") or "").strip()
    if exp_raw.lower() == "not specified":
        exp_raw = ""
        
    title = str(job.get("title") or "").strip()
    combined = f"{exp_raw} {title}".strip()

    # Check exp_raw first, then combined (title) for keyword matches
    for source in [exp_raw, combined]:
        if not source:
            continue
        for pattern, label in _EXPERIENCE_MAP:
            if pattern.search(source):
                return label

    # Numeric fallback: "3" → "3-5 years"
    num_match = re.search(r"(\d+)", exp_raw)
    if num_match:
        years = int(num_match.group(1))
        if years == 0:
            return "Freshers"
        if years <= 1:
            return "0-1 years"
        if years <= 2:
            return "0-2 years"
        if years <= 3:
            return "1-3 years"
        if years <= 5:
            return "3-5 years"
        return "5+ years"

    # Text-mining fallback from overview/description
    if not exp_raw:
        haystack = " ".join(job.get("role_overview") or []) + " " + job.get("description_raw", "")
        # First check explicit "X years of experience" statements
        num_match = re.search(r"(\d+)\+?\s*years?(?:\s+of)?\s+experience", haystack, re.I)
        if num_match:
            years = int(num_match.group(1))
            if years == 0:
                return "Freshers"
            if years <= 1:
                return "0-1 years"
            if years <= 2:
                return "0-2 years"
            if years <= 3:
                return "1-3 years"
            if years <= 5:
                return "3-5 years"
            return "5+ years"
            
        # Then fallback to general map patterns
        for pattern, label in _EXPERIENCE_MAP:
            if pattern.search(haystack):
                return label

    return "Not specified"


def normalize_location(job: dict[str, Any]) -> str:
    """Clean and normalize the stored location field."""
    loc = str(job.get("location") or "").strip()
    title = str(job.get("title") or "").strip()

    # Remote detection
    if not loc or "remote" in loc.lower() or "remote" in title.lower():
        return "Remote"

    # Title-case the first segment
    first = loc.split(",")[0].strip()
    cleaned = first.replace("_", " ").strip()
    if cleaned:
        cleaned = cleaned.title()

    return cleaned or "India"


def get_qualification_fallback(job: dict[str, Any]) -> str:
    """Mine text for basic educational requirements."""
    haystack = " ".join(job.get("role_overview") or []) + " " + job.get("description_raw", "")
    haystack_lower = haystack.lower()
    
    if re.search(r"b\.?e|b\.?tech|bachelor.*?engineering|bachelor.*?technology", haystack_lower):
        return "B.E/B.Tech"
    if re.search(r"m\.?e|m\.?tech|master.*?engineering|master.*?technology", haystack_lower):
        return "M.E/M.Tech"
    if re.search(r"mba|master.*?business", haystack_lower):
        return "MBA"
    if re.search(r"bca|b\.?c\.?a", haystack_lower):
        return "BCA"
    if re.search(r"mca|m\.?c\.?a", haystack_lower):
        return "MCA"
    if re.search(r"bachelor.*?degree|bs/ba|b\.?s\.?|b\.?a\.?|any graduate", haystack_lower):
        return "Bachelor's Degree"
    if re.search(r"master.*?degree|m\.?s\.?|m\.?a\.?", haystack_lower):
        return "Master's Degree"
        
    return "Not specified"



# ── Salary Mining ──────────────────────────────────────────────────────────────

# Ordered by specificity — more specific patterns first
_SALARY_PATTERNS = [
    # INR: ₹5 LPA, ₹5-10 LPA, 5 LPA to 10 LPA, Rs. 5,00,000, INR 6 LPA, CTC ₹8 LPA
    (re.compile(
        r"(?:ctc|salary|package|compensation|stipend|pay|remuneration)[\s:]*"
        r"(?:of\s+|upto\s+|up\s+to\s+|range\s+)?"
        r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*"
        r"(?:[-–to]+\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*)?"
        r"(lpa|l\.?p\.?a\.?|lakhs?|lac|lacs|l/ann|lakh per annum|crore|cr)",
        re.I
    ), "INR_LPA"),
    # Plain LPA without prefix: 5-10 LPA, ₹6 LPA
    (re.compile(
        r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)\s*"
        r"(?:[-–to]+\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*)?"
        r"(lpa|l\.?p\.?a\.?|lakhs?|lac|lacs|lakh per annum)",
        re.I
    ), "INR_LPA"),
    (re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:[-–to]+\s*(\d+(?:\.\d+)?)\s*)?"
        r"(lpa|l\.?p\.?a\.?|lakhs?\s+per\s+annum|lakh per annum)",
        re.I
    ), "INR_LPA"),
    # INR full numbers: ₹5,00,000 - ₹8,00,000
    (re.compile(
        r"(?:₹|rs\.?|inr)\s*([\d,]+)\s*(?:[-–to]+\s*(?:₹|rs\.?|inr)?\s*([\d,]+))?",
        re.I
    ), "INR_NUM"),
    # USD: $80,000 - $120,000 / year, $50k-$80k
    (re.compile(
        r"\$\s*([\d,]+(?:\.\d+)?)\s*k?\s*(?:[-–to]+\s*\$?\s*([\d,]+(?:\.\d+)?)\s*k?)?"
        r"(?:\s*(?:per\s+)?(?:year|yr|annum|pa|annually))?",
        re.I
    ), "USD"),
    # GBP
    (re.compile(
        r"£\s*([\d,]+(?:\.\d+)?)\s*k?\s*(?:[-–to]+\s*£?\s*([\d,]+(?:\.\d+)?)\s*k?)?",
        re.I
    ), "GBP"),
]


def _format_inr_lpa(val: str) -> str:
    """Format a float string as LPA with one decimal if needed."""
    try:
        f = round(float(val), 1)
        return f"{int(f)} LPA" if f == int(f) else f"{f} LPA"
    except Exception:
        return f"{val} LPA"


def mine_salary_from_text(text: str) -> str | None:
    """
    Extract real salary from job description text.
    Returns a formatted string like '₹5 LPA - ₹10 LPA' or '$80,000 - $120,000/yr'
    or None if no salary mentioned.
    """
    if not text:
        return None
    # Strip HTML first
    clean = strip_html(text)

    for pattern, kind in _SALARY_PATTERNS:
        m = pattern.search(clean)
        if not m:
            continue

        groups = [g for g in m.groups() if g is not None]
        if not groups:
            continue

        if kind == "INR_LPA":
            # groups could be (min, max, unit) or (min, unit) depending on pattern
            nums = []
            for g in groups:
                g_clean = g.strip().replace(",", "")
                try:
                    float(g_clean)
                    nums.append(g_clean)
                except ValueError:
                    pass  # skip unit strings like 'LPA'
            if not nums:
                continue
            # Sanity check: LPA values should be between 0.5 and 200
            valid = [n for n in nums if 0.5 <= float(n) <= 200]
            if not valid:
                continue
            if len(valid) >= 2:
                return f"₹{_format_inr_lpa(valid[0])} - ₹{_format_inr_lpa(valid[1])}"
            return f"₹{_format_inr_lpa(valid[0])}"

        elif kind == "INR_NUM":
            nums = [g.replace(",", "") for g in groups if g]
            valid = []
            for n in nums:
                try:
                    v = int(n)
                    if v >= 10000:  # at least ₹10,000 to filter noise
                        valid.append(v)
                except ValueError:
                    pass
            if not valid:
                continue
            if len(valid) >= 2:
                return f"₹{valid[0]:,} - ₹{valid[1]:,}"
            return f"₹{valid[0]:,}"

        elif kind == "USD":
            nums = [g.replace(",", "") for g in groups if g]
            valid = []
            for n in nums:
                try:
                    v = float(n)
                    if v < 1000:  # k suffix — multiply
                        v *= 1000
                    if v >= 5000:
                        valid.append(v)
                except ValueError:
                    pass
            if not valid:
                continue
            if len(valid) >= 2:
                inr1 = valid[0] * 85 / 100000
                inr2 = valid[1] * 85 / 100000
                return f"₹{_format_inr_lpa(str(inr1))} - ₹{_format_inr_lpa(str(inr2))}"
            inr1 = valid[0] * 85 / 100000
            return f"₹{_format_inr_lpa(str(inr1))}"

        elif kind == "GBP":
            nums = [g.replace(",", "") for g in groups if g]
            valid = []
            for n in nums:
                try:
                    v = float(n)
                    if v < 1000:
                        v *= 1000
                    if v >= 5000:
                        valid.append(v)
                except ValueError:
                    pass
            if not valid:
                continue
            if len(valid) >= 2:
                inr1 = valid[0] * 105 / 100000
                inr2 = valid[1] * 105 / 100000
                return f"₹{_format_inr_lpa(str(inr1))} - ₹{_format_inr_lpa(str(inr2))}"
            inr1 = valid[0] * 105 / 100000
            return f"₹{_format_inr_lpa(str(inr1))}"

    return None


def enrich_job_summary(job: dict[str, Any]) -> dict[str, Any]:
    """Central formatter: converts raw DB row into card-ready data."""
    enriched = dict(job)
    enriched["key_skills"] = normalize_skills(enriched, max_items=8)
    enriched["role_overview"] = build_role_overview(enriched)
    enriched["short_description"] = build_short_description(enriched)
    enriched["experience_range"] = normalize_experience_range(enriched)
    enriched["location"] = normalize_location(enriched)

    # Pass through fields that already exist in DB, with safe fallbacks
    if not enriched.get("qualification") or enriched.get("qualification") == "Not specified":
        enriched["qualification"] = get_qualification_fallback(enriched)

    # Only show salary if explicitly scraped or mined from description text
    existing_salary = enriched.get("salary_range")
    if existing_salary and str(existing_salary).strip().lower() not in ("none", "not specified", ""):
        enriched["salary_range"] = str(existing_salary).strip()
    else:
        mined = mine_salary_from_text(enriched.get("description_raw", ""))
        enriched["salary_range"] = mined  # None if not found

    return enriched
