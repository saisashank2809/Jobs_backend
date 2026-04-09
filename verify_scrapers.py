import asyncio
from app.dependencies import get_scraper

async def verify():
    for name in ["greenhouse", "lever", "smartrecruiters", "ashby", "breezy", "workable", "workday"]:
        print(f"Checking {name} scraper...")
        try:
            s = get_scraper(name)
            print(f"Success: {s.COMPANY_NAME} scraper loaded.")
        except Exception as e:
            print(f"Failed {name}: {e}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(verify())
