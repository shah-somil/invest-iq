#!/usr/bin/env python3
"""
Forbes List Scraper
Scrapes Forbes lists (AI50, Fintech50, etc.) and generates seed JSON files.

Usage:
    python build_seed_from_web.py --list ai50
    python build_seed_from_web.py --list fintech50
    python build_seed_from_web.py --list ai50 --output custom_path.json
"""

import os
import re
import json
import time
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ----------------- CONFIG -----------------
FORBES_LISTS = {
    "ai50": {
        "url": "https://www.forbes.com/lists/ai50/",
        "max_companies": 50,
        "output": "data/seed/forbes_ai50_seed.json"
    },
    "fintech50": {
        "url": "https://www.forbes.com/lists/fintech50/",
        "max_companies": 50,
        "output": "data/seed/forbes_fintech50_seed.json"
    }
}

SLEEP = 0.5

UA_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/119.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.google.com/",
}

sess = requests.Session()
sess.headers.update(UA_HEADERS)
sess.max_redirects = 5

# Track all URLs we scrape
scraped_urls = []

# ----------------- HTTP -----------------
def fetch(url: str, timeout=25) -> Optional[str]:
    """Fetch a URL and track it."""
    try:
        scraped_urls.append(url)
        print(f"  → Fetching: {url}")
        r = sess.get(url, timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return None
    return None

def clean(s: str) -> str:
    """Clean whitespace from string."""
    return re.sub(r"\s+", " ", (s or "").strip())

def to_abs(base: str, href: str) -> str:
    """Convert relative URL to absolute."""
    if not href:
        return ""
    return href if re.match(r"^https?://", href) else urljoin(base, href)

def pick_domain(url: str) -> str:
    """Extract base domain from URL."""
    try:
        netloc = urlparse(url).netloc
        return f"https://{netloc}" if netloc else url
    except Exception:
        return url

def dedupe_limit(pairs: List[Tuple[str, str]], n: int) -> List[Tuple[str, str]]:
    """Deduplicate and limit company pairs."""
    seen = set()
    out = []
    for name, url in pairs:
        key = (name.lower(), url.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append((name, url))
        if len(out) >= n:
            break
    return out

# ----------------- LIST PARSERS -----------------
def parse_jsonld(html: str, base: str) -> List[Tuple[str, str]]:
    """Extract company names and URLs from JSON-LD structured data."""
    soup = BeautifulSoup(html, "html.parser")
    pairs = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            continue
        objs = []
        if isinstance(data, dict):
            if data.get("@type") in ("ItemList", "CollectionPage") and isinstance(data.get("itemListElement"), list):
                objs = data["itemListElement"]
            elif "itemListElement" in data:
                objs = data["itemListElement"]
        elif isinstance(data, list):
            for d in data:
                if isinstance(d, dict) and isinstance(d.get("itemListElement"), list):
                    objs.extend(d["itemListElement"])
        for it in objs:
            name = clean(it.get("name") or it.get("headline") or "")
            url = it.get("url") or ""
            if name and url:
                pairs.append((name, to_abs(base, url)))
    return pairs

def parse_visible_anchors(html: str, base: str) -> List[Tuple[str, str]]:
    """Extract company names and URLs from visible anchor tags."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.find_all("a", href=True):
        txt = clean(a.get_text())
        href = to_abs(base, a["href"])
        if not txt or not href:
            continue
        # Look for profile/company links
        if re.search(r"/profiles?/", href) or re.search(r"/compan(y|ies)/", href) or "/profile/" in href:
            if 2 <= len(txt.split()) <= 8 and len(txt) <= 80 and txt.lower() not in {"see more", "read more"}:
                items.append((txt, href))
    return items

def parse_next_data(html: str, base: str) -> List[Tuple[str, str]]:
    """Extract company names and URLs from Next.js __NEXT_DATA__ script."""
    m = re.search(r'id="__NEXT_DATA__"\s*type="application/json">\s*(\{.*?\})\s*</script>', html, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []
    pairs = []
    
    def walk(o):
        if isinstance(o, dict):
            if "name" in o and "url" in o and isinstance(o["name"], str) and isinstance(o["url"], str):
                nm = clean(o["name"])
                u = to_abs(base, o["url"])
                if nm and u:
                    pairs.append((nm, u))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    
    walk(data)
    # Keep plausible names
    pairs = [(n, u) for (n, u) in pairs if 2 <= len(n.split()) <= 8 and len(n) <= 80]
    return pairs

def parse_table_rows(html: str, base: str) -> List[Tuple[str, str]]:
    """Parse company data from table rows (used by Fintech50 page)."""
    soup = BeautifulSoup(html, "html.parser")
    pairs = []
    
    # Look for tables with company data
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 1:
                # First cell usually has company name/link
                first_cell = cells[0]
                link = first_cell.find("a", href=True)
                if link:
                    name = clean(link.get_text())
                    href = to_abs(base, link["href"])
                    if name and href:
                        pairs.append((name, href))
    
    # Also check for list items with company links
    for li in soup.find_all("li"):
        link = li.find("a", href=True)
        if link:
            txt = clean(link.get_text())
            href = to_abs(base, link["href"])
            if txt and href and ("/profile/" in href or "/company/" in href or "forbes.com" in href):
                if 2 <= len(txt.split()) <= 8:
                    pairs.append((txt, href))
    
    return pairs

def get_company_pairs(list_url: str, max_companies: int) -> Tuple[str, List[Tuple[str, str]]]:
    """Extract company name/URL pairs from Forbes list page using multiple strategies."""
    print(f"\n📋 Extracting companies from: {list_url}")
    
    # Strategy 1: Normal page
    html = fetch(list_url) or ""
    pairs = []
    src = "none"
    
    # Try JSON-LD first
    jsonld_pairs = parse_jsonld(html, list_url)
    if len(jsonld_pairs) >= 30:
        pairs, src = jsonld_pairs, "jsonld@normal"
    
    # Try Next.js data
    if len(pairs) < 30:
        nd_pairs = parse_next_data(html, list_url)
        if len(nd_pairs) > len(pairs):
            pairs, src = nd_pairs, "nextdata@normal"
    
    # Try visible anchors
    if len(pairs) < 30:
        va_pairs = parse_visible_anchors(html, list_url)
        if len(va_pairs) > len(pairs):
            pairs, src = va_pairs, "anchors@normal"
    
    # Try table rows (for Fintech50)
    if len(pairs) < 30:
        table_pairs = parse_table_rows(html, list_url)
        if len(table_pairs) > len(pairs):
            pairs, src = table_pairs, "table_rows@normal"
    
    # Strategy 2: Try AMP page as fallback
    if len(pairs) < 30:
        amp_url = list_url.rstrip("/") + "/amp/"
        amp_html = fetch(amp_url) or ""
        
        amp_jsonld = parse_jsonld(amp_html, amp_url)
        if len(amp_jsonld) > len(pairs):
            pairs, src = amp_jsonld, "jsonld@amp"
        
        if len(pairs) < 30:
            amp_nd = parse_next_data(amp_html, amp_url)
            if len(amp_nd) > len(pairs):
                pairs, src = amp_nd, "nextdata@amp"
        
        if len(pairs) < 30:
            amp_va = parse_visible_anchors(amp_html, amp_url)
            if len(amp_va) > len(pairs):
                pairs, src = amp_va, "anchors@amp"
    
    pairs = dedupe_limit(pairs, max_companies)
    print(f"  ✓ Found {len(pairs)} companies using: {src}")
    
    return src, pairs

# ----------------- PROFILE EXTRACT -----------------
def extract_label_value(soup: BeautifulSoup, labels: List[str]) -> Optional[str]:
    """Extract value for a label (e.g., 'Website:', 'Category:')."""
    for lab in labels:
        tag = soup.find(string=re.compile(rf"\b{re.escape(lab)}\b", re.I))
        if not tag:
            continue
        parent = tag.parent
        if not parent:
            continue
        sib = parent.find_next_sibling()
        if sib:
            val = clean(sib.get_text(" "))
            if val:
                return val
        a = parent.find("a", href=True)
        if a:
            return a.get("href") or clean(a.get_text(strip=True))
    return None

def find_link_by_domain(soup: BeautifulSoup, domain: str) -> Optional[str]:
    """Find first link containing domain."""
    for a in soup.find_all("a", href=True):
        if domain in a["href"]:
            return a["href"]
    return None

def parse_profile(html: str, base_url: str) -> Dict[str, Optional[str]]:
    """Extract company data from Forbes profile page."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("h1")
    name = clean(title.get_text()) if title else ""

    website = extract_label_value(soup, ["Website", "Site"])
    if website and not website.startswith("http"):
        website = urljoin(base_url, website)
    
    linkedin = find_link_by_domain(soup, "linkedin.com")
    category = extract_label_value(soup, ["Category", "Industry", "Sector"])
    hq = extract_label_value(soup, ["Headquarters", "HQ"])

    hq_city, hq_country = None, None
    if hq:
        parts = [p.strip() for p in re.split(r"[,/]", hq) if p.strip()]
        if len(parts) == 1:
            hq_city = parts[0]
        elif len(parts) >= 2:
            hq_city, hq_country = parts[0], parts[-1]

    return {
        "company_name": name or None,
        "website": website or None,
        "linkedin": linkedin or None,
        "hq_city": hq_city,
        "hq_country": hq_country,
        "category": category or None,
    }

def find_linkedin_on_home(website: str) -> Optional[str]:
    """Try to find LinkedIn link on company homepage."""
    if not website:
        return None
    html = fetch(website)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    return find_link_by_domain(soup, "linkedin.com")

# ----------------- MAIN PIPELINE -----------------
def build_seed(list_url: str, max_companies: int, list_name: str) -> List[Dict[str, str]]:
    """Main pipeline to build seed data from Forbes list."""
    print(f"\n🚀 Building seed data for {list_name.upper()}")
    print(f"   List URL: {list_url}")
    print(f"   Max companies: {max_companies}")
    
    src, pairs = get_company_pairs(list_url, max_companies)
    print(f"\n📊 Extraction summary:")
    print(f"   Source: {src}")
    print(f"   Companies found: {len(pairs)}")
    
    if len(pairs) < 30:
        print("⚠️  WARNING: Fewer than 30 companies found. Results may be incomplete.")
    
    if len(pairs) == 0:
        print("❌ ERROR: No companies found. Cannot proceed.")
        return []
    
    print(f"\n📝 Scraping profile pages for {min(len(pairs), max_companies)} companies...")
    out = []
    for i, (name_guess, prof_url) in enumerate(pairs[:max_companies], 1):
        print(f"\n[{i}/{min(len(pairs), max_companies)}] {name_guess}")
        print(f"   Profile: {prof_url}")
        time.sleep(SLEEP)
        
        prof_html = fetch(prof_url)
        row = {
            "company_name": name_guess,
            "website": None,
            "linkedin": None,
            "hq_city": None,
            "hq_country": None,
            "category": None,
        }
        
        if prof_html:
            parsed = parse_profile(prof_html, prof_url)
            for k in row.keys():
                if parsed.get(k):
                    row[k] = parsed[k]
        
        # Normalize website URL
        if row["website"] and row["website"] not in (None, ""):
            row["website"] = pick_domain(row["website"])
        
        # Try to find LinkedIn on homepage if not found in profile
        if (not row.get("linkedin") or row["linkedin"] is None) and row.get("website"):
            time.sleep(SLEEP)
            ln = find_linkedin_on_home(row["website"])
            if ln:
                row["linkedin"] = ln
        
        # Convert None to None (keep as null in JSON)
        # Only set defaults if we really have no data
        out.append(row)
    
    return out

def print_scraped_urls():
    """Print all URLs that were scraped."""
    print(f"\n📋 Scraped URLs ({len(scraped_urls)} total):")
    for url in scraped_urls:
        print(f"   - {url}")

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Forbes lists and generate seed JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_seed_from_web.py --list ai50
  python build_seed_from_web.py --list fintech50
  python build_seed_from_web.py --list fintech50 --output custom.json
        """
    )
    parser.add_argument(
        "--list",
        choices=list(FORBES_LISTS.keys()),
        required=True,
        help="Forbes list to scrape"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: auto-generated from list name)"
    )
    parser.add_argument(
        "--show-urls",
        action="store_true",
        help="Print all URLs that were scraped"
    )
    
    args = parser.parse_args()
    
    config = FORBES_LISTS[args.list]
    list_url = config["url"]
    max_companies = config["max_companies"]
    output_path = Path(args.output) if args.output else Path(config["output"])
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build seed data
    data = build_seed(list_url, max_companies, args.list)
    
    if len(data) == 0:
        print("\n❌ No data to save. Exiting.")
        sys.exit(1)
    
    # Save to file
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    print(f"\n✅ Success!")
    print(f"   Saved {len(data)} companies to: {output_path}")
    
    if args.show_urls:
        print_scraped_urls()
    else:
        print(f"\n💡 Tip: Use --show-urls to see all scraped URLs")

if __name__ == "__main__":
    main()
