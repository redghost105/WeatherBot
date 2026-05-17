#!/usr/bin/env python3
"""
Scrape all source URLs from the knowledge base
and save clean markdown versions using requests + html2text
"""
import json
import re
from pathlib import Path
from datetime import datetime
import sys

try:
    import requests
    from bs4 import BeautifulSoup
    import html2text
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "html2text", "--break-system-packages"], check=True)
    import requests
    from bs4 import BeautifulSoup
    import html2text

# URLs to scrape
URLS = [
    "https://arxiv.org/abs/2604.11791",
    "https://arxiv.org/pdf/2508.03474",
    "https://electricity.heatmap.news/",
    "https://github.com/FrondEnt/PolymarketBTC15mAssistant",
    "https://github.com/Jon-Becker/prediction-market-analysis",
    "https://github.com/Polymarket/polymarket-cli",
    "https://github.com/TauricResearch/TradingAgents",
    "https://github.com/alsk1992/CloddsBot",
    "https://github.com/alteregoeth-ai/weatherbot",
    "https://github.com/calesthio/Crucix",
    "https://github.com/evan-kolberg/prediction-market-backtesting",
    "https://github.com/onyx-dot-app/onyx",
    "https://github.com/suislanchez/polymarket-kalshi-weather-bot",
    "https://github.com/terauss/Polymarket-Copy-Trading-Bot",
]

# Output directory
WIKI_ROOT = Path.home() / ".llm-wiki-mind"
OUTPUT_DIR = WIKI_ROOT / "raw" / "scraped_sources"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(url: str) -> str:
    """Convert URL to safe filename"""
    # Extract domain/path
    if "github.com" in url:
        match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
    elif "arxiv.org" in url:
        match = re.search(r'arxiv\.org/(?:abs|pdf)/([^/]+)', url)
        if match:
            return f"arxiv-{match.group(1)}"
    elif "heatmap.news" in url:
        return "electricity-heatmap"

    # Fallback: hash the URL
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:12]

def scrape_url(url: str) -> dict:
    """Scrape a single URL using requests + BeautifulSoup"""
    try:
        print(f"Scraping: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title = None
        if soup.title:
            title = soup.title.string
        elif soup.find('h1'):
            title = soup.find('h1').get_text()
        else:
            title = "Untitled"

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()

        # Convert to markdown using html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0

        markdown = h.handle(str(soup))

        return {
            "url": url,
            "success": True,
            "title": title or "Untitled",
            "markdown": markdown or "",
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return {
            "url": url,
            "success": False,
            "title": "Error",
            "markdown": "",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Main scraper"""
    results = []

    for url in URLS:
        result = scrape_url(url)
        results.append(result)

        # Save individual file
        if result["success"] and result["markdown"]:
            filename = sanitize_filename(url)
            filepath = OUTPUT_DIR / f"{filename}.md"

            content = f"""---
source_url: {url}
title: {result['title']}
scraped_date: {result['timestamp']}
---

# {result['title']}

**Source:** [{url}]({url})

---

{result['markdown']}
"""
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"✓ Saved: {filename}.md")
        else:
            print(f"✗ Failed: {result['error']}")

    # Save summary
    summary_file = OUTPUT_DIR / "SCRAPE_SUMMARY.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Print report
    successful = sum(1 for r in results if r["success"])
    print(f"\n{'='*60}")
    print(f"Scraping Complete!")
    print(f"{'='*60}")
    print(f"Successful: {successful}/{len(URLS)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
