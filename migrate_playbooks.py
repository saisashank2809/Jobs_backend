import os
from supabase import create_client, Client
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

COMPANIES = [
    {
        "slug": "tcs",
        "name": "TCS",
        "industry": "IT Services",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/9/9b/TATA_Consultancy_Services_Logo.svg",
        "hq": "Mumbai, India",
        "locations": ["Across India"],
        "category": "Major IT Services & Consulting",
        "hiring_seasons": "Mass Recruitment (July-Sept)",
        "hiring_type": "Heavy Campus Placements",
        "hiring_zone": "on-campus",
        "cover_image": "/tcs_office.png",
        "roles": ["Ninja Role", "Digital Role", "Prime Role"],
        "difficulty": "Easy",
        "difficulty_level": 2,
        "rounds_count": 3,
        "eligibility": {
            "academic": "60% or 6.0 CGPA throughout",
            "qualification": "BE/B.Tech, ME/M.Tech, MCA, M.Sc",
            "gapInEducation": "Max 24 months",
            "backlogs": "No active backlogs"
        },
        "selection_process": [
            { "name": "Foundation Section", "details": "Numerical, Verbal, and Reasoning ability." },
            { "name": "Advanced Section", "details": "Advanced Quants, Reasoning, and Coding." },
            { "name": "Interview", "details": "Technical + Managerial + HR round." }
        ],
        "test_pattern": [
            { "section": "Foundation (Numerical)", "questions": "20 Qs", "duration": "25 mins" },
            { "section": "Foundation (Verbal)", "questions": "25 Qs", "duration": "25 mins" },
            { "section": "Foundation (Reasoning)", "questions": "20 Qs", "duration": "25 mins" },
            { "section": "Advanced (Quants)", "questions": "10 Qs", "duration": "25 mins" },
            { "section": "Advanced (Coding)", "questions": "3 Qs", "duration": "90 mins" }
        ],
        "syllabus": [
            { "round": "Foundation", "topics": ["Averages", "Percentages", "Ratios", "Syllogism", "Series"] },
            { "round": "Advanced", "topics": ["Complex Quants", "Advanced Data Structures", "Algorithms"] }
        ],
        "registration_process": [
            "Visit TCS NextStep portal",
            "Register under 'IT' category",
            "Fill application form and generate CT/DT ID",
            "Submit application"
        ],
        "compensation": {
            "base": "3.5 LPA - 9 LPA",
            "bonus": "N/A",
            "stock": "N/A",
            "relocation": "Variable",
            "totalYear1": "₹4,00,000 - ₹9,00,000"
        },
        "prep_focus": "Practice quantitative aptitude. For Digital/Prime, focus on advanced DSA.",
        "insider_scoop": "Communication skills are the ultimate dealbreaker. Digital role requires strong coding speed.",
        "jobs_link": "/jobs?company=TCS"
    },
    {
        "slug": "google",
        "name": "Google",
        "industry": "Tech",
        "logo": "https://logo.clearbit.com/google.com",
        "hq": "Mountain View, CA",
        "locations": ["Bangalore", "Hyderabad", "Pune", "Gurgaon"],
        "category": "Global Big Tech & AI Labs",
        "hiring_seasons": "Primarily Fall (Sept-Nov) for next summer, occasional Spring hires.",
        "hiring_type": "Off-Campus / Referral heavy",
        "hiring_zone": "off-campus",
        "cover_image": "/google_office.png",
        "roles": ["SDE", "Data Analyst", "Cloud Engineer"],
        "difficulty": "Hard",
        "difficulty_level": 4,
        "rounds_count": 4,
        "eligibility": {
            "academic": "Degree in CS or related technical field",
            "qualification": "B.Tech/BE, M.Tech/ME, PhD",
            "backlogs": "No active backlogs",
            "experience": "Freshers / University Grads"
        },
        "selection_process": [
            { "name": "Online Assessment", "details": "60-90 mins, 2 DSA questions (Medium/Hard)." },
            { "name": "Recruiter Screen", "details": "Informal call to discuss background and role fit." },
            { "name": "Technical Interviews", "details": "3-4 rounds of DSA problem solving on shared editor." },
            { "name": "Googliness", "details": "Behavioral round focused on leadership and culture fit." }
        ],
        "test_pattern": [
            { "section": "Coding", "questions": "2 Qs", "duration": "90 mins" },
            { "section": "Theory/MCQ", "questions": "N/A", "duration": "N/A" }
        ],
        "syllabus": [
            { "round": "Coding", "topics": ["Graphs", "Dynamic Programming", "Recursion", "Backtracking"] },
            { "round": "Theory", "topics": ["OS Internals", "Networking Basics", "Memory Management"] }
        ],
        "registration_process": [
            "Apply via Google Careers portal",
            "Optimize resume with measurable accomplishments",
            "Complete the Online Assessment if invited",
            "Wait for recruiter outreach"
        ],
        "compensation": {
            "base": "₹18L - ₹25L",
            "bonus": "₹2L - ₹3L",
            "stock": "₹30L+ over 4 years",
            "relocation": "₹2L",
            "totalYear1": "₹28L - ₹35L"
        },
        "prep_focus": "80% Graphs/DP. High focus on time and space complexity analysis.",
        "insider_scoop": "Communication is key. Explain your thought process out loud even if you haven't found the optimal solution yet.",
        "jobs_link": "/jobs?company=Google"
    }
]

def migrate():
    for company in COMPANIES:
        print(f"Migrating {company['name']}...")
        result = supabase.table("playbooks").upsert(company, on_conflict="slug").execute()
        print(f"Result: {result}")

if __name__ == "__main__":
    migrate()
