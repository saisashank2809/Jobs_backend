"""
Experience filter utility for the scraper module.
Filters jobs to include only fresher / 0-2 years experience roles.
"""

import re

# Keywords that strongly indicate an entry-level role
ENTRY_LEVEL_KEYWORDS = {
    "analyst",
    "associate",
    "intern",
    "trainee",
    "fresher",
    "graduate",
    "entry",
    "junior",
    "apprentice",
}

# Keywords that strongly indicate a senior role (reject these)
SENIOR_KEYWORDS = {
    "senior",
    "manager",
    "director",
    "vp",
    "principal",
    "lead",
    "head",
    "architect",
    "partner",
    "chief",
    "specialist",
    "expert",
    "experienced",
    "executive",
}


def is_entry_level(title: str, experience_text: str = "") -> bool:
    """
    Returns True if the job is likley for a fresher or 0-2 years experience.
    Rejects senior roles based on title keywords.
    Accepts roles with 0-2 years experience mentioned or entry-level keywords.
    """
    title_lower = title.lower()

    # 1. Reject if title contains senior keywords
    # Exception: "Senior Analyst" might be okay in some contexts, but usually >2 yrs.
    # For now, we'll be strict to avoid noise.
    if any(kw in title_lower for kw in SENIOR_KEYWORDS):
        return False

    # 2. Accept if title contains entry-level keywords
    if any(kw in title_lower for kw in ENTRY_LEVEL_KEYWORDS):
        return True

    # 4. Reject if experience text mentions >2 years using regex
    # Matches: "3-5 years", "5+ years", "6+ years", "three years", etc.
    if re.search(r'\b[3-9]\s*\+?\s*years?\b', experience_text, re.I):
        return False
    if re.search(r'\b(three|four|five|six|seven|eight|nine|ten)\s*years?\b', experience_text, re.I):
        return False

    # Default to True to allow jobs that don't explicitly require high experience
    return True
