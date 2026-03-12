"""Debug: print all links found on a career page to understand the URL patterns."""
import asyncio
import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

async def debug_links():
    url = "https://careers.microsoft.com"
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        html = await page.content()
        await page.close()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    print(f"All links on {url}:\n")
    
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(strip=True)[:60]
        if len(text) > 3:
            print(f"  [{text}] -> {href}")

if __name__ == "__main__":
    asyncio.run(debug_links())
