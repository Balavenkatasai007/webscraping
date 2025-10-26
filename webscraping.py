import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from urllib.parse import urljoin
from urllib import robotparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://quotes.toscrape.com"

def is_allowed(base_url, user_agent="my-scraper-bot"):
    """
    Check robots.txt to see if scraping the site is allowed for our UA.
    If robots.txt can't be fetched, the function conservatively returns True.
    """
    rp = robotparser.RobotFileParser()
    rp.set_url(urljoin(base_url, "robots.txt"))
    try:
        rp.read()
    except Exception:
        # If we can't fetch robots.txt for some reason, continue (but in real projects warn/log)
        return True
    return rp.can_fetch(user_agent, base_url)

def make_session():
    """Create a requests session with retries and a sensible User-Agent."""
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.3, status_forcelist=(500,502,503,504))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36 (compatible; MyScraper/1.0)"
    })
    return s

def parse_quotes(soup):
    """Extract quote text, author, and tags from a BeautifulSoup page."""
    items = []
    for q in soup.select(".quote"):
        text_el = q.select_one(".text")
        author_el = q.select_one(".author")
        tags_el = q.select(".tags .tag")
        text = text_el.get_text(strip=True) if text_el else ""
        author = author_el.get_text(strip=True) if author_el else ""
        tags = [t.get_text(strip=True) for t in tags_el] if tags_el else []
        items.append({
            "text": text,
            "author": author,
            "tags": ";".join(tags)  # semi-colon separated list inside a cell
        })
    return items

def scrape(max_pages=None):
    if not is_allowed(BASE_URL):
        print("Scraping disallowed by robots.txt. Exiting.")
        return

    session = make_session()
    url = BASE_URL
    all_data = []
    page = 1

    while url:
        print(f"[+] Fetching page {page}: {url}")
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[!] Request failed: {e}")
            break

        soup = BeautifulSoup(resp.text, "lxml")
        page_items = parse_quotes(soup)
        all_data.extend(page_items)

        # pagination: look for <li class="next"><a href="/page/2/">Next</a></li>
        next_link = soup.select_one("li.next > a")
        if next_link and next_link.get("href"):
            url = urljoin(BASE_URL, next_link["href"])
            page += 1
            if max_pages and page > max_pages:
                print("[*] Reached max_pages limit.")
                break
            # polite delay
            time.sleep(random.uniform(1.0, 2.0))
        else:
            url = None

    # Save CSV
    if all_data:
        out_file = "quotes.csv"
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "author", "tags"])
            writer.writeheader()
            writer.writerows(all_data)
        print(f"[+] Saved {len(all_data)} rows to {out_file}")
    else:
        print("[!] No data scraped.")


if __name__ == "__main__":
    scrape()
